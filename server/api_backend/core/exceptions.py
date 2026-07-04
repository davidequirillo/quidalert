# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import HTTPException, status

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

def forbidden_exception(detail: str = "Forbidden request"):
    return HTTPException(
        status_code=status.HTTP_403_FORBIDDEN,
        detail=detail)

def file_too_large_exception(max_size: int):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=f"File too large. Maximum allowed size is {max_size} bytes")

def unsafe_file_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Unsafe file upload detected")

def bad_file_upload_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Bad file upload")

def invalid_file_type_exception():
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail="Invalid file type")

def invalid_request_exception(detail: str = "Invalid request"):
    return HTTPException(
        status_code=status.HTTP_400_BAD_REQUEST,
        detail=detail)

def not_found_exception(detail: str = "Resource not found"):
    return HTTPException(
        status_code=status.HTTP_404_NOT_FOUND,
        detail=detail
    )
