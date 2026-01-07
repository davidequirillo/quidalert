# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

APP_MODE = "development" # "development" or "production"

# The following configurations are only for production

SERVER_NAME = "myservername" # the server name (publicly accessible, for example the reverse proxy)
SERVER_PORT = 8080 # the server port (publicly accessible) 
APP_LOG_LEVEL = 'error' # 'debug', 'error'
# The database connection URL
DB_URL = "postgresql://DB_USER:DB_PASS@DB_HOST:DB_PORT/quidalert_db"
ADMINPASS = "Password!123"
SMTP_HOST = "mailserver" # to send activation mail messages to clients
SMTP_PORT = 465
SMTP_FROM = "no-reply@myservername"