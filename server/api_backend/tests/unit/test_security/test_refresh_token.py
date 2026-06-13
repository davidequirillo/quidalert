# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from sqlmodel import select
from models.general import string_as_uuid, User, RefreshToken
from services.security import (
    TokenExpiredException,
    TokenNotValidException,
    now_tz_naive,
    now_tz_aware,
    ensure_tz_aware,
    from_datetime_to_timestamp,
    REFRESH_TOKEN_TTL_MINUTES,
    decode_token,
    create_refresh_token,
    generate_random_token,
    check_token_against_hash)
from api import check_refresh_token

def test_create_refresh_token_successful():
    user_id = "id123"
    token_id = "tokenid123"
    raw_code = generate_random_token()
    token = create_refresh_token(subject=user_id, token_id=token_id, raw_code=raw_code)
    decoded = decode_token(token)
    assert decoded['raw'] == raw_code
    assert decoded['sub'] == user_id
    assert decoded['jti'] == token_id
    assert decoded['type'] == "refresh"
    exp = decoded['exp']
    iat = decoded['iat']
    assert exp >= from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES - 1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES + 1))
    assert iat <= from_datetime_to_timestamp(now_tz_aware())
    assert iat >= from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=1)) # issued in the past, allow some leeway

def test_create_refresh_token_with_custom_exp():
    user_id = "id123"
    token_id = "tokenid123"
    raw_code = generate_random_token()
    custom_exp_delta = timedelta(minutes=30)
    token = create_refresh_token(subject=user_id, token_id=token_id, raw_code=raw_code, expires_delta=custom_exp_delta)
    decoded = decode_token(token)
    exp = decoded['exp']
    assert exp >= from_datetime_to_timestamp(now_tz_aware() + custom_exp_delta - timedelta(minutes=1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_aware() + custom_exp_delta + timedelta(minutes=1))
    assert decoded['type'] == "refresh"

def test_create_refresh_token_with_custom_iat():
    user_id = "id123"
    token_id = "tokenid123"
    raw_code = generate_random_token()
    token = create_refresh_token(subject=user_id, token_id=token_id, raw_code=raw_code, issued_at=now_tz_aware()-timedelta(minutes=5))
    decoded = decode_token(token)
    sub = decoded["sub"]
    assert sub == user_id
    exp = decoded["exp"]
    assert exp >= from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=5) + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES-1)) # allow some leeway for timing
    assert exp <= from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=5) + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES+1))
    iat = decoded["iat"]
    assert iat <= from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=5))
    assert iat >= from_datetime_to_timestamp(now_tz_aware() - timedelta(minutes=6)) # issued in the past, allow some leeway
    assert decoded["type"] == "refresh"

