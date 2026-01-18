# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from middleware.request_ctx import request_id_ctx, client_ip_ctx, client_ua_ctx
from core.logging import get_security_logger
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

def log_deleted_user_to_renew_registration(email: str):
    logger.info(
        "deleted_user_to_renew_registration",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua(),
            "email_hash": get_email_hash(email)
        }
    )

def log_password_reset_code_generation(user_id: str):
    logger.warning(
        "password_reset_code_generation",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua,
            "user_id": user_id
        }
    )

def log_password_reset_successful(user_id: str):
    logger.info(
        "password_reset_confirm_successful",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua(),
            "user_id": user_id
        }
    )

def log_password_reset_failed(user_id: str, reason: str, attempts: int | None = None):
    logger.warning(
        "password_reset_confirm_failed",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua,
            "user_id": user_id,
            "reason": reason,
            "attempts": attempts
        }
    )

def log_password_reset_locked(user_id: str):
    logger.warning(
        "password_reset_locked",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua,
            "user_id": user_id
        }
    )

def log_login_successful(user_id: str):
    logger.info(
        "login_successful",
        extra={
            "client_ip": get_client_ip(),
            "request_id": get_request_id(),
            "user_agent": get_client_ua(),
            "user_id": user_id
        }
    )
