# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from models.general import User
from services.security import (
    now_tz_naive,
    RESET_LOCK_HOURS, 
    otp_hmac, otp_expiry, OTP_CODE_TTL_MINUTES, 
    MAIL_COOLDOWN_SECONDS,
    get_password_hash)

def test_password_reset_request_missing_fields(client):
    payload = {}
    response = client.post("/api/password-reset/request", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_request_invalid_email(client):
    payload = {"email": "not-an-email"}
    response = client.post("/api/password-reset/request", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_request_nonexistent_user(client):
    payload = {"email": "nonexistent@example.com"}
    response = client.post("/api/password-reset/request", json=payload)
    # We return 200 OK even if the email doesn't exist, to prevent user enumeration
    assert response.status_code == status.HTTP_200_OK

def test_password_reset_request_user_exists_but_is_not_active(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    user.is_active = False
    db_session.commit() # Ensure the change is saved to the database
    response = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user from the database to get the latest state
    # We return 200 OK even if the user is not active, to prevent user enumeration
    assert response.status_code == status.HTTP_200_OK
    # No reset code should be generated
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None

def test_password_reset_request_existing_active_user(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    response = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response.status_code == status.HTTP_200_OK
    # Code hash is generated and expiration time is set
    assert (user.reset_code_hash is not None) and (user.reset_code_hash != "")
    assert user.reset_expires_at is not None

def test_password_reset_request_operation_is_locked(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    user.reset_locked_until = now_tz_naive() + timedelta(hours=RESET_LOCK_HOURS)
    db_session.commit() # Save the changes to the database
    response = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    # Even if the operation is locked, we return 200 OK to prevent user enumeration
    assert response.status_code == status.HTTP_200_OK
    # No new reset code should be generated
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None

def test_password_reset_request_locked_expired(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    user.reset_locked_until = now_tz_naive() - timedelta(seconds=1)
    db_session.commit() # Save the changes to the database
    response = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response.status_code == status.HTTP_200_OK
    # Code hash is generated and expiration time is set, because the lockout has expired
    assert (user.reset_code_hash is not None) and (user.reset_code_hash != "")
    assert (user.reset_expires_at is not None) and (user.reset_expires_at > now_tz_naive())

def test_password_reset_request_code_expiration_is_none(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    reset_code_example = "0123456789"
    code_hash = otp_hmac(reset_code_example)
    user.reset_code_hash = code_hash
    user.reset_expires_at = None
    db_session.commit() # Save the changes to the database
    response = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response.status_code == status.HTTP_200_OK
    # A new reset code should be generated
    assert (user.reset_code_hash is not None) and (user.reset_code_hash != "")
    assert (user.reset_expires_at is not None) and (user.reset_expires_at > now_tz_naive())
    assert user.last_reset_mail_code_at is not None

def test_password_reset_request_retry_too_soon(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    assert (user.reset_code_hash is not None) and (user.reset_code_hash != "")
    assert (user.reset_expires_at is not None) and (user.reset_expires_at > now_tz_naive())
    assert (user.last_reset_mail_code_at is not None)
    code_expires_at = user.reset_expires_at
    code_hash = user.reset_code_hash
    last_mail_code_at = user.last_reset_mail_code_at
    # Now we try to reset the password again too soon
    response2 = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response2.status_code == status.HTTP_200_OK
    # The reset code should remain unchanged, because the second request should be ignored due to cooldown (too soon)
    assert user.reset_code_hash == code_hash
    assert user.reset_expires_at == code_expires_at
    assert user.last_reset_mail_code_at == last_mail_code_at

def test_password_reset_request_retry_after_cooldown(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    assert (user.reset_code_hash is not None) and (user.reset_code_hash != "")
    assert (user.reset_expires_at is not None) and (user.reset_expires_at > now_tz_naive())
    assert (user.last_reset_mail_code_at is not None)
    code_hash = user.reset_code_hash
    # Simulate waiting for cooldown period to expire
    user.reset_expires_at = user.reset_expires_at - timedelta(minutes=OTP_CODE_TTL_MINUTES + 1)
    db_session.commit()
    # Now we try to reset the password again after cooldown
    response2 = client.post("/api/password-reset/request", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response2.status_code == status.HTTP_200_OK
    # A new reset code should be generated (because the cooldown is expired)
    assert user.reset_code_hash != code_hash

def test_password_reset_confirm_missing_fields(client):
    payload = {}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_confirm_invalid_email(client):
    payload = {"email": "not-an-email", "code": "0123456789", "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_confirm_invalid_code(client):
    payload = {"email": "testuser@example.com", "code": "invalid-code", "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_confirm_invalid_password(client):
    payload = {"email": "testuser@example.com", "code": "0123456789", "new_password": "password_too_simple"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_password_reset_confirm_nonexistent_user(client):
    payload = {"email": "nonexistent@example.com", "code": "0123456789", "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_password_reset_confirm_user_exists_but_is_not_active(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    user.is_active = False
    # We set a valid reset code and expiration time, to ensure that the reset code is valid but the user is not active
    valid_code = "0123456789"
    user.reset_code_hash = otp_hmac(valid_code)
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    payload = {"email": user.email, "code": valid_code, "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_password_reset_confirm_code_expired(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    # We don't know the generated code, so we set a valid reset code
    # We set a valid reset code but with an expiration time too old (expired)
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = now_tz_naive() - timedelta(minutes=1)
    db_session.commit() # Ensure the change is saved to the database
    payload = {"email": user.email, "code": valid_code, "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_password_reset_confirm_wrong_code(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    # We don't know the generated code, so we set a valid reset code
    valid_code = "0123456789"
    valid_code_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_code_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    # A code that is different from the valid code
    wrong_code = "0000000000"
    payload = {"email": user.email, "code": wrong_code, "new_password": "Password!12345"}
    response2 = client.post("/api/password-reset/confirm", json=payload)
    assert response2.status_code == status.HTTP_400_BAD_REQUEST

def test_password_reset_confirm_too_many_attempts(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # We can skip the request step for convenience (we will set the reset code and expiration time manually)
    valid_code = "0123456789"
    valid_code_hash = otp_hmac(valid_code)
    wrong_code = "0000000000"
    user.reset_code_hash = valid_code_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    for i in range(0, 3): # Simulate 3 failed attempts
         payload = {"email": user.email, "code": wrong_code, "new_password": "Password!12345"}
         response = client.post("/api/password-reset/confirm", json=payload)
         db_session.refresh(user)
         assert response.status_code == status.HTTP_400_BAD_REQUEST
         assert user.reset_locked_until is None
         assert user.reset_attempts == (i + 1) 
    # After 3 failed attempts (at the 4th attempt) the operation should be locked
    payload = {"email": user.email, "code": wrong_code, "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert user.reset_locked_until is not None
    assert user.reset_locked_until > now_tz_naive()
    # After the lockout, these values should be reset
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.reset_attempts == 0
    # Now we try with a valid code, but the operation should still be locked
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit()
    # The code is valid, but the operation should still be locked
    payload = {"email": user.email, "code": valid_code, "new_password": "Password!12345"}
    response = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response.status_code == status.HTTP_400_BAD_REQUEST
    assert user.reset_locked_until is not None
    assert user.reset_locked_until > now_tz_naive()
    # The reset attempts should not be incremented, because the operation is locked
    assert user.reset_attempts == 0

def test_password_reset_confirm_lock_expired(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    old_password_hash = user.password_hash
    new_password = "Password!12345"
    new_password_hash = get_password_hash(new_password)
    assert old_password_hash != new_password_hash
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    user.reset_locked_until = now_tz_naive() - timedelta(seconds=1)  # Set the lockout time in the past
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    wrong_code = "0000000000"
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    # We try with a wrong code, but the lockout has expired, so the reset attempts should be incremented and the operation should not be locked
    payload = {"email": user.email, "code": wrong_code, "new_password": new_password }
    response2 = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response2.status_code == status.HTTP_400_BAD_REQUEST
    assert user.reset_locked_until is not None # expired but not None
    # The reset attempts should be incremented, because the lockout has expired
    assert user.reset_attempts == 1
    # Now we try with the valid code, and the operation should be successful because the lockout has expired
    payload = {"email": user.email, "code": valid_code, "new_password": new_password}
    response3 = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response3.status_code == status.HTTP_200_OK
    assert user.reset_locked_until is None
    assert user.reset_attempts == 0
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.password_hash is not None
    # The password hash should be updated to the new password hash
    assert user.password_hash != old_password_hash

def test_password_reset_confirm_valid_code(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    old_password_hash = user.password_hash
    new_password = "Password!12345"
    new_password_hash = get_password_hash(new_password)
    assert old_password_hash != new_password_hash
    payload = {"email": user.email}
    response1 = client.post("/api/password-reset/request", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user to get the latest state
    # We don't know the generated code, so we set a valid reset code
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    assert user.reset_expires_at > now_tz_naive() + timedelta(minutes=(OTP_CODE_TTL_MINUTES-1))
    assert user.reset_expires_at <= now_tz_naive() + timedelta(minutes=OTP_CODE_TTL_MINUTES)
    db_session.commit() # Ensure the change is saved to the database
    payload = {"email": user.email, "code": valid_code, "new_password": new_password}
    response2 = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response2.status_code == status.HTTP_200_OK
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.reset_locked_until is None
    assert user.reset_attempts == 0
    assert user.last_reset_done_at is not None
    assert user.password_hash is not None
    assert user.password_hash != old_password_hash
    assert user.last_reset_mail_confirmation_at is not None

def test_password_reset_confirm_no_email_if_reset_again_too_soon(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    old_password_hash = user.password_hash
    new_password = "Password!12345"
    new_password_hash = get_password_hash(new_password)
    assert old_password_hash != new_password_hash
    # We can skip the request step for convenience (we will set the reset code and expiration time manually)
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit()
    payload = {"email": user.email, "code": valid_code, "new_password": new_password}
    response1 = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response1.status_code == status.HTTP_200_OK
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.reset_locked_until is None
    assert user.reset_attempts == 0
    assert user.last_reset_done_at is not None
    assert user.password_hash is not None
    assert user.password_hash != old_password_hash
    assert user.last_reset_mail_confirmation_at is not None
    # We simulate that the confirmation email was sent just 1 second ago (just now more or less)
    user.last_reset_mail_confirmation_at -= timedelta(seconds=1)
    old_last_reset_mail_confirmation_at = user.last_reset_mail_confirmation_at
    db_session.commit() # Save the change to the database
    # Now we try to reset the password again immediately
    response2 = client.post("/api/password-reset/request", json={"email": user.email})
    assert response2.status_code == status.HTTP_200_OK
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    db_session.commit() # Ensure the change is saved to the database
    response3 = client.post("/api/password-reset/confirm", json={"email": user.email, "code": valid_code, "new_password": new_password})
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response3.status_code == status.HTTP_200_OK
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.last_reset_mail_code_at is not None
    assert user.last_reset_mail_confirmation_at is not None
    assert user.password_hash != old_password_hash
    # The last_reset_mail_confirmation_at should remain unchanged, 
    # because the second request should be ignored due to cooldown
    # so the confirmation email should not be sent again
    assert user.last_reset_mail_confirmation_at == old_last_reset_mail_confirmation_at

def test_password_reset_confirm_email_resent_if_cooldown_expired(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    old_password_hash = user.password_hash
    new_password = "Password!12345"
    new_password_hash = get_password_hash(new_password)
    assert old_password_hash != new_password_hash
    # We can skip the request step for convenience (we will set the reset code and expiration time manually)
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    payload = {"email": user.email, "code": valid_code, "new_password": new_password}
    response1 = client.post("/api/password-reset/confirm", json=payload)
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response1.status_code == status.HTTP_200_OK
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.reset_locked_until is None
    assert user.reset_attempts == 0
    assert user.last_reset_done_at is not None
    assert user.password_hash is not None
    assert user.password_hash != old_password_hash
    assert user.last_reset_mail_confirmation_at is not None
    # We simulate that the confirmation email was sent many seconds ago (cooldown expired)
    user.last_reset_mail_confirmation_at -= timedelta(seconds=MAIL_COOLDOWN_SECONDS + 1)
    old_last_reset_mail_confirmation_at = user.last_reset_mail_confirmation_at
    # Now we try to reset the password again immediately, and we will see that a new confirmation email should be sent
    # We skip the request step for convenience (we will set the reset code and expiration time manually)
    valid_code = "0123456789"
    valid_hash = otp_hmac(valid_code)
    user.reset_code_hash = valid_hash
    user.reset_expires_at = otp_expiry()
    db_session.commit() # Ensure the change is saved to the database
    response2 = client.post("/api/password-reset/confirm", json={"email": user.email, "code": valid_code, "new_password": new_password})
    db_session.refresh(user) # Refresh the user to get the latest state
    assert response2.status_code == status.HTTP_200_OK
    assert user.reset_code_hash is None
    assert user.reset_expires_at is None
    assert user.last_reset_mail_confirmation_at is not None
    assert user.password_hash != old_password_hash
    # The last_reset_mail_confirmation_at should be updated,
    # because the cooldown has expired and a new confirmation email should be sent
    assert user.last_reset_mail_confirmation_at != old_last_reset_mail_confirmation_at