def test_create_refresh_token_expired():
    # Create a refresh token that is already expired
    user_id = "id123"
    token_id = "tokenid123"
    raw_code = generate_random_token()
    token = create_refresh_token(subject=user_id, token_id=token_id, raw_code=raw_code, issued_at=now_tz_aware() - timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES + 10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an expired token"
    except TokenExpiredException:
        assert True  # expected outcome

def test_create_refresh_token_with_iat_in_the_future():
    # Create a refresh token with an "iat" in the future
    user_id = "id123"
    token_id = "tokenid123"
    raw_code = generate_random_token()
    token = create_refresh_token(subject=user_id, token_id=token_id, raw_code=raw_code, issued_at=now_tz_aware() + timedelta(minutes=10))
    try:
        decode_token(token)
        assert False, "Expected decode_token to raise an exception for an invalid 'iat' claim"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_successful(db_session, test_baseuser):
    user: User = test_baseuser['user']
    refresh_token = test_baseuser['refresh_token']
    user_id = str(user.id)
    refresh_token_data = decode_token(refresh_token)
    token_id = refresh_token_data['jti']
    raw_code = refresh_token_data['raw']
    token_user_id = refresh_token_data['sub']
    assert token_user_id == user_id
    # Check refresh token returns the relative user and refresh token from the database
    db_user, db_rtoken = check_refresh_token(
        token_data=refresh_token_data, db_session=db_session
    )
    assert str(db_user.id) == user_id
    assert str(db_rtoken.id) == token_id
    assert db_rtoken.raw_hash is not None
    assert str(db_rtoken.user_id) == user_id
    assert check_token_against_hash(raw_code, db_rtoken.raw_hash) == True

def test_check_refresh_token_data_is_none(db_session):
    try:
        check_refresh_token(token_data=None, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is None"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_data_missing_sub(db_session):
    # Create token data with missing "sub" field
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        # "sub" is missing
        "jti": "tokenid123",
        "raw": "rawcode123",
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing 'sub' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_data_missing_jti(db_session):
    # Create token data with missing "jti" field
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        "sub": "id123",
        # "jti" is missing
        "raw": "rawcode123",
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing 'jti' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_data_missing_type(db_session):
    # Create token data with missing "type" field
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        "sub": "id123",
        "jti": "tokenid123",
        "raw": "rawcode123",
        # "type" is missing
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing 'type' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_data_wrong_type(db_session):
    # Create token data with wrong "type" field
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        "sub": "id123",
        "jti": "tokenid123",
        "raw": "rawcode123",
        "type": "access",  # should be "refresh"
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data has wrong 'type' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_data_missing_raw(db_session):
    # Create token data with missing fields
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        "sub": "id123",
        "jti": "tokenid123",
        # "raw" is missing
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing required fields"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_missing_iat(db_session):
    # Create token data with missing "iat" field
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    token_data = {
        "sub": "id123",
        "jti": "tokenid123",
        "raw": "rawcode123",
        "type": "refresh",
        "exp": exp,
        # "iat" is missing
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing 'iat' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_missing_exp(db_session):
    # Create token data with missing "exp" field
    iat = from_datetime_to_timestamp(now_tz_aware())
    token_data = {
        "sub": "id123",
        "jti": "tokenid123",
        "raw": "rawcode123",
        "type": "refresh",
        "iat": iat
        # "exp" is missing
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when token_data is missing 'exp' field"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_user_not_found_in_db(db_session, test_baseuser):
    # Create token data for a user that does not exist in the database
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    iat = from_datetime_to_timestamp(now_tz_aware())
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    token_data = {
        "sub": user_id[:-1] + ("9" if user_id[-1] != "9" else "8"),  # modify user_id to make it not found
        "jti": token_id,
        "raw": token_raw,
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when user is not found in the database"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_iat_too_old(db_session, test_baseuser):
    # Create token data with "iat" too old
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    # simulate a password reset done 20 minutes ago
    user.last_reset_done_at = now_tz_naive() - timedelta(minutes=20)
     # issued 10 minutes before the last reset, which is too old
    iat = from_datetime_to_timestamp(ensure_tz_aware(user.last_reset_done_at) - timedelta(minutes=10))
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    token_data = {
        "sub": user_id,
        "jti": token_id,
        "raw": token_raw,
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception for an 'iat' that is too old"
    except TokenExpiredException:
        assert True  # expected outcome

def test_check_refresh_token_jti_not_found_in_db(db_session, test_baseuser):
    # Create token data with "jti" that does not exist in the database
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    iat = from_datetime_to_timestamp(now_tz_aware())
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    token_data = {
        "sub": user_id,
        "jti": token_id[:-1] + ("9" if token_id[-1] != "9" else "8"),  # modify jti to make it not found
        "raw": token_raw,
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when 'jti' is not found in the database"
    except TokenNotValidException: # if jti is not found, we consider the token as expired
        assert True  # expected outcome

def test_check_refresh_token_is_revoked(db_session, test_baseuser):
    # Create token data for a refresh token that is revoked in the database
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    iat = from_datetime_to_timestamp(now_tz_aware())
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    # Mark the refresh token as revoked in the database
    token_in_db = db_session.exec(select(RefreshToken).where(RefreshToken.id == string_as_uuid(token_id))).first()
    token_in_db.is_revoked = True
    db_session.add(token_in_db)
    db_session.commit()
    token_data = {
        "sub": user_id,
        "jti": token_id,
        "raw": token_raw,
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception for a revoked refresh token"
    except TokenExpiredException: # if the token is revoked, we consider it as expired
        assert True  # expected outcome

def test_check_refresh_token_raw_code_does_not_match_hash_in_db(db_session, test_baseuser):
    # Create token data for a refresh token whose raw code does not match the hash stored in the database
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    iat = from_datetime_to_timestamp(now_tz_aware())
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    # Modify the raw code so that it does not match the hash in the database
    modified_raw_code = token_raw[:-1] + ("9" if token_raw[-1] != "9" else "8")
    token_data = {
        "sub": user_id,
        "jti": token_id,
        "raw": modified_raw_code,  # use the modified raw code
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }       
    try:
        check_refresh_token(token_data=token_data, db_session=db_session)
        assert False, "Expected check_refresh_token to raise an exception when the raw code does not match the hash in the database"
    except TokenNotValidException:
        assert True  # expected outcome

def test_check_refresh_token_all_fields_valid(db_session, test_baseuser):
    # Create token data for a refresh token that is valid and matches the database
    user: User = test_baseuser['user']
    token: RefreshToken = test_baseuser['refresh_token']
    token_decoded = decode_token(token)
    token_id = token_decoded['jti']
    token_raw = token_decoded['raw']
    user_id = str(user.id)
    iat = from_datetime_to_timestamp(now_tz_aware())
    exp = from_datetime_to_timestamp(now_tz_aware() + timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    token_data = {
        "sub": user_id,
        "jti": token_id,
        "raw": token_raw,
        "type": "refresh",
        "iat": iat,
        "exp": exp
    }
    db_user, db_rtoken = check_refresh_token(token_data=token_data, db_session=db_session)
    assert str(db_user.id) == user_id
    assert str(db_rtoken.id) == token_id
    assert db_rtoken.raw_hash is not None
    assert str(db_rtoken.user_id) == user_id
    assert check_token_against_hash(token_raw, db_rtoken.raw_hash) == True
