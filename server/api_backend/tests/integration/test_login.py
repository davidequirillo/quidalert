# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from sqlmodel import select
from models.general import (
    User, RefreshToken,
    USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS,
    USER_RELIABILITY_SCORE_INC_VALUE,
    UserLanguage
)
from services.security import (
    get_password_hash, 
    otp_hmac, otp_expiry, OTP_CODE_TTL_MINUTES,
    now_tz_naive, now_tz_aware,
    from_timestamp_to_datetime_tz_naive,
    from_datetime_to_timestamp,
    MAIL_COOLDOWN_SECONDS,
    LOGIN_TOKEN_TTL_MINUTES,
    REFRESH_TOKEN_TTL_MINUTES,
    ACCESS_TOKEN_TTL_MINUTES,
    GEOPOSITION_TOKEN_TTL_MINUTES,
    decode_token, create_login_token,
    check_token_against_hash)
from core.exceptions import (
    credentials_exception, 
    two_factor_not_valid_exception,
    two_factor_locked_exception,
    forbidden_exception)
from core.responses import two_factor_required_response

def test_login_request_missing_credentials(client):
    payload = {}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = {"email": "user@example.com", "password": None}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_login_request_password_empty(client):
    payload = {"email": "user@example.com", "password": ""}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_invalid_credentials(client, not_logged_test_user):
    user: User = not_logged_test_user
    assert user.email != "invalid@example.com"
    payload = {"email": "invalid@example.com", "password": "InvalidPassword123?"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_invalid_password(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": "InvalidPassword12345?"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_valid_password(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We use the valid password
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.json()["detail"] == "2FA required"
    db_session.refresh(user)
    assert user.login_code_hash is not None
    assert user.login_expires_at is not None
    assert user.login_expires_at > now_tz_naive() + timedelta(minutes=(OTP_CODE_TTL_MINUTES-1))
    assert user.login_expires_at <= now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
    assert user.last_login_mail_code_at is not None

def test_login_request_user_not_active(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    user.is_active = False
    db_session.commit() # Ensure the updated user status is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_user_not_found(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We use the valid password but an email that does not exist in the database
    payload = {"email": "nonexistent@example.com", "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_again_too_soon(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response1 = client.post("/api/auth/login", json=payload)
    assert response1.status_code == two_factor_required_response().status_code
    assert response1.json()["detail"] == "2FA required"
    db_session.refresh(user)
    assert user.login_code_hash is not None
    assert user.login_expires_at is not None
    old_login_code_hash = user.login_code_hash
    old_login_expires_at = user.login_expires_at
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    # Try to login again immediately, which should be too soon and return the same 2FA required response without generating a new code
    response2 = client.post("/api/auth/login", json=payload)
    assert response2.status_code == two_factor_required_response().status_code
    assert response2.json()["detail"] == "2FA required"
    db_session.refresh(user)
    # The login code hash and expires_at should be unchanged (same code still valid)
    assert user.login_code_hash == old_login_code_hash
    assert user.login_expires_at == old_login_expires_at

def test_login_request_again_after_expiry(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response1 = client.post("/api/auth/login", json=payload)
    assert response1.status_code == two_factor_required_response().status_code
    assert response1.json()["detail"] == "2FA required"
    db_session.refresh(user)
    assert user.login_code_hash is not None
    assert user.login_expires_at is not None
    old_login_code_hash = user.login_code_hash
    # Simulate code expiry by setting expires_at in the past
    user.login_expires_at = now_tz_naive() - timedelta(minutes=1)
    db_session.commit() # Ensure the updated login expires_at is saved to the database
    # Try to login again, which should generate a new code since the old one is expired
    response2 = client.post("/api/auth/login", json=payload)
    assert response2.status_code == two_factor_required_response().status_code
    assert response2.json()["detail"] == "2FA required"
    db_session.refresh(user)
    # The login code hash and expires_at should be updated (new code generated)
    assert user.login_code_hash != old_login_code_hash
    assert user.login_expires_at > now_tz_naive()

def test_login_2fa_wrong_code(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.json()["detail"] == "2FA required"
    db_session.refresh(user)
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    wrong_otp_code = "000000"
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": wrong_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == two_factor_not_valid_exception().status_code
    assert response_2fa.json()["detail"] == two_factor_not_valid_exception().detail
    db_session.refresh(user)
    assert user.login_2fa_attempts == 1
    # We try again with a wrong code
    response_2fa_again = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa_again.status_code == two_factor_not_valid_exception().status_code
    assert response_2fa_again.json()["detail"] == two_factor_not_valid_exception().detail
    db_session.refresh(user)
    assert user.login_2fa_attempts == 2

def test_login_2fa_expired_code(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # We can skip the initial login request and directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    # Simulate code expiry by setting expires_at in the past
    user.login_expires_at = now_tz_naive() - timedelta(minutes=1)
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    # We try to login with the expired code (valid, but expired)
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == two_factor_not_valid_exception().status_code
    assert response_2fa.json()["detail"] == two_factor_not_valid_exception().detail

def test_login_2fa_code_not_requested(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": "123456"}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == two_factor_not_valid_exception().status_code
    assert response_2fa.json()["detail"] == two_factor_not_valid_exception().detail
    db_session.refresh(user)
    # Login attempts should be zero because 2FA code was not requested (it's not a case of wrong code)
    assert user.login_2fa_attempts == 0
    assert user.login_code_hash is None
    assert user.login_expires_at is None

def test_login_2fa_too_many_attempts(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # We can skip the initial login request and directly set the login code, expires_at and attempts for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = otp_expiry()
    user.login_2fa_attempts = 3 # Simulate max attempts reached
    db_session.commit() # Ensure the updated login code hash, expires_at and attempts are saved to the database
    wrong_otp_code = "000000"
    # Try to login with wrong code, but since max attempts are reached, it should lock the login 2fa process
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": wrong_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    # The response should indicate that the 2FA code is not valid (max attempts reached, so it doesn't even check the code)
    assert response_2fa.status_code == two_factor_not_valid_exception().status_code
    assert response_2fa.json()["detail"] == two_factor_not_valid_exception().detail
    db_session.refresh(user)
    # The user is locked from now, 2fa attempts attribute is reset to 0, and login code is cleared
    assert user.login_2fa_attempts == 0
    # The login code hash and expires_at should be cleared (code invalidated)
    assert user.login_code_hash is None
    assert user.login_expires_at is None
    assert user.login_locked_until is not None
    # Now, even if we try with the correct code, it should still be locked
    payload_2fa_correct = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa_correct = client.post("/api/auth/login", json=payload_2fa_correct)
    assert response_2fa_correct.status_code == two_factor_locked_exception().status_code
    assert response_2fa_correct.json()["detail"] == two_factor_locked_exception().detail
    # We also try to do a login request (only email and password)
    # It shoud be locked as well
    payload_login = {"email": user.email, "password": valid_password}
    response_login = client.post("/api/auth/login", json=payload_login)
    assert response_login.status_code == two_factor_locked_exception().status_code
    assert response_login.json()["detail"] == two_factor_locked_exception().detail

def test_login_2fa_successful(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.json()["detail"] == "2FA required"
    db_session.refresh(user)
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = otp_expiry()
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == status.HTTP_200_OK
    assert "access_token" in response_2fa.json()
    assert response_2fa.json()["token_type"] == "bearer"
    db_session.refresh(user)
    # After successful login, the login code and expires_at should be cleared, and attempts reset
    assert user.login_code_hash is None
    assert user.login_expires_at is None
    assert user.login_2fa_attempts == 0
    assert user.login_locked_until is None
    assert user.last_login_done_at is not None
    assert user.last_login_mail_confirmation_at is not None

def test_login_2fa_successful_again_too_soon(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # We can skip the initial login request and directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.password_hash = valid_password_hash
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = otp_expiry()
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response1 = client.post("/api/auth/login", json=payload_2fa)
    assert response1.status_code == status.HTTP_200_OK
    assert "access_token" in response1.json()
    assert response1.json()["token_type"] == "bearer"
    db_session.refresh(user)
    # After successful login, the login code and expires_at should be cleared, and attempts reset
    assert user.login_code_hash is None
    assert user.login_expires_at is None
    assert user.login_2fa_attempts == 0
    assert user.login_locked_until is None
    assert user.last_login_done_at is not None
    assert user.last_login_mail_confirmation_at is not None
    # Now we try to login (with 2fa) again immediately, and mail message should not be send again (in cooldown)
    # We can skip again the initial login request and directly set the login code and the expires_at for convenience
    # We set the code hash from a valid code
    user.login_code_hash = otp_hmac(valid_otp_code)
    user.login_expires_at = otp_expiry()
    # We also simulate that the mail was sent just now, more or less, 1 second ago
    user.last_login_mail_confirmation_at = now_tz_naive() - timedelta(seconds=1)
    old_last_mail_confirmation_at = user.last_login_mail_confirmation_at
    db_session.commit() # Ensure the updated last_login_mail_confirmation_at is saved to the database
    # Now we do the 2fa login with the valid code, and it should work, but it should not send a new mail, because it's in cooldown
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response2 = client.post("/api/auth/login", json=payload_2fa)
    assert response2.status_code == status.HTTP_200_OK
    assert "access_token" in response2.json()
    assert response2.json()["token_type"] == "bearer"
    db_session.refresh(user)
    # After successful login, the login code and expires_at should be cleared, and attempts reset
    assert user.login_code_hash is None
    assert user.login_expires_at is None
    assert user.login_2fa_attempts == 0
    assert user.login_locked_until is None
    assert user.last_login_done_at is not None
    assert user.last_login_mail_confirmation_at is not None
    # The last_login_mail_confirmation_at should be unchanged, because the mail should not be sent again, because we are within the cooldown period for sending a new mail
    assert user.last_login_mail_confirmation_at == old_last_mail_confirmation_at # No new mail should be sent, so the timestamp should be unchanged

def test_login_2fa_successful_again_after_cooldown(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # We can skip the initial login request and directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = otp_expiry()
    # We simulate that the mail was already sent many seconds ago (cooldown expired)
    # We skip the last 2fa login and directly set the last_login_mail_confirmation_at in the past
    user.last_login_mail_confirmation_at = now_tz_naive() - timedelta(seconds=MAIL_COOLDOWN_SECONDS + 1)
    old_last_mail_confirmation_at = user.last_login_mail_confirmation_at
    db_session.commit() # Ensure the updated login code hash, expires_at and last_login_mail_confirmation_at are saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == status.HTTP_200_OK
    assert "access_token" in response_2fa.json()
    assert response_2fa.json()["token_type"] == "bearer"
    db_session.refresh(user)
    # After successful login, the login code and expires_at should be cleared, and attempts reset
    assert user.login_code_hash is None
    assert user.login_expires_at is None
    assert user.login_2fa_attempts == 0
    assert user.login_locked_until is None
    assert user.last_login_done_at is not None
    assert user.last_login_mail_confirmation_at is not None
    # A new mail should be sent, so the timestamp should be updated
    assert user.last_login_mail_confirmation_at > old_last_mail_confirmation_at

def test_login_2fa_successful_and_login_token_works(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Last reset done at is a default timestamp, equal to created_at when the user is created
    assert user.last_reset_done_at is not None
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.json()["detail"] == "2FA required"
    db_session.refresh(user) # Refresh to get the latest login code hash and expires_at
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = otp_expiry()
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    db_session.refresh(user) # Refresh to get the latest last_2fa_success_at
    assert user.last_2fa_success_at is not None
    assert response_2fa.status_code == status.HTTP_200_OK
    assert "access_token" in response_2fa.json()
    assert response_2fa.json()["token_type"] == "bearer"
    access_token = response_2fa.json()["access_token"]
    assert access_token is not None
    login_token = response_2fa.json().get("login_token")
    assert login_token is not None
    # Test that the login token is valid and contains the expected data
    login_token_data = decode_token(login_token)
    login_token_sub = login_token_data.get("sub")
    login_token_type = login_token_data.get("type")
    login_token_exp = login_token_data.get("exp")
    login_token_iat = login_token_data.get("iat")
    assert login_token_data is not None
    assert login_token_sub == str(user.id)
    assert login_token_type == "login"
    assert login_token_exp is not None
    assert login_token_iat is not None
    # The issued at time should be in the past, but not too much in the past (e.g. not more than 1 minute ago)
    assert login_token_iat <= int(now_tz_aware().timestamp())
    assert login_token_iat > int((now_tz_aware() - timedelta(minutes=1)).timestamp())
    iat_dt = from_timestamp_to_datetime_tz_naive(login_token_iat)
    # The issued at time should be after the last password reset time, otherwise the token should be invalid
    assert iat_dt >= user.last_reset_done_at
    # The issued at time should be after the last successful 2FA time
    assert iat_dt >= user.last_2fa_success_at
    # The token should not be expired (expiration more or less at timedelta of LOGIN_TOKEN_TTL_MINUTES)
    assert login_token_exp > int((now_tz_aware() + timedelta(minutes=(LOGIN_TOKEN_TTL_MINUTES-1))).timestamp())
    assert login_token_exp <= int((now_tz_aware() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES)).timestamp())
    # Now we try to login again with the login token, without providing the 2FA code, and it should work
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None

def test_login_token_expired(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id), expires_delta=timedelta(minutes=-1)) # Create an already expired token
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    # The token is expired, so the login will send to the user the 2FA required response (2FA code via mail)
    assert response.status_code == two_factor_required_response().status_code
    assert response.json()["detail"] == "2FA required"

def test_login_user_is_blocked(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    user.is_blocked = True
    db_session.commit() # Ensure the updated password hash and blocked status are saved to the database
    # we skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_login_user_is_blocked_but_is_superuser(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    user.is_blocked = True
    user.is_superuser = True    
    db_session.commit() # Ensure the updated password hash and blocked status are saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    # Even if the user is blocked, since it's a superuser, it should be allowed to login
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None

def test_login_2fa_code_and_login_token_together(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # We skip the initial login request for convenience, and we directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    user.login_code_hash = otp_hmac(valid_otp_code)
    user.login_expires_at = otp_expiry()
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We create a login token with a custom expiry time
    # it ensures that the new login token will be different from this one
    login_token = create_login_token(str(user.id), expires_delta=timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES + 10))
    payload = {"email": user.email, "password": valid_password, "login_token": login_token, "login_code": valid_otp_code}
    response = client.post("/api/auth/login", json=payload)
    # When both otp code and login token are provided, login token is ignored, and the otp code is used for authentication
    # A new login token is generated and returned to the client
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert response.json()["token_type"] == "bearer"
    assert "login_token" in response.json()
    new_login_token = response.json()["login_token"]
    assert new_login_token is not None
    # The new login token should be different from the old one, because the old one should be ignored and a new one should be generated based on the successful 2FA authentication
    assert new_login_token != login_token

def test_login_refresh_token_saved_in_db(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit()
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token, "device_model": "Example device model"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_refresh_at is not None
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "gps_token" in response.json()
    assert "login_token" in response.json()
    # If we provide login token in place of 2FA, 
    # a successful login will not return a new login token
    assert response.json()["login_token"] is None
    refresh_token = response.json()["refresh_token"]
    refresh_token_data = decode_token(refresh_token)
    rtoken_sub = refresh_token_data.get("sub")
    rtoken_type = refresh_token_data.get("type")
    rtoken_exp = refresh_token_data.get("exp")
    rtoken_iat = refresh_token_data.get("iat")
    rtoken_raw = refresh_token_data.get("raw")
    rtoken_jti = refresh_token_data.get("jti")
    assert rtoken_sub == str(user.id)
    assert rtoken_type == "refresh"
    assert rtoken_iat <= int(now_tz_aware().timestamp())
    assert rtoken_iat > int((now_tz_aware() - timedelta(minutes=1)).timestamp())
    iat_dt = from_timestamp_to_datetime_tz_naive(rtoken_iat)
    assert iat_dt >= user.last_reset_done_at
    assert rtoken_exp > int((now_tz_aware() + timedelta(minutes=(REFRESH_TOKEN_TTL_MINUTES-1))).timestamp())
    assert rtoken_exp <= int((now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES)).timestamp())
    # Now we check if the refresh token is in the database, is unique, and has a valid raw hash
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    db_token: RefreshToken = results[0]
    assert str(db_token.id) == rtoken_jti
    assert check_token_against_hash(rtoken_raw, db_token.raw_hash) == True
    assert db_token.updated_at is not None
    assert db_token.updated_at <= now_tz_naive()
    assert db_token.updated_at > now_tz_naive() - timedelta(minutes=1)
    assert db_token.device_info is not None
    assert db_token.device_info == payload["device_model"]

def test_login_refresh_token_overwritten_if_login_again(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit()
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token, "device_model": "Example device model"}
    response1 = client.post("/api/auth/login", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_refresh_at is not None
    assert response1.json()["token_type"] == "bearer"
    assert "access_token" in response1.json()
    assert "refresh_token" in response1.json()
    refresh_token1 = response1.json()["refresh_token"]
    # Now we do another login, which should overwrite the previous refresh token in the database with a new one
    response2 = client.post("/api/auth/login", json=payload)
    assert response2.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_refresh_at is not None
    assert response2.json()["token_type"] == "bearer"
    assert "access_token" in response2.json()
    assert "refresh_token" in response2.json()
    refresh_token2 = response2.json()["refresh_token"]
    # The new refresh token should be different from the old one, because it should have overwritten the previous one in the database
    refresh_token_data1 = decode_token(refresh_token1)
    refresh_token_data2 = decode_token(refresh_token2)
    rtoken_jti1 = refresh_token_data1.get("jti")
    rtoken_jti2 = refresh_token_data2.get("jti")
    assert rtoken_jti1 != rtoken_jti2
    # Now we check if the new refresh token is in the database, and the old not
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    db_token: RefreshToken = results[0]
    assert str(db_token.id) == rtoken_jti2
    assert check_token_against_hash(refresh_token_data2['raw'], db_token.raw_hash) == True

def test_login_returned_access_token_is_ok(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # For convenience, we skip the initial login request and 2FA, and we directly generate a login token for the user
    login_token = create_login_token(str(user.id))
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    db_session.refresh(user) # Refresh to get the latest last_login_done_at and last_refresh_at
    assert response.status_code == status.HTTP_200_OK
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    assert response.json()["token_type"] == "bearer"
    assert "access_token" in response.json()
    access_token = response.json()["access_token"]
    assert access_token is not None
    access_token_data = decode_token(access_token)
    atoken_sub = access_token_data.get("sub")
    atoken_type = access_token_data.get("type")
    atoken_exp = access_token_data.get("exp")
    atoken_iat = access_token_data.get("iat")
    assert atoken_sub == str(user.id)
    assert atoken_type == "access"
    assert atoken_iat <= int(now_tz_aware().timestamp())
    assert atoken_iat > int((now_tz_aware() - timedelta(minutes=1)).timestamp())
    iat_dt = from_timestamp_to_datetime_tz_naive(atoken_iat)
    assert iat_dt >= user.last_login_done_at
    assert iat_dt >= user.last_refresh_at
    assert atoken_exp > from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=(ACCESS_TOKEN_TTL_MINUTES-1)))
    assert atoken_exp <= from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    # Now we can use the access token to access a protected route (e.g. /api/users/me) to verify that it works
    headers = {"Authorization": f"Bearer {access_token}"}
    protected_response = client.get("/api/profile", headers=headers)
    assert protected_response.status_code == status.HTTP_200_OK
    protected_data = protected_response.json()
    assert protected_data["email"] == user.email

def test_login_returned_gps_token_is_ok(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # The user has no role assigned (default=None), 
    # so the gps token should have a relative string role of "citizen" in the payload
    assert user.role is None
    user_role_str = user.role if user.role else "citizen"
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # For convenience, we skip the initial login request and 2FA, and we directly generate a login token for the user
    login_token = create_login_token(str(user.id))
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh to get the latest last_login_done_at and last_refresh_at
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    assert "gps_token" in response.json()
    gps_token = response.json()["gps_token"]
    assert gps_token is not None
    gps_token_data = decode_token(gps_token)
    gt_token_type = gps_token_data.get("type")
    gt_sub = gps_token_data.get("sub")
    gt_exp = gps_token_data.get("exp")
    gt_iat = gps_token_data.get("iat")
    gt_is_chief = gps_token_data.get("user_is_chief")
    gt_role = gps_token_data.get("user_role")
    assert gt_sub == str(user.id)
    assert gt_token_type == "gps-update"
    assert gt_is_chief == (1 if user.is_chief else 0)
    user_role_str = user.role if user.role is not None else "citizen"
    assert gt_role == user_role_str
    assert gt_iat <= int(now_tz_aware().timestamp())
    assert gt_iat > int((now_tz_aware() - timedelta(minutes=1)).timestamp())
    iat_dt = from_timestamp_to_datetime_tz_naive(gt_iat)
    assert iat_dt >= user.last_login_done_at
    assert iat_dt >= user.last_refresh_at
    assert gt_exp > from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=(GEOPOSITION_TOKEN_TTL_MINUTES-1)))
    assert gt_exp <= from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES))

def test_login_returned_refresh_token_is_ok(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # For convenience, we skip the initial login request and 2FA, and we directly generate a login token for the user
    login_token = create_login_token(str(user.id))
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh to get the latest last_login_done_at and last_refresh_at
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    assert "refresh_token" in response.json()
    refresh_token = response.json()["refresh_token"]
    assert refresh_token is not None
    decoded_refresh_token = decode_token(refresh_token)
    rtoken_sub = decoded_refresh_token.get("sub")
    rtoken_type = decoded_refresh_token.get("type")
    rtoken_exp = decoded_refresh_token.get("exp")
    rtoken_iat = decoded_refresh_token.get("iat")
    rtoken_raw = decoded_refresh_token.get("raw")
    rtoken_jti = decoded_refresh_token.get("jti")
    assert rtoken_sub == str(user.id)
    assert rtoken_type == "refresh"
    assert rtoken_iat <= from_datetime_to_timestamp(now_tz_aware())
    assert rtoken_iat > from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=1))
    assert rtoken_iat >= from_datetime_to_timestamp(user.last_reset_done_at)
    assert rtoken_exp > from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=(REFRESH_TOKEN_TTL_MINUTES-1)))
    assert rtoken_exp <= from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    assert rtoken_iat >= from_datetime_to_timestamp(user.last_login_done_at)
    assert rtoken_iat >= from_datetime_to_timestamp(user.last_refresh_at)
    assert rtoken_jti is not None
    assert rtoken_raw is not None

def test_login_with_negative_reliability_score_for_too_long(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time in the past, so that it's not in cooldown anymore, and the reliability score should be reset to the default value on login
    # Set a negative reliability score to check that it will be reset to a default minimum value on login, because it's been too long since the last reliability score update
    user.reliability_score = -50
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    assert user.reliability_score == USER_RELIABILITY_SCORE_INC_VALUE
    # After login, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been reset due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_login_with_negative_reliability_score_in_cooldown(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time to 10 minutes ago, so that it's in cooldown, and the reliability score should not be reset on login
    # Set a negative reliability score to check that it will not be reset
    user.reliability_score = -50
    user.last_reliability_score_at = now_tz_naive() - timedelta(minutes=10) # Set it to 10 minutes ago, so it's within the cooldown period
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should not be reset because it's in cooldown
    assert user.reliability_score == -50 
    assert user.last_reliability_score_at is not None
    # The last_reliability_score_at should be unchanged, because the reliability score should not be reset due to cooldown
    # It should be unchanged, so it should still be the old timestamp, which is 10 minutes ago
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(minutes=5)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=15)

def test_login_with_low_reliability_score_for_too_long(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time in the past, so that it's not in cooldown anymore, and the reliability score should be reset to the default value on login
    # Set a low reliability score to check that it will increase on login, because it's been too long since the last reliability score update
    user.reliability_score = 10
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should be increased, to 10 + USER_RELIABILITY_SCORE_INC_VALUE
    assert user.reliability_score == 10 + USER_RELIABILITY_SCORE_INC_VALUE
    # After login, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been increased due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_login_with_low_reliability_score_in_cooldown(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time to 10 minutes ago, so that it's in cooldown, and the reliability score should not be increased on login
    # Set a low reliability score to check that it will not be increased
    user.reliability_score = 10
    user.last_reliability_score_at = now_tz_naive() - timedelta(minutes=10) # Set it to 10 minutes ago, so it's within the cooldown period
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should not be increased because it's in cooldown
    assert user.reliability_score == 10 
    assert user.last_reliability_score_at is not None
    # The last_reliability_score_at should be unchanged, because the reliability score should not be increased due to cooldown
    # It should be unchanged, so it should still be the old timestamp, which is 10 minutes ago
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(minutes=5)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=15)

def test_login_with_low_reliability_score_and_null_timestamp(client, db_session, not_logged_test_user):
    # If reliability score is low but last_reliability_score_at is None (null timestamp), 
    # we don't increase reliability_score
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time to None
    # Set a low reliability score to check that it will not be increased
    user.reliability_score = 10
    user.last_reliability_score_at = None
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should not be increased because it's in cooldown
    assert user.reliability_score == 10 
    assert user.last_reliability_score_at is None

def test_login_with_reliability_score_near_maximum_for_too_long(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time in the past, so that it's not in cooldown anymore, and the reliability score should be reset to the default value on login
    # Set a reliability score near the maximum to check that it will be reset to the maximum value on login, because it's been too long since the last reliability score update
    user.reliability_score = 90
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should be reset to the maximum value, because it's been too long since the last reliability score update
    assert user.reliability_score == min(90 + USER_RELIABILITY_SCORE_INC_VALUE, 100)
    # After login, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been increased due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_login_with_reliability_score_near_maximum_in_cooldown(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # Set the last reliability score time to 10 minutes ago, so that it's in cooldown, and the reliability score should not be increased on login
    # Set a reliability score near the maximum to check that it will not be increased
    user.reliability_score = 90
    user.last_reliability_score_at = now_tz_naive() - timedelta(minutes=10) # Set it to 10 minutes ago, so it's within the cooldown period
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The reliability score should not be increased because it's in cooldown
    assert user.reliability_score == 90 
    assert user.last_reliability_score_at is not None
    # The last_reliability_score_at should be unchanged, because the reliability score should not be increased due to cooldown
    # It should be unchanged, so it should still be the old timestamp, which is 10 minutes ago
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(minutes=5)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=15)

def test_login_with_language_preference(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # We set the language preference to English
    user.language = UserLanguage.en.value # Default language is English
    db_session.commit() # Ensure the updated password hash and language preference are saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    # We set the language to Italian in the login request
    payload = {"email": user.email, "password": valid_password, "login_token": login_token, "language": "it"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The language preference should be updated to Italian
    assert user.language == UserLanguage.it.value

def test_login_with_language_preference_invalid(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # We set the language preference to English
    user.language = UserLanguage.en.value # Default language is English
    db_session.commit() # Ensure the updated password hash and language preference are saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    # We set an invalid language in the login request
    payload = {"email": user.email, "password": valid_password, "login_token": login_token, "language": "invalid"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # The language preference should remain unchanged
    db_session.refresh(user)
    assert user.language == UserLanguage.en.value

def test_login_with_pending_delete_status(client, db_session, not_logged_test_user):
    user: User = not_logged_test_user
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    # We set the user as pending deletion from yesterday (or recently)
    user.pending_delete_since = now_tz_naive() - timedelta(days=1)
    db_session.commit() # Ensure the updated password hash and pending deletion status are saved to the database
    # We skip login request and 2fa for convenience, and we directly generate a login token for the user, simulating that the user has already passed 2FA and has a valid login token
    login_token = create_login_token(str(user.id)) 
    payload = {"email": user.email, "password": valid_password, "login_token": login_token}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
    # The pending_delete_since should be cleared after successful login, because the user has logged in and is active again
    # It means: the user has confirmed that they want to keep their account, so the pending deletion is canceled
    assert user.pending_delete_since is None
