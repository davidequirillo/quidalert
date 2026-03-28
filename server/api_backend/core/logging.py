# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import logging
from middleware.request_ctx import request_id_ctx, client_ip_ctx, client_ua_ctx
from core.settings import settings

class DefaultExtrasFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for k in ("client_ip", "request_id", "user_agent", "user_id"):
            if not hasattr(record, k):
                setattr(record, k, "-")
        return True
    
def setup_logging():
    handler = logging.StreamHandler()
    handler.addFilter(DefaultExtrasFilter())

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s "
            "ip=%(client_ip)s req_id=%(request_id)s ua=%(user_agent)s user_id=%(user_id)s %(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    if settings.app_log_level.lower() == 'debug':
        root.setLevel(logging.DEBUG)
    elif settings.app_log_level.lower() == 'info':
        root.setLevel(logging.INFO)
    elif settings.app_log_level.lower() == 'warning':
        root.setLevel(logging.WARNING)
    elif settings.app_log_level.lower() == 'error':
        root.setLevel(logging.ERROR)
    else:
        root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

def get_security_logger():
    return logging.getLogger("security")

def get_tasks_logger():
    return logging.getLogger("btasks")

def get_periodics_logger():
    return logging.getLogger("periodics")

def get_api_logger():
    return logging.getLogger("api")

sql_logger = logging.getLogger('sqlalchemy.engine')
sql_logger.propagate = False # to avoid duplicates log records
sql_logger.setLevel(logging.INFO)

def get_client_ip() -> str | None:
    try:
        return client_ip_ctx.get()
    except LookupError:
        return None

def get_request_id() -> str | None:
    try:
        return request_id_ctx.get()
    except LookupError:
        return None

def get_client_ua() -> str | None:
    try:
        return client_ua_ctx.get()
    except LookupError:
        return None
    
def get_request_info(user_id: str) -> dict:
    return {
        "client_ip": get_client_ip(),
        "request_id": get_request_id(),
        "user_agent": get_client_ua(),
        "user_id": user_id
    }