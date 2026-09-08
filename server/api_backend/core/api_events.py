# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from typing import Optional
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

def log_gps_position_updated(user_id: str, latitude: float, longitude: float, 
        location_id: Optional[str] = None, accuracy: Optional[float] = None, 
        is_moving: Optional[bool] = None, speed: Optional[float] = None):
    if speed is not None:
        speed_ms = f"{speed:.1f}"  # format to 1 decimal places
        speed_kmh = f"{speed * 3.6:.1f}"  # convert to km/h and format to 1 decimal places
    else:
        speed_ms = None
        speed_kmh = None
    logger.info(
        f"gps_position_updated, latitude={latitude}, longitude={longitude}, location_id={location_id}, accuracy={accuracy}, is_moving={is_moving}, speed={speed_ms} m/s -> {speed_kmh} km/h",
        extra=get_request_info(user_id)
    )
