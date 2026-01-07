# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import config 

class AppSettings:
    is_development = False
    protocol = "https"
    server_name = config.SERVER_NAME
    server_port = config.SERVER_PORT
    app_log_level = config.APP_LOG_LEVEL
    db_url = config.DB_URL
    cors_allow_origins = [
        f'https://{server_name}:{server_port}'
    ]
    adminpass = config.ADMINPASS
    smtp_host = config.SMTP_HOST
    smtp_port = config.SMTP_PORT
    smtp_from = config.SMTP_FROM
