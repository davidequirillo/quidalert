# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_common_logger

logger = get_common_logger()

# Network notification events logging

def log_notify_single_client_unregistered_error(request_info: dict, detail: str = ""):
    logger.error(
        f"notify_single_client_unregistered_error, detail={detail}",
        extra=request_info
    )

def log_notify_single_client_error(request_info: dict, detail: str = ""):
    logger.error(
        f"notify_single_client_error, detail={detail}",
        extra=request_info
    )

def log_notify_single_client_success(request_info: dict, detail: str = ""):
    logger.info(
        f"notify_single_client_success, detail={detail}",
        extra=request_info
    )

def log_notify_many_clients_unregistered_warning(request_info: dict, detail: str = ""):
    logger.warning(
        f"notify_many_clients_unregistered_warning, detail={detail}",
        extra=request_info
    )

def log_notify_many_clients_info(request_info: dict, detail: str = ""):
    logger.info(
        f"notify_many_clients_info, detail={detail}",
        extra=request_info
    )

def log_notify_many_clients_error(request_info: dict, detail: str = ""):
    logger.error(
        f"notify_many_clients_error, detail={detail}",
        extra=request_info
    )
