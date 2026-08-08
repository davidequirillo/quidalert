# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_security_logger
from core.logging import (
    get_request_info
)

logger = get_security_logger()

def log_password_reset_code_generation(user_id: str):
    logger.warning(
        "password_reset_code_generation",
        extra=get_request_info(user_id)
    )

def log_password_reset_successful(user_id: str):
    logger.info(
        "password_reset_confirm_successful",
        extra=get_request_info(user_id)
    )

def log_password_reset_failed(user_id: str, reason: str, attempts: int | None = None):
    logger.warning(
        f"password_reset_confirm_failed, attemps={attempts}, detail={reason}",
        extra=get_request_info(user_id)
    )

def log_password_reset_locked(user_id: str):
    logger.warning(
        "password_reset_locked",
        extra=get_request_info(user_id)
    )

def log_login_successful(user_id: str):
    logger.info(
        "login_successful",
        extra=get_request_info(user_id)
    )

def log_login_failed(user_id: str, reason: str | None = None):
    logger.warning(
        f"login_failed, detail={reason}",
        extra=get_request_info(user_id)
    )

def log_login_2fa_failed(user_id: str, reason: str | None = None, attempts: int | None = None):
    logger.warning(
        f"login_2fa_failed, detail={reason}, attempts={attempts}",
        extra=get_request_info(user_id)
    )

def log_login_code_generation(user_id: str):
    logger.info(
        "login_code_generation",
        extra=get_request_info(user_id)
    )

def log_login_locked(user_id: str):
    logger.warning(
        "login_locked",
        extra=get_request_info(user_id)
    )

def log_login_token_generation(user_id: str):
    logger.info(
        "login_token_generation",
        extra=get_request_info(user_id)
    )

def log_login_token_used(user_id: str):
    logger.info(
        "login_token_used",
        extra=get_request_info(user_id)
    )
