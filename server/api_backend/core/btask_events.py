# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_tasks_logger

logger = get_tasks_logger()

## ALERT CREATE events logging

def log_alert_search_closest_chiefs_done(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_search_closest_chiefs_done, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )
    
def log_alert_search_nearby_users_done(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_search_nearby_users_done, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_searching_closest_chiefs(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_searching_closest_chiefs, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_checking_closest_chiefs(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_checking_closest_chiefs, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_orphan_ids_found_in_checking_closest_chiefs(alert_id: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_orphan_ids_found_in_checking_closest_chiefs, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_saving_closest_chief(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_saving_closest_chief, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_no_closest_chief_to_notify(alert_id: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_no_closest_chief_to_notify, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_closest_chief(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_closest_chief, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_closest_chief(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_closest_chief, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_searching_nearby_users(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_searching_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_checking_nearby_users(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_checking_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_orphan_ids_found_in_checking_nearby_users(alert_id: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_orphan_ids_found_in_checking_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_saving_nearby_users(alert_id: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_saving_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_no_nearby_users_to_notify(alert_id: str, request_info: dict, detail: str=""):
    logger.warning(
        f"alert_no_nearby_users_to_notify, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_nearby_users(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_nearby_users(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_nearby_users, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_no_sender_to_notify(alert_id: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_no_sender_to_notify, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_sender(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_sender, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_sender(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_sender, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

## ALERT CLOSE events logging

def log_alert_notify_about_closure(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_about_closure, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_about_closure(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_about_closure, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

## ALERT EXPAND events logging

def log_alert_error_finalizing_expansion(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_finalizing_expansion, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )
