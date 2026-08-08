# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import jwt
from datetime import timedelta
from core.settings import settings
from services.security import (
    TokenExpiredException,
    TokenNotValidException,
    now_tz_aware,
    decode_token, 
    JWT_ALGORITHM)

def test_decode_token_successful():
    # Create a valid token for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    decoded_payload = decode_token(token)
    assert decoded_payload["sub"] == user_id
    assert decoded_payload["type"] == token_type
    assert decoded_payload["iat"] == int(iat.timestamp())
    assert decoded_payload["exp"] == int(exp.timestamp())
    assert decoded_payload["exp"] >= int((now_tz_aware() + timedelta(minutes=59)).timestamp()) # allow some leeway for timing
    assert decoded_payload["exp"] <= int((now_tz_aware() + timedelta(minutes=61)).timestamp())
    assert decoded_payload["iat"] <= int(now_tz_aware().timestamp())
    assert decoded_payload["iat"] >= int((now_tz_aware() - timedelta(minutes=1)).timestamp()) # allow some leeway for timing

def test_decode_token_expired():
    # Create an expired token for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware() - timedelta(minutes=61)  # issued 61 minutes ago
    exp = iat + timedelta(minutes=60)  # expired 1 minute ago
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        decode_token(token)
        assert False, "Expected TokenExpiredException"
    except TokenExpiredException:
        pass

def test_decode_token_issued_at_in_future():
    # Create a token with issued at in the future for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware() + timedelta(minutes=10)  # issued 10 minutes in the future
    exp = iat + timedelta(minutes=60)  # expires 70 minutes in the future
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    try:
        decode_token(token)
        assert False, "Expected TokenNotValidException for a token with iat in the future"
    except TokenNotValidException:
        pass

def test_decode_token_invalid_signature():
    # Create a token with an invalid signature
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    # Encode the token with the wrong secret key to create an invalid signature
    token = jwt.encode(payload, "wrongsecretkey", algorithm=JWT_ALGORITHM)
    # ...but the decode_token function uses the correct secret key
    try:
        decode_token(token)
        assert False, "Expected TokenNotValidException"
    except TokenNotValidException:
        pass

def test_decode_token_malformed_token():
    # Create a malformed token (not a valid JWT)
    malformed_token = "this.is.not.a.valid.token"
    try:
        decode_token(malformed_token)
        assert False, "Expected TokenNotValidException for a malformed token"
    except TokenNotValidException:
        pass

def test_decode_altered_token():
    # Create a valid token for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    # Alter the token by changing one character (this will break the signature)
    # We alter the last characters of the token, removing them
    altered_token = token[:-3]
    try:
        decode_token(altered_token)
        assert False, "Expected TokenNotValidException for an altered token"
    except TokenNotValidException:
        pass
    # We alter the first character of the token
    altered_token = ("A" if token[0] != "A" else "B") + token[1:]
    try:        
        decode_token(altered_token)
        assert False, "Expected TokenNotValidException for an altered token"
    except TokenNotValidException:
        pass
    # We alter a character in the middle of the token
    middle_index = len(token) // 2
    altered_token = token[:middle_index] + ("A" if token[middle_index] != "A" else "B") + token[middle_index+1:]
    try:        
        decode_token(altered_token)
        assert False, "Expected TokenNotValidException for an altered token"
    except TokenNotValidException:
        pass

def test_decode_altered_payload():
    # Create a valid token for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    # Decode the token to get the payload, then alter it and re-encode it
    # We use a wrong key, because an attacker would not be able to re-sign the token with the correct key, so we want to simulate that
    decoded_token = decode_token(token)
    decoded_token["sub"] = "attacker123"
    altered_token = jwt.encode(decoded_token, "wrongsecretkey", algorithm=JWT_ALGORITHM)
    # The decoding function will use the correct secret key, so it will detect that the signature does not match the altered payload
    try:
        decode_token(altered_token)
        assert False, "Expected TokenNotValidException for an altered payload"
    except TokenNotValidException:
        pass

def test_decode_token_with_wrong_algorithm():
    # Create a token using a different algorithm (e.g. HS384 instead of HS256)
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    # Encode the token using a different algorithm
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm="HS384")
    try:
        decode_token(token)
        assert False, "Expected TokenNotValidException for a token with the wrong algorithm"
    except TokenNotValidException:
        pass

def test_decode_token_different_payload_different_signature():
    # Create a valid token for testing using jwt directly to have full control over the payload
    user_id = "user123"
    iat = now_tz_aware()
    exp = iat + timedelta(minutes=60)
    token_type = "token_test"
    payload = {
        "sub": user_id,
        "iat": iat,
        "exp": exp,
        "type": token_type
    }
    token = jwt.encode(payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    token_signature = token.rsplit('.', 1)[-1]
    # Create a different payload with the same user_id but different type and timestamps
    different_payload = {
        "sub": user_id,
        "iat": iat - timedelta(minutes=5),  # different issued at
        "exp": exp + timedelta(minutes=6),  # different expiration
        "type": "different_type"  # different type
    }
    # Encode the different payload with the same secret key to get a different token
    different_token = jwt.encode(different_payload, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    different_token_signature = different_token.rsplit('.', 1)[-1]
    # The signatures should be different because the payload is different
    assert token_signature != different_token_signature
    # Now we decode the two tokens and check that they have the expected payloads
    decoded_original_payload = decode_token(token)
    assert decoded_original_payload["sub"] == user_id
    assert decoded_original_payload["type"] == token_type
    decoded_different_payload = decode_token(different_token)
    assert decoded_different_payload["sub"] == user_id
    assert decoded_different_payload["type"] == "different_type"
    # The issued at and expiration should be different between the two tokens
    assert decoded_different_payload["iat"] != decoded_original_payload["iat"]
    assert decoded_different_payload["exp"] != decoded_original_payload["exp"]
