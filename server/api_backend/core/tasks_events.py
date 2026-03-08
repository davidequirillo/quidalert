# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_tasks_logger

logger = get_tasks_logger()

def log_alert_error_searching_nearby_users(alert_id: str, request_info: dict):
    logger.error(
        f"alert_error_searching_nearby_users, alert_id={alert_id}",
        extra=request_info
    )

def log_alert_error_searching_nearest_chief(alert_id: str, request_info: dict):
    logger.error(
        f"alert_error_searching_nearest_chief, alert_id={alert_id}",
        extra=request_info
    )

def log_alert_error_saving_nearby_chief_and_users(alert_id: str, request_info: dict):
    logger.error(
        f"alert_error_saving_nearby_chief_and_users, alert_id={alert_id}",
        extra=request_info
    )

def log_alert_notify_nearby_users(alert_id: str, request_info: dict):
    logger.info(
        f"alert_notify_nearby_users, alert_id={alert_id}",
        extra=request_info
    )
