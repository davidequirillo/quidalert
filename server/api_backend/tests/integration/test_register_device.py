# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_expired_exception, 
    token_not_valid_exception,
    invalid_request_exception
)
from models.general import User, RefreshToken
from services.security import (
    create_access_token,
    decode_token,
    ACCESS_TOKEN_TTL_MINUTES,
    TOKEN_DECODE_LEEWAY_SECONDS,
)

def test_register_device_user_not_authorized(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    # We alter the access token to make it invalid
    access_token = access_token[:-3] # Remove the last 3 characters to make it invalid
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"fcm_token": "test_fcm_token"}
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).first()
    assert result is not None
    assert (result.fcm_token is None) or (result.fcm_token != "test_fcm_token")

def test_register_device_access_token_expired(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    access_token = test_baseuser['access_token']
    decoded_access_token = decode_token(access_token)
    token_sub = decoded_access_token.get("sub")
    # Create an expired access token
    expired_access_token = create_access_token(subject=token_sub, expires_delta=timedelta(seconds=-TOKEN_DECODE_LEEWAY_SECONDS - 1))
    headers = {"Authorization": f"Bearer {expired_access_token}"}
    payload = {"fcm_token": "test_fcm_token"}
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == token_expired_exception().status_code
    assert response.json()["detail"] == token_expired_exception().detail

def test_register_device_fcm_token_missing(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {} # No fcm_token provided
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = {"fcm_token": ""} # Empty fcm_token provided
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == invalid_request_exception("FCM token is required").status_code
    assert response.json()["detail"] == invalid_request_exception("FCM token is required").detail

def test_register_device_user_not_found(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    access_token = test_baseuser['access_token']
    # We create a token with a non-existent user id
    decoded_access_token = decode_token(access_token)
    token_sub = decoded_access_token.get("sub")
    fake_user_id = "00000000-0000-0000-0000-000000000000"
    assert token_sub != fake_user_id
    expired_access_token = create_access_token(subject=fake_user_id, expires_delta=timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    headers = {"Authorization": f"Bearer {expired_access_token}"}
    payload = {"fcm_token": "test_fcm_token"}
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_register_device_success(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    assert refresh_token is not None
    assert user.id is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    payload = {"fcm_token": "test_fcm_token"}
    response = client.post("/api/register-device", json=payload, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).first()
    assert result is not None
    assert result.fcm_token == "test_fcm_token"
