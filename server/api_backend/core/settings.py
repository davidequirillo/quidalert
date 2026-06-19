# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from pydantic_settings import BaseSettings, SettingsConfigDict
import config 

# Note: Settings priority: docker environment variables > .env file > default values in the code

class Settings(BaseSettings):
    # App conf
    app_mode: str = "production"
    send_emails: bool = True
    host: str = "localhost" # backend host
    port: int = 8080 # backend port
    protocol: str = "https"
    server_name: str = config.SERVER_NAME # the server name is used for CORS and other security policies, it should be the same as the one used in the frontend conf
    server_port: int = config.SERVER_PORT
    app_log_level: str = config.APP_LOG_LEVEL
    # CORS conf
    cors_allow_origins: list = []
    # Security conf
    admin_pass: str = "" # from environment (system, container, or .env)
    email_pepper: str = "" # same as above, from environment 
    otp_pepper: str = "" # same as above, they are critical for security
    global_pepper: str = "" # same...
    jwt_secret_key: str = "" # same...
    # Database conf
    db_user : str = "" # from environment, critical for security
    db_pass : str = "" # same as above
    db_host : str = config.DB_HOST
    db_port : int = config.DB_PORT
    db_name : str = config.DB_NAME
    db_pool_size: int = config.DB_POOL_SIZE
    db_max_overflow: int = config.DB_MAX_OVERFLOW
    db_pool_recycle: int = config.DB_POOL_RECYCLE
    db_engine_log_enabled: str = config.DB_ENGINE_LOG_ENABLED
    # Redis conf
    redis_mode: str = config.REDIS_MODE
    redis_url: str = config.REDIS_URL
    redis_user: str = "" # from environment, critical for security
    redis_pass: str = "" # same as above
    redis_max_connections: int = config.REDIS_MAX_CONNECTIONS
    redis_cluster_nodes: str = config.REDIS_CLUSTER_NODES
    redis_max_connections_per_node: int = config.REDIS_MAX_CONNECTIONS_PER_NODE
    # Mail sender conf
    smtp_user: str = "" # from environment, critical for security
    smtp_pass: str = "" # same as above
    smtp_host: str = config.SMTP_HOST
    smtp_port: int = config.SMTP_PORT
    smtp_from: str = config.SMTP_FROM
    # MinIO conf
    s3_user: str = "" # from environment, critical for security
    s3_pass: str = "" # same as above
    s3_endpoint: str = config.S3_ENDPOINT
    s3_bucket_name: str = config.S3_BUCKET_NAME
    s3_access_key: str = "" # from environment, critical for security
    s3_secret_key: str = "" # same as above
    # Firebase conf
    firebase_keys_path: str = "" # from environment, critical for security
    firebase_pool_size: int = config.FIREBASE_POOL_SIZE
    # Initialized after loading the settings, not from environment 
    db_engine_echo: bool = False
    db_url: str = ""
    # 
    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

try:
    settings = Settings()
    settings.db_url = f"postgresql://{settings.db_user}:{settings.db_pass}@{settings.db_host}:{settings.db_port}/{settings.db_name}"
    settings.db_engine_echo = settings.db_engine_log_enabled.lower() in ("true", "1", "yes")
    if (settings.app_mode != "production"):
        settings.cors_allow_origins = ["*"]
    else:
        settings.cors_allow_origins = [
            f'https://{settings.server_name}:{settings.server_port}'
        ]
except Exception as e:
    print(f"Configuration error: {e}")
    raise SystemExit(1)

if (not settings.admin_pass) or (settings.admin_pass==""):
    print(f"Configuration error: environment var ADMIN_PASS not found")
    raise SystemExit(1)

if (not settings.otp_pepper) or (settings.otp_pepper==""):
    print(f"Configuration error: environment var OTP_PEPPER not found")
    raise SystemExit(1)

if (not settings.email_pepper) or (settings.email_pepper==""):
    print(f"Configuration error: environment var EMAIL_PEPPER not found")
    raise SystemExit(1)

if (not settings.global_pepper) or (settings.global_pepper==""):
    print(f"Configuration error: environment var GLOBAL_PEPPER not found")
    raise SystemExit(1)

if (not settings.jwt_secret_key) or (settings.jwt_secret_key==""):
    print(f"Configuration error: environment var JWT_SECRET_KEY not found")
    raise SystemExit(1)

if (not settings.s3_user) or (settings.s3_user==""):
    print(f"Configuration error: environment var S3_USER not found")
    raise SystemExit(1)

if (not settings.s3_pass) or (settings.s3_pass==""):
    print(f"Configuration error: environment var S3_PASS not found")
    raise SystemExit(1)

if (not settings.smtp_user) or (settings.smtp_user==""):
    print(f"Configuration error: environment var SMTP_USER not found")
    raise SystemExit(1)

if (not settings.smtp_pass) or (settings.smtp_pass==""):
    print(f"Configuration error: environment var SMTP_PASS not found")
    raise SystemExit(1)

if (not settings.db_user) or (settings.db_user==""):
    print(f"Configuration error: environment var DB_USER not found")
    raise SystemExit(1)

if (not settings.db_pass) or (settings.db_pass==""):
    print(f"Configuration error: environment var DB_PASS not found")
    raise SystemExit(1)

if (not settings.redis_user) or (settings.redis_user==""):
    print(f"Configuration error: environment var REDIS_USER not found")
    raise SystemExit(1)

if (not settings.redis_pass) or (settings.redis_pass==""):
    print(f"Configuration error: environment var REDIS_PASS not found")
    raise SystemExit(1)
