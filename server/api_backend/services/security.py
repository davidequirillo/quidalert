# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timezone, timedelta
from typing import Optional
import jwt
from jwt.exceptions import InvalidTokenError
import bcrypt
import secrets
import hashlib
import hashlib
import hmac
from core.settings import settings

def now_tz_naive():
    return datetime.now(timezone.utc).replace(tzinfo=None)
    
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

ACTIVATION_TOKEN_BYTES = 32
ACTIVATION_TOKEN_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 10
RESET_LOCK_HOURS = 24
MAIL_COOLDOWN_SECONDS = 180

def generate_activation_token() -> str:
    return secrets.token_urlsafe(ACTIVATION_TOKEN_BYTES)

def activation_expiry() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
    return now + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS)

def generate_reset_code() -> str:
    # 10 digits, zero padded
    return str(secrets.randbelow(10**10)).zfill(10)

def reset_code_expiry() -> datetime:
    now = datetime.now(timezone.utc).replace(tzinfo=None)
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

ACCESS_TOKEN_TTL_MINUTES = 60
REFRESH_TOKEN_TTL_DAYS = 180
JWT_ALGORITHM = "HS256"

def create_access_token(subject, expires_delta: Optional[timedelta] = None):
    expire = now_tz_naive() + (expires_delta or timedelta(minutes=ACCESS_TOKEN_TTL_MINUTES))
    data = {
        "sub": subject,
        "exp": expire
    }
    token = jwt.encode(data, settings.jwt_secret_key, algorithm=JWT_ALGORITHM)
    return token

def create_refresh_token(sub):
    rtoken = create_access_token(sub, expires_delta=timedelta(days=REFRESH_TOKEN_TTL_DAYS))
    return rtoken

def decode_token(token):
    try:
        data = jwt.decode(token, settings.jwt_secret_key, 
                algorithms=[JWT_ALGORITHM])
        return data
    except InvalidTokenError:
        return None
