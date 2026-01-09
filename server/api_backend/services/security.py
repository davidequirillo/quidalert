# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timezone, timedelta
import bcrypt
import secrets
import hashlib
import hashlib
import hmac
from core.commons import AppSettings

def ensure_utc(dt: datetime) -> datetime:
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

def check_password_with_hash(plain_password, hashed_password):
    return bcrypt.checkpw(
        bytes(plain_password, encoding="utf-8"),
        bytes(hashed_password, encoding="utf-8"),
    )

ACTIVATION_TOKEN_BYTES = 32
ACTIVATION_TOKEN_TTL_HOURS = 24
RESET_CODE_TTL_MINUTES = 10
RESET_LOCK_HOURS = 24
COOLDOWN_SECONDS = 60

def generate_activation_token() -> str:
    return secrets.token_urlsafe(ACTIVATION_TOKEN_BYTES)

def activation_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS)

def generate_reset_code() -> str:
    # 8 digits, zero padded
    return str(secrets.randbelow(10**8)).zfill(8)

def reset_code_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(minutes=RESET_CODE_TTL_MINUTES)

def get_email_hash(email: str) -> str:
    normalized = email.strip().lower()
    material = (AppSettings.email_pepper + normalized).encode("utf-8")
    return hashlib.sha256(material).hexdigest()

def check_email_hash(email: str, expected_hash_hex: str) -> bool:
    computed = get_email_hash(email)
    return hmac.compare_digest(computed, expected_hash_hex)

# useful to calculate "reset code hash"
def otp_hmac(code: str) -> str:
    mac = hmac.new(AppSettings.otp_pepper.encode("utf-8"),
        msg=code.encode("utf-8"),
        digestmod=hashlib.sha256,
    )
    return mac.hexdigest()

def otp_verify(code: str, stored_hmac_hex: str) -> bool:
    return hmac.compare_digest(otp_hmac(code), stored_hmac_hex)