# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import logging

class DefaultExtrasFilter(logging.Filter):
    def filter(self, record: logging.LogRecord) -> bool:
        for k in ("client_ip", "request_id", "ua", "email_hash"):
            if not hasattr(record, k):
                setattr(record, k, "-")
        return True

def setup_logging():
    handler = logging.StreamHandler()
    handler.addFilter(DefaultExtrasFilter())

    formatter = logging.Formatter(
        fmt="%(asctime)s %(levelname)s %(name)s "
            "ip=%(client_ip)s req_id=%(request_id)s ua=%(ua)s email_hash=%(email_hash)s "
            "%(message)s"
    )
    handler.setFormatter(formatter)

    root = logging.getLogger()
    root.setLevel(logging.INFO)
    root.handlers.clear()
    root.addHandler(handler)

def get_security_logger():
    return logging.getLogger("security")

sql_logger = logging.getLogger('sqlalchemy.engine')
sql_logger.propagate = False # to avoid duplicates log records
sql_logger.setLevel(logging.INFO)