# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_periodics_logger

logger = get_periodics_logger()

def log_cleanup_expired_locations_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_error, detail={detail}"
    )

def log_cleanup_expired_locations_started(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_started, detail={detail}"
    )

def log_cleanup_expired_locations_completed(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_completed, detail={detail}"
    )

def log_cleanup_expired_demotions_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_error, detail={detail}"
    )

def log_cleanup_expired_demotions_started(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_started, detail={detail}"
    )

def log_cleaning_demotions_shard(detail: str = ""):
    logger.info(
        f"cleaning_demotions_shard, detail={detail}"
    )

def log_cleanup_expired_demotions_completed(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_completed, detail={detail}"
    )

