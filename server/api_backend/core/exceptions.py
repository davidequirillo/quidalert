# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import HTTPException, Response, status

def token_not_valid_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token not valid",
        headers={"WWW-Authenticate": "Bearer"})

def token_expired_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Token expired",
        headers={"WWW-Authenticate": "Bearer"})

def credentials_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="Invalid credentials")

def two_factor_locked_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="2FA locked")

def two_factor_not_valid_exception():
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail="2FA code not valid")

def permission_exception():
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail="Permission denied")

def two_factor_required_response(): # Note: this is not an exception, but a response
    return Response(
        status_code=status.HTTP_401_UNAUTHORIZED,
        content="2FA required")