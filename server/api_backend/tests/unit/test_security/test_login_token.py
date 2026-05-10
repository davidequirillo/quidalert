# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from models.general import User
from services.security import (
    TokenExpiredException,
    now_tz_naive,
    LOGIN_TOKEN_TTL_MINUTES,
    decode_token,
    create_login_token)
from api import check_login_token

def test_create_login_token_successful():
    # Create a valid login token for testing with default TTL
    token = create_login_token(subject="id123")
    decoded = decode_token(token)
    sub = decoded["sub"]
    assert sub == "id123"
    exp = decoded["exp"]
    assert exp >= int((now_tz_naive() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES - 1)).timestamp()) # allow some leeway for timing
    assert exp <= int((now_tz_naive() + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES + 1)).timestamp())
    iat = decoded["iat"]
    assert iat <= int(now_tz_naive().timestamp())
    assert iat >= int((now_tz_naive() - timedelta(minutes=1)).timestamp())  # issued in the past, allow some leeway
    assert decoded["type"] == "login"

def test_create_login_token_with_custom_exp():
    # Create a valid login token for testing with custom expiration time
    custom_exp_delta = timedelta(minutes=30)
    token = create_login_token(subject="id123", expires_delta=custom_exp_delta)
    decoded = decode_token(token)
    exp = decoded["exp"]
    assert exp >= int((now_tz_naive() + custom_exp_delta - timedelta(minutes=1)).timestamp()) # allow some leeway for timing
    assert exp <= int((now_tz_naive() + custom_exp_delta + timedelta(minutes=1)).timestamp())
    assert decoded["type"] == "login"

def test_create_login_token_with_custom_iat():
    # Create a valid login token for testing with custom issued_at
    token = create_login_token(subject="id123", issued_at=now_tz_naive()-timedelta(minutes=5))
    decoded = decode_token(token)
    sub = decoded["sub"]
    assert sub == "id123"
    exp = decoded["exp"]
    assert exp >= int((now_tz_naive() - timedelta(minutes=5) + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES-1)).timestamp()) # allow some leeway for timing
    assert exp <= int((now_tz_naive() - timedelta(minutes=5) + timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES+1)).timestamp())
    iat = decoded["iat"]
    assert iat <= int((now_tz_naive() - timedelta(minutes=5)).timestamp())
    assert iat >= int((now_tz_naive() - timedelta(minutes=6)).timestamp()) # issued in the past, allow some leeway
    assert decoded["type"] == "login"

def test_create_login_token_expired():
    # Create a login token that is already expired
    token = create_login_token(subject="id123", issued_at=now_tz_naive() - timedelta(minutes=LOGIN_TOKEN_TTL_MINUTES + 10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an expired token"
    except TokenExpiredException:
        assert True  # expected outcome

def test_create_login_token_with_iat_in_the_future():
    # Create a login token with an "iat" in the future
    token = create_login_token(subject="id123", issued_at=now_tz_naive() + timedelta(minutes=10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an invalid 'iat' claim"
    except Exception:
        assert True  # expected outcome

def test_check_login_token_successful(test_baseuser):
    user: User = test_baseuser['user']
    # Create a valid login token and check it successfully
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    result = check_login_token(token_data, user)
    assert result == True    

def test_check_login_token_is_none(test_baseuser):
    user: User = test_baseuser['user']
    token_data = None
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_sub_missing(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    del token_data['sub']
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_iat_missing(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    del token_data['iat']
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_exp_missing(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    del token_data['exp']
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_type_missing(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    del token_data['type']
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_type_wrong(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    token_data['type'] = 'access'
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_token_sub_wrong(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    token_data['sub'] = 'wrong_id'
    result = check_login_token(token_data, user)
    assert result == False

def test_check_login_iat_too_old(test_baseuser):
    user: User = test_baseuser['user']
    token = test_baseuser['login_token']
    token_data = decode_token(token)
    # Set iat to a time before the user's last password reset, which should invalidate the token
    user.last_reset_done_at = now_tz_naive() - timedelta(minutes=7)
    token_data['iat'] = int((user.last_reset_done_at - timedelta(minutes=1)).timestamp())
    result = check_login_token(token_data, user)
    assert result == False
    # Set iat to a time before the user's last successful 2fa
    user.last_2fa_success_at = now_tz_naive() - timedelta(minutes=10)
    token_data['iat'] = int((user.last_2fa_success_at - timedelta(minutes=1)).timestamp())
    result = check_login_token(token_data, user)
    assert result == False
