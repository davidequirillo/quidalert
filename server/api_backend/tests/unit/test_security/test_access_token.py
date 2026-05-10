# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from services.security import (
    TokenExpiredException,
    now_tz_naive,
    from_datetime_to_timestamp,
    ACCESS_TOKEN_TTL_MINUTES,
    decode_token,
    create_access_token)

def test_create_access_token_successful():
    token = create_access_token(subject="id123")
    decoded = decode_token(token)
    sub = decoded["sub"]
    assert sub == "id123"
    exp = decoded["exp"]
    assert exp >= from_datetime_to_timestamp(now_tz_naive() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES - 1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_naive() + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES + 1))
    iat = decoded["iat"]
    assert iat <= from_datetime_to_timestamp(now_tz_naive())
    assert iat >= from_datetime_to_timestamp(now_tz_naive() - timedelta(minutes=1)) # issued in the past, allow some leeway
    assert decoded["type"] == "access"

def test_create_access_token_with_custom_exp():
    custom_exp_delta = timedelta(minutes=30)
    token = create_access_token(subject="id123", expires_delta=custom_exp_delta)
    decoded = decode_token(token)
    exp = decoded["exp"]
    assert exp >= from_datetime_to_timestamp(now_tz_naive() + custom_exp_delta - timedelta(minutes=1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_naive() + custom_exp_delta + timedelta(minutes=1))
    assert decoded["type"] == "access"

def test_create_access_token_with_custom_iat():
    token = create_access_token(subject="id123", issued_at=now_tz_naive()-timedelta(minutes=5))
    decoded = decode_token(token)
    sub = decoded["sub"]
    assert sub == "id123"
    exp = decoded["exp"]
    assert exp >= from_datetime_to_timestamp(now_tz_naive() - timedelta(minutes=5) + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES-1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_naive() - timedelta(minutes=5) + timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES+1))
    iat = decoded["iat"]
    assert iat <= from_datetime_to_timestamp(now_tz_naive() - timedelta(minutes=5))
    assert iat >= from_datetime_to_timestamp(now_tz_naive() - timedelta(minutes=6)) # issued in the past, allow some leeway
    assert decoded["type"] == "access"

def test_create_access_token_expired():
    # Create an access token that is already expired
    token = create_access_token(subject="id123", issued_at=now_tz_naive() - timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES + 10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an expired token"
    except TokenExpiredException:
        assert True  # expected outcome

def test_create_access_token_with_iat_in_the_future():
    # Create an access token with an "iat" in the future
    token = create_access_token(subject="id123", issued_at=now_tz_naive() + timedelta(minutes=10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an invalid 'iat' claim"
    except Exception:
        assert True  # expected outcome
