# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

# The following configurations are only for production

SERVER_NAME = "myservername" # the server name (publicly accessible, for example the reverse proxy)
SERVER_PORT = 8080 # the server port (publicly accessible) 
APP_LOG_LEVEL = 'error' # 'debug', 'error'

# The database connection URL and db engine logging
DB_URL = "postgresql://DB_USER:DB_PASS@DB_HOST:DB_PORT/quidalert_db"
DB_ENGINE_LOG = "no"

# Mail sender configuration
SMTP_HOST = "mailserver" # to send activation mail messages to clients
SMTP_PORT = 465
SMTP_FROM = "no-reply@myservername"

# A note about security configurations:
# variables APP_MODE, ADMIN_PASS, OTP_PEPPER, EMAIL_PEPPER, JWT_SECRET_KEY
# must be set as system environment variables (for production) or in .env file (for development)
