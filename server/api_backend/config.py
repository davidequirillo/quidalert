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

# Pepper string is useful for email hashing (to log email address securely) 
EMAIL_PEPPER = "ZK2s8F7Q9mP1X4vR0Jw3B6YH5kD8nT2A" # change it
# OTP pepper is useful for verification code hashing
OTP_PEPPER ="5y9yN0xv6F9pZk2t7Zl1D6+Kx2z5Hc+6p9LxEw==" # change it
