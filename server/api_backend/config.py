# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

# IMPORTANT
# The following configurations are the default fallback values for the application. 
# They can be overridden by environment variables (in system, in container, or in a ".env" file) 

SERVER_NAME = "myservername" # the server name (publicly accessible, for example the reverse proxy)
SERVER_PORT = 8080 # the server port (publicly accessible) 
APP_LOG_LEVEL = 'warning' # 'info', 'warning'

# The database connection URL and db engine logging
DB_NAME = "quidalert_db"
DB_PORT = 5432
DB_HOST = "localhost"
DB_ENGINE_LOG_ENABLED = "no"
DB_POOL_SIZE = 10
DB_MAX_OVERFLOW = 20
DB_POOL_RECYCLE = 1800

# Redis DBMS
REDIS_MODE = "single" # "single" or "cluster"
REDIS_URL="redis://localhost:6379/0"
REDIS_CLUSTER_NODES="redis-node-1:7001,redis-node-2:7002,redis-node-3:7003"
REDIS_MAX_CONNECTIONS = 200
REDIS_MAX_CONNECTIONS_PER_NODE = 32 # in cluster mode

# Mail sender configuration
SMTP_HOST = "mailserver" # to send activation mail messages to clients
SMTP_PORT = 465
SMTP_FROM = "no-reply@myservername"

# Firebase configuration
FIREBASE_POOL_SIZE = 10 # the maximum number of concurrent connections to Firebase, default is 10

# S3 conf (for file uploads storage)
S3_ENDPOINT="http://localhost:9000"
S3_BUCKET_NAME="quidalert-uploads"

# IMPORTANT note about security configurations.
# The following variables are critical for security and should not be hardcoded in the codebase. The application will not start if any of these variables is missing or empty.
# They must be set as environment variables in the system, container (for production), or in a ".env" file (for development).
# 
# Copy the ".env.example" file to ".env" and fill the values for those variables.
# 
# Variables:
# APP_MODE, ADMIN_PASS, 
# OTP_PEPPER, EMAIL_PEPPER, GLOBAL_PEPPER, JWT_SECRET_KEY
# S3_USER, S3_PASSWORD, S3_ACCESS_KEY, S3_SECRET_KEY
# SMTP_USER, SMTP_PASSWORD  
# DB_USER, DB_PASSWORD
# REDIS_USER, REDIS_PASSWORD
# FIREBASE_KEYS_PATH
# FIREBASE_PROJECT_ID
