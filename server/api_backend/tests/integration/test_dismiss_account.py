# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_expired_exception, 
    token_not_valid_exception,
    forbidden_exception
)
from models.general import User, RefreshToken
from services.security import (
    now_tz_naive,
    create_access_token,
    decode_token,
    ACCESS_TOKEN_TTL_MINUTES,
    TOKEN_DECODE_LEEWAY_SECONDS,
)

def test_dismiss_account_user_not_authorized(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    # We alter the access token to make it invalid
    access_token = access_token[:-3] # Remove the last 3 characters to make it invalid
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).first()
    assert result is not None
    assert (result.fcm_token is None) or (result.fcm_token != "test_fcm_token")

def test_dismiss_account_access_token_expired(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    access_token = test_baseuser['access_token']
    decoded_access_token = decode_token(access_token)
    token_sub = decoded_access_token.get("sub")
    # Create an expired access token
    expired_access_token = create_access_token(subject=token_sub, expires_delta=timedelta(seconds=-TOKEN_DECODE_LEEWAY_SECONDS - 1))
    headers = {"Authorization": f"Bearer {expired_access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == token_expired_exception().status_code
    assert response.json()["detail"] == token_expired_exception().detail

def test_dismiss_account_user_not_found(client, test_baseuser):
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
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_dismiss_account_called_by_superuser(client, db_session, test_superuser):
    superuser: User = test_superuser['user']
    assert superuser is not None
    access_token = test_superuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
    db_session.refresh(superuser) # Refresh the superuser instance to get the updated refresh token
    assert superuser.pending_delete_since is None  # The pending_delete_since should not be set for superusers

def test_dismiss_account_called_by_admin(client, db_session, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
    db_session.refresh(admin) # Refresh the admin instance to get the updated refresh token
    assert admin.pending_delete_since is None  # The pending_delete_since should not be set for admins

def test_dismiss_account_called_by_officer(client, db_session, test_officer):
    officer: User = test_officer['user']
    assert officer is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
    db_session.refresh(officer) # Refresh the officer instance to get the updated refresh token
    assert officer.pending_delete_since is None  # The pending_delete_since should not be set for officers

def test_dismiss_account_success(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    assert refresh_token is not None
    assert user.id is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.post("/api/dismiss-account", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user) # Refresh the user instance to get the updated refresh token
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    result = db_session.exec(statement).first()
    assert result is not None
    # The refresh token should be marked as revoked after dismissing the account
    assert result.is_revoked == True
    # The FCM token should be cleared after dismissing the account
    assert result.fcm_token == None
    assert result.fcm_token_updated_at == None
    assert user.pending_delete_since is not None  # The pending_delete_since should be set after dismissing the account
    assert user.pending_delete_since > now_tz_naive() - timedelta(seconds=5) # the pending_delete_since should be set to now, with a small margin of error
    assert user.pending_delete_since < now_tz_naive() + timedelta(seconds=5) # the pending_delete_since should be set to now, with a small margin of error
