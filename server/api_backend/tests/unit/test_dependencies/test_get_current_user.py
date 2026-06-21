# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
import jwt
from fastapi import HTTPException
from core.settings import settings
from models.general import User
from dependencies import get_current_user
from core.exceptions import token_not_valid_exception, token_expired_exception
from services.security import (
    create_access_token,
    ACCESS_TOKEN_TTL_MINUTES,
    JWT_ALGORITHM, 
    now_tz_aware)

def test_get_current_user_success(db_session, test_baseuser):
    user: User = test_baseuser['user']
    token = create_access_token(subject=str(user.id))
    result = get_current_user(access_token=token, db_session=db_session)
    assert type(result) == User
    assert result.id == user.id

def test_get_current_user_invalid_token(db_session):
    token = "invalidtoken"
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_expired_token(db_session, test_baseuser):
    user: User = test_baseuser['user']
    token = create_access_token(subject=str(user.id), expires_delta=timedelta(seconds=-1))
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_expired_exception().status_code
        assert e.detail == token_expired_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_invalid_iat(db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Create a token with an "iat" in the future
    token = create_access_token(subject=str(user.id), issued_at=now_tz_aware() + timedelta(minutes=10))
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_missing_user_id(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    # Create a token without the "sub" claim
    iat = now_tz_aware()
    exp = now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    token_type = "access"
    payload = {
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_missing_iat(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    # Create a token without the "iat" claim
    exp = now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    token_type = "access"
    payload = {
        "sub": str(user.id),
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_missing_exp(db_session, test_baseuser):
    user: User = test_baseuser['user']
    iat = now_tz_aware()
    token_type = "access"
    payload = {
        "sub": str(user.id),
        "iat": iat,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_missing_type(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    # Create a token without the "type" claim
    iat = now_tz_aware()
    exp = now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    payload = {
        "sub": str(user.id),
        "iat": iat,
        "exp": exp
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_invalid_user_id(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    # Create a token with an invalid user ID (not a valid UUID)
    invalid_user_id = "invalid-uuid"
    token = create_access_token(subject=invalid_user_id)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_invalid_type_claim(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    # Create a token with an invalid "type" claim
    iat = now_tz_aware()
    exp = now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES)
    token_type = "invalid-type"
    payload = {
        "sub": str(user.id),
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_valid_token(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None, "Test setup error: the test user should have a valid ID"
    payload = {
        "sub": str(user.id),
        "iat": now_tz_aware(),
        "exp": now_tz_aware() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES),
        "type": "access"
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    result = get_current_user(access_token=token, db_session=db_session)
    assert type(result) == User
    assert result.id == user.id

def test_get_current_user_nonexistent_user(db_session, test_baseuser):
    user: User = test_baseuser['user']
    wrong_id = "00000000-0000-0000-0000-000000000000"  # UUID that does not exist in the database
    assert str(user.id) != wrong_id, "Test setup error: the wrong_id should not match the test user ID"
    token = create_access_token(subject=wrong_id)
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_blocked_user(db_session, test_baseuser):
    user: User = test_baseuser['user']
    user.is_blocked = True
    db_session.add(user)
    db_session.commit()
    token = create_access_token(subject=str(user.id))
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_blocked_user_but_superuser(db_session, test_superuser):
    user: User = test_superuser['user']
    user.is_blocked = True
    db_session.add(user)
    db_session.commit()
    token = create_access_token(subject=str(user.id))
    result = get_current_user(access_token=token, db_session=db_session)
    assert type(result) == User
    assert result.id == user.id
    assert result.is_blocked == False  # The superuser should be unblocked by the function

def test_get_current_user_token_issued_before_last_reset(db_session, test_baseuser):
    user: User = test_baseuser['user']
    # Simulate a token issued before the last reset
    token = create_access_token(subject=str(user.id), issued_at=user.last_reset_done_at - timedelta(minutes=1))    
    try:
        get_current_user(access_token=token, db_session=db_session)
    except HTTPException as e:
        assert e.status_code == token_expired_exception().status_code
        assert e.detail == token_expired_exception().detail
    except Exception as e:
        assert False, f"Unexpected exception type: {type(e)}"

def test_get_current_user_superuser_cannot_be_downgraded(db_session, test_superuser):
    user: User = test_superuser['user']
    user.is_admin = False
    user.is_reliable = False
    user.reliability_score = 50
    user.is_blocked = True
    assert user.is_superuser == True, "Test setup error: the test user should be a superuser"
    # Create a token for the superuser
    token = create_access_token(subject=str(user.id))
    # Call get_current_user to trigger the logic that checks if the superuser has been downgraded, 
    # and if so, restores their privileges
    result = get_current_user(access_token=token, db_session=db_session)
    assert type(result) == User
    assert result.id == user.id
    assert result.is_admin == True
    assert result.is_reliable == True
    assert result.reliability_score == 100
    assert result.is_blocked == False
    db_session.refresh(user) # Refresh the user from the database to ensure we have the latest state
    assert user.is_admin == True
    assert user.is_reliable == True
    assert user.reliability_score == 100
    assert user.is_blocked == False
