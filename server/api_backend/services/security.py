# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
import bcrypt
import secrets
import hashlib
import hmac
from core.settings import settings

def now_tz_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None, microsecond=0)

def from_timestamp_to_datetime_tz_naive(timestamp: int) -> datetime:
    dt = datetime.fromtimestamp(timestamp, tz=timezone.utc)
    return dt.replace(tzinfo=None, microsecond=0)

def ensure_tz_aware(dt: datetime) -> datetime:
    if dt is None:
        raise Exception("datetime is None")
    if dt.tzinfo is None:
        return dt.replace(tzinfo=timezone.utc)
    return dt.astimezone(timezone.utc)

def get_password_hash(password):
    return bcrypt.hashpw(
        bytes(password, encoding="utf-8"),
        bcrypt.gensalt(),
    ).decode(encoding="utf-8")

def check_password_against_hash(plain_password, hashed_password):
    return bcrypt.checkpw(
        bytes(plain_password, encoding="utf-8"),
        bytes(hashed_password, encoding="utf-8"),
    )

RANDOM_TOKEN_BYTES = 32
ACTIVATION_TOKEN_BYTES = 32
ACTIVATION_TOKEN_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 10
RESET_LOCK_HOURS = 24
MAIL_COOLDOWN_SECONDS = 180

def generate_random_token() -> str:
    return secrets.token_urlsafe(RANDOM_TOKEN_BYTES)

def get_token_hash(token): 
    bytes_str = (settings.global_pepper + token).encode("utf-8")
    return hashlib.sha256(bytes_str).hexdigest()

def check_token_against_hash(token: str, expected_hash_hex: str) -> bool:
    computed = get_token_hash(token)
    return hmac.compare_digest(computed, expected_hash_hex)

def generate_activation_token() -> str:
    return secrets.token_urlsafe(ACTIVATION_TOKEN_BYTES)

def activation_expiry() -> datetime:
    now = now_tz_naive()
    return now + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS)

def generate_reset_code() -> str:
    # 10 digits, zero padded
    return str(secrets.randbelow(10**10)).zfill(10)

def reset_code_expiry() -> datetime:
    now = now_tz_naive()
    return now + timedelta(minutes=RESET_CODE_TTL_MINUTES)

def get_email_hash(email: str) -> str:
    normalized = email.strip().lower()
    bytes_str = (settings.email_pepper + normalized).encode("utf-8")
    return hashlib.sha256(bytes_str).hexdigest()

def check_email_against_hash(email: str, expected_hash_hex: str) -> bool:
    computed = get_email_hash(email)
    return hmac.compare_digest(computed, expected_hash_hex)

# useful to calculate "reset code hash"
def otp_hmac(code: str) -> str:
    mac = hmac.new(key=settings.otp_pepper.encode("utf-8"),
        msg=code.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()

def otp_verify(code: str, stored_hmac_hex: str) -> bool:
    return hmac.compare_digest(otp_hmac(code), stored_hmac_hex)

ACCESS_TOKEN_TTL_MINUTES = 2
REFRESH_TOKEN_TTL_MINUTES = 5 # 180 days
MAX_ACTIVE_REFRESH_TOKENS = 6
JWT_ALGORITHM = "HS256"

def create_access_token(subject: str, expires_delta: Optional[timedelta] = None):
    now = now_tz_naive()
    expire = now + (expires_delta or timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    data = {
        "sub": subject,
        "type": "access",
        "iat": now,
        "exp": expire
    }
    token = jwt.encode(data, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token

def create_refresh_token(subject: str, token_id: str, raw_code: str, created_at: Optional[datetime], expires_delta: Optional[timedelta] = None):
    if created_at is None:
        created_at = now_tz_naive()
    expire = created_at + (expires_delta or timedelta(minutes=REFRESH_TOKEN_TTL_MINUTES))
    data = {
        "sub": subject,
        "type": "refresh",
        "jti": token_id,
        "raw": raw_code,
        "iat": created_at,
        "exp": expire
    }
    token = jwt.encode(data, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token

def decode_token(token):
    data = jwt.decode(token, settings.jwt_secret_key, 
        algorithms=[JWT_ALGORITHM])
    return data
