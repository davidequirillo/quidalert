# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import Request
from core.logging import get_security_logger
from middleware.request_ctx import request_id_ctx, client_ip_ctx, client_ua_ctx
from services.security import get_email_hash
logger = get_security_logger()

def get_client_ip() -> str | None:
    try:
        return client_ip_ctx.get()
    except LookupError:
        return None

def get_request_id() -> str | None:
    try:
        return request_id_ctx.get()
    except LookupError:
        return None

def get_client_ua() -> str | None:
    try:
        return client_ua_ctx.get()
    except LookupError:
        return None

def log_delete_user_to_refresh_registration(email: str):
    logger.info(
        "delete_user_to_refresh_registration",
        extra={
            "ip": get_client_ip(),
            "request_id": get_request_id(),
            "email_hash": get_email_hash(email),
            "ua": get_client_ua()
        }
    )

def log_password_reset_success(email: str):
    logger.info(
        "password_reset_confirm_success",
        extra={
            "ip": get_client_ip(),
            "request_id": get_request_id(),
            "email_hash": get_email_hash(email),
            "ua": get_client_ua()
        }
    )

def log_password_reset_fail(email: str, reason: str, attempts: int | None = None):
    logger.warning(
        "password_reset_confirm_fail",
        extra={
            "ip": get_client_ip(),
            "request_id": get_request_id(),
            "email_hash": get_email_hash(email),
            "ua": get_client_ua,
            "reason": reason,
            "attempts": attempts
        }
    )

def log_password_reset_locked(email: str):
    logger.warning(
        "password_reset_locked",
        extra={
            "ip": get_client_ip(),
            "request_id": get_request_id(),
            "email_hash": get_email_hash(email),
            "ua": get_client_ua,
        }
    )
