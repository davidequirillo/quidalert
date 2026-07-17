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
from models.general import User, RefreshToken
from services.security import (
    now_tz_aware,
    create_refresh_token,
    decode_token,
    TOKEN_DECODE_LEEWAY_SECONDS,
)

def test_revoke_successful(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    payload = {"refresh_token": refresh_token}
    response = client.post("/api/auth/revoke", json=payload)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).all()
    # Refresh token will not be deleted but it will be marked as revoked
    assert len(result) == 1
    result_token = result[0]
    assert result_token.is_revoked == True
    assert result_token.fcm_token == None
    assert result_token.fcm_token_updated_at == None

def test_revoke_expired_token(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    refresh_token = test_baseuser['refresh_token']
    refresh_token_decoded = decode_token(refresh_token)
    token_jti = refresh_token_decoded.get("jti")
    token_raw = refresh_token_decoded.get("raw")
    token_sub = refresh_token_decoded.get("sub")
    # Create an expired refresh token 
    exp = timedelta(seconds=-TOKEN_DECODE_LEEWAY_SECONDS - 1) # Set expiration time in the past to simulate an expired token
    iat = now_tz_aware()
    rtoken_expired = create_refresh_token(subject=token_sub, token_id=token_jti, raw_code=token_raw, expires_delta=exp, issued_at=iat)
    payload = {"refresh_token": rtoken_expired}
    response = client.post("/api/auth/revoke", json=payload)
    assert response.status_code == token_expired_exception().status_code
    assert response.json()["detail"] == token_expired_exception().detail
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).all()
    assert len(result) == 1
    result_token = result[0]
    # Refresh token in db remains unchanged (not revoked)
    assert result_token.is_revoked == False

def test_revoke_invalid_token(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    # Create an invalid refresh token by modifying the original token
    invalid_refresh_token = refresh_token[:-3] # Remove the last 3 characters to make it invalid
    payload = {"refresh_token": invalid_refresh_token}
    response = client.post("/api/auth/revoke", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).all()
    assert len(result) == 1
    result_token = result[0]
    # Refresh token in db remains unchanged (not revoked)
    assert result_token.is_revoked == False

def test_revoke_missing_token(client):
    payload = {} # No refresh token provided
    response = client.post("/api/auth/revoke", json=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_revoke_invalid_token_format(client):
    payload = {"refresh_token": "not_a_valid_token_format"}
    response = client.post("/api/auth/revoke", json=payload)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail
