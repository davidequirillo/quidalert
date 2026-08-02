# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025-2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

# IMPORTANT
# The following configurations are the default fallback values for the application. 
# They can be overridden by environment variables (in system, in container, or in a ".env" file) 

SERVER_NAME = "myservername" # the server name (publicly accessible, for example the reverse proxy)
SERVER_PORT = 8080 # the server port (publicly accessible) 
APP_LOG_LEVEL = 'warning' # 'info', 'warning'

## The database connection URL and db engine logging
DB_NAME = "quidalert_db"
DB_PORT = 5432
DB_HOST = "localhost"
DB_ENGINE_LOG_ENABLED = "no"
DB_POOL_SIZE = 20
DB_MAX_OVERFLOW = 20
DB_POOL_TIMEOUT = 30
DB_POOL_RECYCLE = 1800

## Redis DBMS (redis mode can be "single" or "cluster")
# Important note about cluster mode: the number of cluster nodes 
# must be less or equal than the number of logical shards.
# An equal number is recommended (redis nodes number = logical shards number)
REDIS_MODE = "single" # "single" or "cluster"
REDIS_URL="redis://localhost:6379/0"
REDIS_CLUSTER_NODES="redis-node-1:7001,redis-node-2:7002,redis-node-3:7003"
REDIS_MAX_CONNECTIONS = 200
REDIS_MAX_CONNECTIONS_PER_NODE = 32 # in cluster mode
# REDIS_LOGICAL_SHARDS_NUM: don't change this value, 
# because at the moment it's the recommended value.
# But, in theory, values ​​from 16 up to 128 should not represent a problem.
REDIS_LOGICAL_SHARDS_NUM = 16

## Mail sender configuration
SMTP_HOST = "mailserver" # to send activation mail messages to clients
SMTP_PORT = 465
SMTP_FROM = "no-reply@myservername"

## Firebase configuration (not used at the moment)
FIREBASE_POOL_SIZE = 10 # the maximum number of concurrent connections to Firebase, default is 10

## S3 conf (for file uploads storage)
S3_ENDPOINT="http://localhost:9000"
S3_BUCKET_NAME="quidalert-uploads"

## IMPORTANT note about security configurations.
# The following variables are critical for security and should not be hardcoded in the codebase. 
# The application will not start if any of these variables is missing or empty.
# They must be set as environment variables (see .env file), and in production, they should be managed securely 
# (e.g., using Docker secrets, HashiCorp Vault, etc.) to avoid storing them in plaintext in the .env file.
# 
# Copy the ".env.example" file to ".env" and fill the values for those variables.
# 
# Variables:
# APP_MODE, ADMIN_PASS, FAKE_USERS_PASS
# OTP_PEPPER, EMAIL_PEPPER, GLOBAL_PEPPER, JWT_SECRET_KEY
# S3_USER, S3_PASS, S3_ACCESS_KEY, S3_SECRET_KEY
# SMTP_USER, SMTP_PASS  
# DB_USER, DB_PASS
# REDIS_USER, REDIS_PASS
# FIREBASE_KEYS_PATH
# FIREBASE_PROJECT_ID
