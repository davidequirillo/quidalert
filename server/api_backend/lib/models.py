# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from typing import Optional
import re
from enum import Enum
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone, timedelta
from pydantic import EmailStr, field_validator, model_validator
import bcrypt
import secrets

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

def generate_activation_token() -> str:
    return secrets.token_urlsafe(ACTIVATION_TOKEN_BYTES)

def activation_expiry() -> datetime:
    return datetime.now(timezone.utc) + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS)

class UserType(str, Enum):
    fireman = "fireman"
    wateroperator = "wateroperator"
    usar = "usar"
    alpinrescuer = "alpinerescuer"
    medic = "medic"
    military = "military"
    policeman = "policeman"
    volunteer = "volunteer"
    citizen = "citizen"

class UserStatus(str, Enum):
    ok = "ok"
    unreliable = "unreliable"
    blocked = "blocked"

class UserLanguage(str, Enum):
    en = "en"
    it = "it"

class UserBase(SQLModel, table=False):
    firstname: str = Field(nullable=False, min_length=2, max_length=64)
    surname: str = Field(nullable=False, min_length=2, max_length=64)
    email: EmailStr = Field(index=True, nullable=False, unique=True, min_length=3, max_length=128)
    language: str = Field(default=UserLanguage.en, nullable=False)

    @field_validator("language")
    @classmethod
    def validate_language(cls, s):
        if not s in [UserLanguage.en, UserLanguage.it]:
            raise ValueError("Wrong language")
        return s
    
class UserIn(UserBase, table=False):
    password: str = Field(min_length=10, max_length=256)

    @field_validator("password")
    @classmethod
    def validate_password(cls, s):
        if not re.search(r"[A-Z]", s):
            raise ValueError("Password must contain at least an uppercase character")
        if not re.search(r"[a-z]", s):
            raise ValueError("Password must contain at least a lowercase character")
        if not re.search(r"[0-9]", s):
            raise ValueError("Password must contain at least a digit")
        if not re.search(r"[!@#$%\^&*()\[\],;+=.?\":{}|<>_\-]", s):
            raise ValueError("Password must contain a special character")
        return s

class UserOut(UserBase, table=False):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    is_admin: bool = Field(default=False, nullable=False)
    is_official: bool = Field(default=False, nullable=True)
    type: str = Field(default=UserType.citizen, nullable=False)
    status: str = Field(default=UserStatus.ok, nullable=False)
    is_active: bool = Field(default=False, nullable=False)

    @field_validator("type")
    @classmethod
    def validate_type(cls, s):
        if not s in [t.value for t in UserType]:
            raise ValueError("Wrong type")
        return s
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, s):
        if not s in [UserStatus.ok, UserStatus.unreliable, UserStatus.blocked]:
            raise ValueError("Wrong status")
        return s
        
class User(UserOut, table=True):
    __tablename__: str = 'users'
    password_hash: str = Field(nullable=False)
    gps_lat: float | None = Field(default=None, nullable=True)
    gps_lon: float | None = Field(default=None, nullable=True)
    activation_code: Optional[str] = Field(default=None)
    activation_expires_at: Optional[datetime] = Field(default=None)    
    created_at: Optional[datetime] = Field(default_factory=lambda:datetime.now(timezone.utc), nullable=False)
    
    @field_validator("gps_lat")
    @classmethod
    def validate_lat(cls, v):
        if v is None:
            return v
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("gps_lon")
    @classmethod
    def validate_lon(cls, v):
        if v is None:
            return v
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
    @model_validator(mode="after")
    def check_both_or_none(self):
        if (self.gps_lat is None) != (self.gps_lon is None):
            raise ValueError("Latitude and Longitude must have either a value or be None")
        return self
    
class Alert(SQLModel, table=True):
    __tablename__: str = "alerts"
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    description: str = Field(default="", nullable=False, min_length=0, max_length=256)
    created_at: Optional[datetime] = Field(default_factory=lambda:datetime.now(timezone.utc), nullable=False)
    is_closed: bool = Field(default=False, nullable=False)

class WhiteRecordIn(SQLModel, table=False):
    firstname: Optional[str] = Field(nullable=True, max_length=64)
    surname: Optional[str] = Field(nullable=True, max_length=64)
    email: EmailStr = Field(index=True, nullable=False, unique=True, min_length=3, max_length=128)
    type: str = Field(default=UserType.citizen, nullable=False) 

    @field_validator("type")
    @classmethod
    def validate_type(cls, s):
        if not s in [t.value for t in UserType]:
            raise ValueError("Wrong type")
        return s    

class WhiteRecord(WhiteRecordIn, table=True):
    __tablename__: str = 'whitelist'
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    registrant_id: int = Field(foreign_key="users.id", nullable=False)
