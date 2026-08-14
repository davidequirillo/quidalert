# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import HTTPException, status

def token_not_valid_exception(detail: str = "Token not valid"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
        headers={"WWW-Authenticate": "Bearer"})

def token_expired_exception(detail: str = "Token expired"):
    return HTTPException(
        status_code=status.HTTP_401_UNAUTHORIZED,
        detail=detail,
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

def server_error_exception(detail: str = "Internal server error"):
    return HTTPException(
        status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
        detail=detail
    )
