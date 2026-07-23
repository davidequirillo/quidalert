# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_expired_exception, 
    token_not_valid_exception
)
from models.general import (
    User, RefreshToken, string_as_uuid,
    USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS,
    USER_RELIABILITY_SCORE_INC_VALUE
)
from services.security import (
    now_tz_naive, now_tz_aware,
    create_refresh_token,
    decode_token,
    TOKEN_DECODE_LEEWAY_SECONDS,
)

def test_refresh_successful(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "gps_token" in response.json()
    new_refresh_token = response.json()["refresh_token"]
    assert new_refresh_token != refresh_token

def test_refresh_expired_token(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    refresh_token = test_baseuser['refresh_token']
    refresh_token_decoded = decode_token(refresh_token)
    token_jti = refresh_token_decoded.get("jti")
    token_raw = refresh_token_decoded.get("raw")
    token_sub = refresh_token_decoded.get("sub")
    # Create an expired refresh token 
    exp = timedelta(seconds=-TOKEN_DECODE_LEEWAY_SECONDS - 1)
    iat = now_tz_aware()
    rtoken_expired = create_refresh_token(subject=token_sub, token_id=token_jti, raw_code=token_raw, expires_delta=exp, issued_at=iat)
    payload = {"refresh_token": rtoken_expired}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_expired_exception().status_code
    assert response.json()["detail"] == token_expired_exception().detail

def test_refresh_invalid_token(client, test_baseuser):
    refresh_token = test_baseuser['refresh_token']
    # Create an invalid refresh token by modifying the original token
    invalid_refresh_token = refresh_token[:-3] # Remove the last 3 characters to make it invalid
    payload = {"refresh_token": invalid_refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_refresh_missing_token(client):
    payload = {} # No refresh token provided
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_refresh_invalid_token_format(client):
    payload = {"refresh_token": "not_a_valid_token_format"}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_refresh_with_a_cloned_valid_token(client, test_baseuser):
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    token_decoded = decode_token(refresh_token)
    token_jti = token_decoded.get("jti")
    token_raw = token_decoded.get("raw")
    token_sub = token_decoded.get("sub")
    # Create a new refresh token with the same jti, raw_code, subject, and with a valid issued at time to simulate a cloned token
    new_refresh_token = create_refresh_token(subject=token_sub, token_id=token_jti, raw_code=token_raw, issued_at=now_tz_aware())
    payload = {"refresh_token": new_refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "gps_token" in response.json()

def test_refresh_token_iat_too_old(client, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    refresh_token_decoded = decode_token(refresh_token)
    token_jti = refresh_token_decoded.get("jti")
    token_raw = refresh_token_decoded.get("raw")
    token_sub = refresh_token_decoded.get("sub")
    assert user.last_reset_done_at is not None
    # Create a refresh token with an issued less than last_reset_done_at to simulate an old token
    iat = user.last_reset_done_at - timedelta(seconds=1) # Set issued at to just before last_reset_done_at
    rtoken_old_iat = create_refresh_token(subject=token_sub, token_id=token_jti, raw_code=token_raw, issued_at=iat)
    payload = {"refresh_token": rtoken_old_iat}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_expired_exception().status_code
    assert response.json()["detail"] == token_expired_exception().detail

def test_refresh_reuse_old_token(client, db_session, test_baseuser, frozen_now):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    old_timestamp_naive = now_tz_naive()
    # We go ahead with time (simulate a delay)
    frozen_now.tick(delta=timedelta(seconds=5))
    new_timestamp_naive = now_tz_naive()
    # First refresh to get a new token
    response1 = client.post("/api/auth/refresh", json=payload)
    assert response1.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    new_refresh_token = response1.json()["refresh_token"]
    assert new_refresh_token != refresh_token
    decoded_token = decode_token(refresh_token)
    decoded_new_token = decode_token(new_refresh_token)
    decoded_token_jti = decoded_token.get("jti")
    decoded_new_token_jti = decoded_new_token.get("jti")
    decoded_token_user_id = decoded_token.get("sub")
    decoded_new_token_user_id = decoded_new_token.get("sub")
    decoded_token_iat = decoded_token.get("iat")
    decoded_new_token_iat = decoded_new_token.get("iat")
    decoded_token_exp = decoded_token.get("exp")
    decoded_new_token_exp = decoded_new_token.get("exp")
    # Curiosity check: it's a refresh (an update), so the jti should be the same for both tokens
    assert decoded_token_jti == decoded_new_token_jti
    # Obviously the user ID should be the same for both tokens
    assert decoded_token_user_id == decoded_new_token_user_id
    assert decoded_token_iat < decoded_new_token_iat
    assert decoded_token_exp < decoded_new_token_exp
    jti_as_uuid = string_as_uuid(decoded_token_jti)
    statement = select(RefreshToken).where(RefreshToken.id == jti_as_uuid)
    db_rtoken: RefreshToken = db_session.exec(statement).first()
    assert db_rtoken is not None
    assert db_rtoken.updated_at > old_timestamp_naive
    assert db_rtoken.updated_at >= new_timestamp_naive
    assert db_rtoken.updated_at < new_timestamp_naive + timedelta(minutes=1) # We check that the updated_at time has been updated to a recent time (within the next minute) to ensure that the token has been refreshed in the database
    assert user.last_refresh_at is not None
    assert user.last_refresh_at > old_timestamp_naive
    assert user.last_refresh_at >= new_timestamp_naive
    assert user.last_refresh_at < new_timestamp_naive + timedelta(minutes=1) # We check that the last_refresh_at time has been updated to a recent time (within the next minute) to ensure that the user's last refresh time has been updated in the database
    # Attempt to reuse the old refresh token
    payload = {"refresh_token": refresh_token}
    # Use the old refresh token to get another new token
    response2 = client.post("/api/auth/refresh", json=payload)
    # We expect a token not valid exception because the old token 
    # has a raw code that doesn't match with the hash stored in the database anymore after the first refresh, 
    # so it should not be valid for a second refresh
    assert response2.status_code == token_not_valid_exception().status_code
    assert response2.json()["detail"] == token_not_valid_exception().detail

def test_refresh_token_user_not_found(client, test_baseuser):
    refresh_token = test_baseuser['refresh_token']
    refresh_token_decoded = decode_token(refresh_token)
    token_raw = refresh_token_decoded.get("raw")
    token_jti = refresh_token_decoded.get("jti")
    token_sub = refresh_token_decoded.get("sub")
    token_wrong_user = str(123456) # Assuming this user ID does not exist in the database
    assert token_sub != token_wrong_user
    # Create a refresh token for a non-existent user
    invalid_refresh_token = create_refresh_token(subject=token_wrong_user, token_id=token_jti, raw_code=token_raw)
    payload = {"refresh_token": invalid_refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_refresh_token_user_not_active(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    # Set the user to inactive
    user.is_active = False
    db_session.commit() # Ensure the updated active status is saved to the database
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_refresh_token_user_is_active(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    assert user.is_active == True
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    assert "access_token" in response.json()
    assert "refresh_token" in response.json()
    assert "gps_token" in response.json()

def test_refresh_token_user_with_negative_reliability_score_for_too_long(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # so that it's not in cooldown anymore, and the reliability score should be reset to a minimal positive value on refresh
    # We simulate a negative reliability score for a long time, so that it should be reset to a minimal positive value on refresh
    user.reliability_score = -50
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token and also reset the reliability score because the cooldown has expired
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    assert user.reliability_score == USER_RELIABILITY_SCORE_INC_VALUE
    # After refresh, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been reset due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_refresh_token_with_negative_reliability_score_in_cooldown(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # but not enough to expire the cooldown, so the reliability score should not be reset on refresh
    # Set a negative reliability score to check that it will not be reset
    user.reliability_score = -50
    # Set the last reliability score time to just before the cooldown expires
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 1) 
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token but should not reset the reliability score because the cooldown has not expired yet
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    assert user.reliability_score == -50 # The reliability score should not be reset because the cooldown has not expired yet
    # After refresh, the last_reliability_score_at should not be updated because the reliability score has not been reset due to the cooldown has not expired yet
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 2)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS)

def test_refresh_token_with_low_reliability_score_for_too_long(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # so that it's not in cooldown anymore, and the reliability score should be increased on refresh
    # We simulate a low reliability score for a long time, so that it should be increased on refresh
    user.reliability_score = 50
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token and also increase the reliability score because the cooldown has expired
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    # The reliability score should be increased by USER_RELIABILITY_SCORE_INC_VALUE
    assert user.reliability_score == 50 + USER_RELIABILITY_SCORE_INC_VALUE 
    # After refresh, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been increased due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_refresh_token_with_low_reliability_score_in_cooldown(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # but not enough to expire the cooldown, so the reliability score should not be increased on refresh
    # Set a low reliability score to check that it will not be increased
    user.reliability_score = 50
    # Set the last reliability score time to just before the cooldown expires
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 1) 
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token but should not increase the reliability score because the cooldown has not expired yet
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    # The reliability score should not be increased because the cooldown has not expired yet
    assert user.reliability_score == 50
    # After refresh, the last_reliability_score_at should not be updated because the reliability score has not been increased due to the cooldown has not expired yet
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 2)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS)

def test_refresh_token_with_low_reliability_score_and_null_timestamp(client, db_session, test_baseuser):
    # If reliability_score is low, but the last_reliability_score_at is None (null timestamp), 
    # we don't increase the reliability score
    user: User = test_baseuser['user']
    user.reliability_score = 50
    user.last_reliability_score_at = None
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    # The reliability score should not be increased because the last_reliability_score_at is None
    assert user.reliability_score == 50
    assert user.last_reliability_score_at is None

def test_refresh_token_with_reliability_score_near_maximum_for_too_long(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # so that it's not in cooldown anymore, and the reliability score should be increased on refresh
    # We simulate a reliability score near maximum for a long time, so that it should be increased on refresh
    user.reliability_score = 90
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS + 1)
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token and also increase the reliability score because the cooldown has expired
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    # The reliability score should be increased by USER_RELIABILITY_SCORE_INC_VALUE, but not exceed 100
    expected_reliability_score = min(90 + USER_RELIABILITY_SCORE_INC_VALUE, 100)
    assert user.reliability_score == expected_reliability_score 
    # After refresh, the last_reliability_score_at should be updated to now, 
    # because the reliability score has been increased due to the cooldown expired
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(minutes=1)

def test_refresh_token_with_reliability_score_near_maximum_in_cooldown(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Set the last reliability score time in the past,
    # but not enough to expire the cooldown, so the reliability score should not be increased on refresh
    # Set a reliability score near maximum to check that it will not be increased
    user.reliability_score = 90
    # Set the last reliability score time to just before the cooldown expires
    user.last_reliability_score_at = now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 1) 
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    # Now we call refresh api, which should refresh the token but should not increase the reliability score because the cooldown has not expired yet
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated reliability score and last_reliability_score_at
    # The reliability score should not be increased because the cooldown has not expired yet
    assert user.reliability_score == 90
    # After refresh, the last_reliability_score_at should not be updated because the reliability score has not been increased due to the cooldown has not expired yet
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at < now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS - 2)
    assert user.last_reliability_score_at > now_tz_naive() - timedelta(days=USER_RELIABILITY_SCORE_WAIT_FOR_INC_DAYS)

def test_refresh_token_with_pending_delete_status(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    # Set the pending_delete_since to a recent past time to simulate a user that is pending deletion
    user.pending_delete_since = now_tz_naive() - timedelta(days=1)
    db_session.commit() # Ensure the updated pending_delete_since is saved to the database
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/refresh", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated pending_delete_since
    # After refresh, the pending_delete_since should be cleared 
    # because the user has refreshed his token (to continue using his account)
    # so he is no longer considered pending deletion
    assert user.pending_delete_since is None
