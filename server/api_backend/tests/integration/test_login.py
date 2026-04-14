# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from models.general import User
from services.security import (
    get_password_hash, 
    otp_hmac, OTP_CODE_TTL_MINUTES,
    now_tz_naive, MAIL_COOLDOWN_SECONDS,
    LOGIN_TOKEN_TTL_MINUTES,
    decode_token)
from core.exceptions import (
    credentials_exception, 
    two_factor_required_response,
    two_factor_not_valid_exception,
    two_factor_locked_exception)

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

def test_login_request_invalid_credentials(client, test_user_not_logged):
    user: User = test_user_not_logged
    assert user.email != "invalid@example.com"
    payload = {"email": "invalid@example.com", "password": "InvalidPassword123?"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_invalid_password(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": "InvalidPassword12345?"}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == credentials_exception().status_code
    assert response.json()["detail"] == credentials_exception().detail

def test_login_request_valid_password(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    # We use the valid password
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.content == two_factor_required_response().body
    db_session.refresh(user)
    assert user.login_code_hash is not None
    assert user.login_expires_at is not None
    assert user.last_login_mail_code_at is not None

def test_login_request_user_not_active(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
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

def test_login_request_user_not_found(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
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

def test_login_request_again_too_soon(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response1 = client.post("/api/auth/login", json=payload)
    assert response1.status_code == two_factor_required_response().status_code
    assert response1.content == two_factor_required_response().body
    db_session.refresh(user)
    assert user.login_code_hash is not None
    assert user.login_expires_at is not None
    old_login_code_hash = user.login_code_hash
    old_login_expires_at = user.login_expires_at
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    # Try to login again immediately, which should be too soon and return the same 2FA required response without generating a new code
    response2 = client.post("/api/auth/login", json=payload)
    assert response2.status_code == two_factor_required_response().status_code
    assert response2.content == two_factor_required_response().body
    db_session.refresh(user)
    # The login code hash and expires_at should be unchanged (same code still valid)
    assert user.login_code_hash == old_login_code_hash
    assert user.login_expires_at == old_login_expires_at

def test_login_request_again_after_expiry(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response1 = client.post("/api/auth/login", json=payload)
    assert response1.status_code == two_factor_required_response().status_code
    assert response1.content == two_factor_required_response().body
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
    assert response2.content == two_factor_required_response().body
    db_session.refresh(user)
    # The login code hash and expires_at should be updated (new code generated)
    assert user.login_code_hash != old_login_code_hash
    assert user.login_expires_at > now_tz_naive()

def test_login_2fa_wrong_code(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.content == two_factor_required_response().body
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

def test_login_2fa_expired_code(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
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

def test_login_2fa_code_not_requested(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
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

def test_login_2fa_too_many_attempts(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # We can skip the initial login request and directly set the login code, expires_at and attempts for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
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

def test_login_2fa_successful(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.content == two_factor_required_response().body
    db_session.refresh(user)
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
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

def test_login_2fa_successful_again_too_soon(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # We can skip the initial login request and directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.password_hash = valid_password_hash
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
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
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
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

def test_login_2fa_successful_again_after_cooldown(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # We can skip the initial login request and directly set the login code and expires_at for convenience
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
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

def test_login_2fa_successful_login_token_works(client, db_session, test_user_not_logged):
    user: User = test_user_not_logged
    # Set a know valid password for the user
    valid_password = "ValidPass123!"
    valid_password_hash = get_password_hash(valid_password)
    user.password_hash = valid_password_hash
    db_session.commit() # Ensure the updated password hash is saved to the database
    payload = {"email": user.email, "password": valid_password}
    response = client.post("/api/auth/login", json=payload)
    assert response.status_code == two_factor_required_response().status_code
    assert response.content == two_factor_required_response().body
    db_session.refresh(user) # Refresh to get the latest login code hash and expires_at
    valid_otp_code = "123456"
    valid_otp_code_hash = otp_hmac(valid_otp_code)
    user.login_code_hash = valid_otp_code_hash
    user.login_expires_at = now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
    db_session.commit() # Ensure the updated login code hash and expires_at are saved to the database
    payload_2fa = {"email": user.email, "password": valid_password, "login_code": valid_otp_code}
    response_2fa = client.post("/api/auth/login", json=payload_2fa)
    assert response_2fa.status_code == status.HTTP_200_OK
    assert "access_token" in response_2fa.json()
    assert response_2fa.json()["token_type"] == "bearer"
    access_token = response_2fa.json()["access_token"]
    assert access_token is not None
    login_token = response_2fa.json().get("login_token")
    assert login_token is not None
    # Test that the login token is valid and contains the expected data
    login_token_data = decode_token(login_token)
    assert login_token_data is not None
    assert login_token_data.get("sub") == str(user.id)
    assert login_token_data.get("type") == "login"
    assert login_token_data.get("exp") is not None
    assert login_token_data.get("iat") is not None
    # The issued at time should be in the past, but not too much in the past (e.g. not more than 1 minute ago)
    assert login_token_data.get("iat") <= int(now_tz_naive().timestamp())
    assert login_token_data.get("iat") > int((now_tz_naive() - timedelta(minutes=1)).timestamp())
    # The token should not be expired (expiration more or less at timedelta of LOGIN_TOKEN_TTL_MINUTES)
    assert login_token_data.get("exp") > int((now_tz_naive() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES - 1)).timestamp())
    assert login_token_data.get("exp") <= int((now_tz_naive() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES)).timestamp())
    # Now we try to login again with the login token, without providing the 2FA code, and it should work
    payload_login_token = {"email": user.email, "password": valid_password, "login_token": login_token}
    response_login_token = client.post("/api/auth/login", json=payload_login_token)
    assert response_login_token.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.last_login_done_at is not None
    assert user.last_refresh_at is not None
