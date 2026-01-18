# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from pydantic_settings import BaseSettings, SettingsConfigDict
import config 

class Settings(BaseSettings):
    admin_pass: str = "" # from environment (system or .env)
    email_pepper: str = "" # from environment (system or .env)
    otp_pepper: str = "" # from environment (system or .env)
    global_pepper: str = "" # from environment (system or .env)
    jwt_secret_key: str = "" # from environment (system or .env)
    app_mode: str = "production"
    protocol: str = "https"
    server_name: str = config.SERVER_NAME
    server_port: int = config.SERVER_PORT
    app_log_level: str = config.APP_LOG_LEVEL
    db_url: str = config.DB_URL
    db_engine_log_enabled: str = config.DB_ENGINE_LOG_ENABLED
    db_engine_echo: bool = False
    cors_allow_origins: list = []
    smtp_host: str = config.SMTP_HOST
    smtp_port: int = config.SMTP_PORT
    smtp_from: str = config.SMTP_FROM

    model_config = SettingsConfigDict(
        env_file=".env",
        env_file_encoding='utf-8',
        extra='ignore'
    )

try:
    settings = Settings()
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
