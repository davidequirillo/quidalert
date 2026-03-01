# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from models.general import Alert, User
from core.tasks_events import log_alert_notify_nearby_users

def notify_nearby_users(alert: Alert, user: User, request_info: dict):
    if alert.is_closed:
        return
    log_alert_notify_nearby_users(str(alert.id), request_info)
