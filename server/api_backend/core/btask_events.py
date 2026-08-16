# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_btasks_logger

logger = get_btasks_logger()

## USER E-MAIL MESSAGES

def log_user_activation_code_mail_sent(email: str, request_info: dict, detail: str = ""):
    logger.info(
        f"user_activation_code_mail_sent, email={email}, detail={detail}", 
        extra=request_info
    )

def log_user_activation_code_mail_error(email: str, request_info: dict, detail: str = ""):
    logger.error(
        f"user_activation_code_mail_error, email={email}, detail={detail}",
        extra=request_info
    )

def log_user_reset_code_mail_sent(email: str, request_info: dict, detail: str = ""):
    logger.info(
        f"user_reset_code_mail_sent, email={email}, detail={detail}", 
        extra=request_info
    )

def log_user_reset_code_mail_error(email: str, request_info: dict, detail: str = ""):
    logger.error(
        f"user_reset_code_mail_error, email={email}, detail={detail}",
        extra=request_info
    )

def log_user_reset_successful_mail_sent(email: str, request_info: dict, detail: str = ""):
    logger.info(
        f"user_reset_successful_mail_sent, email={email}, detail={detail}", 
        extra=request_info
    )

def log_user_reset_successful_mail_error(email: str, request_info: dict, detail: str = ""):
    logger.error(
        f"user_reset_successful_mail_error, email={email}, detail={detail}",
        extra=request_info
    )

def log_user_login_code_mail_sent(email: str, request_info: dict, detail: str = ""):
    logger.info(
        f"user_login_code_mail_sent, email={email}, detail={detail}", 
        extra=request_info
    )

def log_user_login_code_mail_error(email: str, request_info: dict, detail: str = ""):
    logger.error(
        f"user_login_code_mail_error, email={email}, detail={detail}",
        extra=request_info
    )

def log_user_login_successful_mail_sent(email: str, request_info: dict, detail: str = ""):
    logger.info(
        f"user_login_successful_mail_sent, email={email}, detail={detail}", 
        extra=request_info
    )

def log_user_login_successful_mail_error(email: str, request_info: dict, detail: str = ""):
    logger.error(
        f"user_login_successful_mail_error, email={email}, detail={detail}",
        extra=request_info
    )

## ALERT CREATE events logging

def log_alert_search_closest_chiefs_done(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_search_closest_chiefs_done, alert_id={alert_id}, detail={detail}",
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

def log_alert_no_chief_manager_to_notify(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_no_chief_manager_to_notify, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_chief_manager(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_chief_manager, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_chief_manager(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_chief_manager, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_search_nearby_users_done(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_search_nearby_users_done, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_searching_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_searching_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_checking_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_checking_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_orphan_ids_found_in_checking_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_orphan_ids_found_in_checking_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_saving_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str):
    logger.error(
        f"alert_error_saving_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_no_nearby_users_to_notify(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str=""):
    logger.warning(
        f"alert_no_nearby_users_to_notify, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_nearby_users(alert_id: str, role: str|None, operation: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_nearby_users, alert_id={alert_id}, role={role}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_no_sender_to_notify(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.warning(
        f"alert_no_sender_to_notify, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_sender(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_sender, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_notify_sender(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_sender, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_success_sending_mail_to_chief_manager(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_success_sending_mail_to_chief_manager, alert_id={alert_id}, operation={operation}, detail={detail}",
        extra=request_info
    )

def log_alert_error_sending_mail_to_chief_manager(alert_id: str, operation: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_sending_mail_to_chief_manager, alert_id={alert_id}, operation={operation}, detail={detail}",
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

### ALERT MESSAGE events logging

def log_alert_notify_on_new_message(alert_id: str, request_info: dict, detail: str = ""):
    logger.info(
        f"alert_notify_on_new_message, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )

def log_alert_error_notifying_on_new_message(alert_id: str, request_info: dict, detail: str = ""):
    logger.error(
        f"alert_error_notifying_on_new_message, alert_id={alert_id}, detail={detail}",
        extra=request_info
    )
