# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from core.logging import get_periodics_logger

logger = get_periodics_logger()

def log_cleanup_expired_locations_in_cooldown(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_in_cooldown, detail={detail}"
    )

def log_cleanup_expired_locations_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_error, detail={detail}"
    )

def log_cleanup_expired_locations_started(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_started, detail={detail}"
    )

def log_cleanup_expired_locations_shard(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_shard, detail={detail}"
    )

def log_cleanup_expired_locations_shard_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_shard_error, detail={detail}"
    )

def log_cleanup_expired_locations_completed(detail: str = ""):
    logger.info(
        f"cleanup_expired_locations_completed, detail={detail}"
    )

def log_cleanup_expired_demotions_in_cooldown(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_in_cooldown, detail={detail}"
    )

def log_cleanup_expired_demotions_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_error, detail={detail}"
    )

def log_cleanup_expired_demotions_started(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_started, detail={detail}"
    )

def log_cleanup_expired_demotions_shard(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_shard, detail={detail}"
    )

def log_cleanup_expired_demotions_shard_error(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_shard_error, detail={detail}"
    )

def log_cleanup_expired_demotions_completed(detail: str = ""):
    logger.info(
        f"cleanup_expired_demotions_completed, detail={detail}"
    )

def log_cleanup_dismissed_users_in_cooldown(detail: str = ""):
    logger.info(
        f"cleanup_dismissed_users_in_cooldown, detail={detail}"
    )

def log_cleanup_dismissed_users_error(detail: str = ""):
    logger.info(
        f"cleanup_dismissed_users_error, detail={detail}"
    )

def log_cleanup_dismissed_users_started(detail: str = ""):
    logger.info(
        f"cleanup_dismissed_users_started, detail={detail}"
    )

def log_cleanup_dismissed_users_completed(detail: str = ""):
    logger.info(
        f"cleanup_dismissed_users_completed, detail={detail}"
    )

def log_cleanup_old_alerts_in_cooldown(detail: str = ""):
    logger.info(
        f"cleanup_old_alerts_in_cooldown, detail={detail}"
    )

def log_cleanup_old_alerts_error(detail: str = ""):
    logger.info(
        f"cleanup_old_alerts_error, detail={detail}"
    )

def log_cleanup_old_alerts_started(detail: str = ""):
    logger.info(
        f"cleanup_old_alerts_started, detail={detail}"
    )

def log_cleanup_old_alerts_completed(detail: str = ""):
    logger.info(
        f"cleanup_old_alerts_completed, detail={detail}"
    )
