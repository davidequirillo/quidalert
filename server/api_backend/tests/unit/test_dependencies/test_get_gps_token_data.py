# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
import jwt
from fastapi import HTTPException
from core.settings import settings
from models.general import User, GpsTokenData, UserRole
from dependencies import get_geoposition_token_data
from core.exceptions import token_not_valid_exception, token_expired_exception
from services.security import (
    create_geoposition_token,
    GEOPOSITION_TOKEN_TTL_MINUTES,
    JWT_ALGORITHM,
    now_tz_aware)

def test_get_gps_token_data_successful(test_baseuser):
    user: User = test_baseuser['user']
    # Create a valid GPS token for testing using jwt directly to have full control over the payload
    user_id = str(user.id)
    user_is_chief = user.is_chief = True
    user_role = user.role = UserRole.medic.value
    token = create_geoposition_token(
        user_id=user_id, 
        user_is_chief=user_is_chief, 
        user_role=user_role)
    token_data_obj: GpsTokenData = get_geoposition_token_data(token)
    assert token_data_obj.user_id == user_id
    assert token_data_obj.user_is_chief == user_is_chief
    assert token_data_obj.user_role == user_role
    # Another check
    user_is_chief = user.is_chief = False
    user_role = user.role = UserRole.policeman.value
    token = create_geoposition_token(
        user_id=user_id, 
        user_is_chief=user_is_chief, 
        user_role=user_role)
    token_data_obj: GpsTokenData = get_geoposition_token_data(token)
    assert token_data_obj.user_is_chief == user_is_chief
    assert token_data_obj.user_role == user_role
    assert token_data_obj.user_id == user_id

def test_get_gps_token_data_expired(test_baseuser):
    user: User = test_baseuser['user']
    # Create an expired GPS token for testing using jwt directly to have full control over the payload
    user_id = str(user.id)
    user_is_chief = user.is_chief
    user_role = user.role
    token = create_geoposition_token(
        user_id=user_id, 
        user_is_chief=user_is_chief, 
        user_role=user_role,
        expires_delta=timedelta(minutes=-1))
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for an expired token"
    except HTTPException as e:
        assert e.status_code == token_expired_exception().status_code
        assert e.detail == token_expired_exception().detail

def test_get_gps_token_data_iat_in_the_future(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with an "iat" in the future for testing using jwt directly to have full control over the payload
    user_id = str(user.id)
    user_is_chief = user.is_chief
    user_role = user.role
    token = create_geoposition_token(
        user_id=user_id, 
        user_is_chief=user_is_chief, 
        user_role=user_role,
        issued_at=now_tz_aware() + timedelta(minutes=10))
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with 'iat' in the future"
    except HTTPException as e:
        assert e.status_code == token_expired_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_create_gps_token_data_invalid_token(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with an invalid user_id (e.g., empty string)
    token = "invalidtoken"
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with an invalid user_id"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_create_gps_token_data_type_missing(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with the "type" claim missing
    user_id = str(user.id)
    user_is_chief = user.is_chief
    user_role = user.role
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        # "type" is intentionally missing
        "user_is_chief": user_is_chief,
        "user_role": user_role
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with the 'type' claim missing"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_get_gps_token_data_type_invalid(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with an invalid "type" claim
    user_id = str(user.id)
    user_is_chief = user.is_chief
    user_role = user.role
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": "invalid-type",  # invalid type
        "user_is_chief": user_is_chief,
        "user_role": user_role
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with an invalid 'type' claim"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_get_gps_token_data_missing_user_id(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with the "sub" claim missing
    user_is_chief = user.is_chief
    user_role = user.role
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        # "sub" is intentionally missing
        "iat": iat,
        "exp": exp,
        "type": "gps-update",
        "user_is_chief": user_is_chief,
        "user_role": user_role
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with the 'sub' claim missing"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_get_gps_token_data_user_id_empty(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with an empty "sub" claim
    user_is_chief = user.is_chief
    user_role = user.role
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        "sub": "",  # empty user_id
        "iat": iat,
        "exp": exp,
        "type": "gps-update",
        "user_is_chief": user_is_chief,
        "user_role": user_role
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with an empty 'sub' claim"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_get_gps_token_data_missing_user_is_chief(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with the "user_is_chief" claim missing
    user_id = str(user.id)
    user_role = user.role
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": "gps-update",
        # "user_is_chief" is intentionally missing
        "user_role": user_role
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with the 'user_is_chief' claim missing"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail

def test_get_gps_token_data_missing_user_role(test_baseuser):
    user: User = test_baseuser['user']
    # Create a GPS token with the "user_role" claim missing
    user_id = str(user.id)
    user_is_chief = user.is_chief
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES)
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": "gps-update",
        "user_is_chief": user_is_chief,
        # "user_role" is intentionally missing
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        get_geoposition_token_data(token)
        assert False, "Expected HTTPException for a token with the 'user_role' claim missing"
    except HTTPException as e:
        assert e.status_code == token_not_valid_exception().status_code
        assert e.detail == token_not_valid_exception().detail
