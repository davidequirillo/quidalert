# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_api_logger
from core.logging import (
    get_request_info
)

logger = get_api_logger()

def log_deleted_user_to_renew_registration(user_id: str):
    logger.info(
        "deleted_user_to_renew_registration",
        extra=get_request_info(user_id)
    )

def log_promote_users_by_emails_error(user_id: str, detail: str):
    logger.warning(
        f"promote_users_by_emails_error, detail={detail}",
        extra=get_request_info(user_id)
    )

def log_promote_users_error(user_id: str, detail: str):
    logger.warning(
        f"promote_users_error, detail={detail}",
        extra=get_request_info(user_id)
    )

def log_fcm_token_registration_error(user_id: str, detail: str):
    logger.warning(
        f"fcm_token_registration_error, detail={detail}",
        extra=get_request_info(user_id)
    )

def log_fcm_token_registration_success(user_id: str):
    logger.info(
        "fcm_token_registration_success",
        extra=get_request_info(user_id)
    )
