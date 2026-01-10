# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import re
from datetime import datetime, timezone
from typing import Optional
from enum import Enum
from pydantic import EmailStr, field_validator, model_validator
from sqlmodel import SQLModel, Field, Column, DateTime

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
    activation_expires_at: Optional[datetime] = Field(default=None)
    reset_expires_at: Optional[datetime] = Field(default=None)
    reset_attempts: int = Field(default=0, nullable=False)
    reset_locked_until: Optional[datetime] = Field(default=None)
    last_reset_done_at: Optional[datetime] = Field(default=None)
    last_reset_asked_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: datetime.now(timezone.utc).replace(tzinfo=None), nullable=False
    )

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
    reset_code_hash: Optional[str] = Field(default=None)
    
    @field_validator("gps_lat")
    @classmethod
    def validate_gps_lat(cls, v):
        if v is None:
            return v
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("gps_lon")
    @classmethod
    def validate_gps_lon(cls, v):
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

class PasswordResetRequest(SQLModel):
    email: EmailStr

class PasswordResetConfirm(SQLModel):
    email: EmailStr
    code: str
    new_password: str
    
class Alert(SQLModel, table=True):
    __tablename__: str = "alerts"
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    description: str = Field(default="", nullable=False, min_length=0, max_length=256)
    severity: Optional[int] = Field(default=0, nullable=False)
    created_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)
    is_closed: bool = Field(default=False, nullable=False)

    @field_validator("severity")
    @classmethod
    def validate_severity(cls, v):
        if v is None:
            return v
        if not (0 <= v <= 5):
            raise ValueError("Severity must be between 0 and 5")
        return v
    
class WhiteRecordIn(SQLModel, table=False):
    firstname: Optional[str] = Field(nullable=True, max_length=64)
    surname: Optional[str] = Field(nullable=True, max_length=64)
    email: EmailStr = Field(index=True, nullable=False, unique=True, min_length=3, max_length=128)
    type: str = Field(default=UserType.citizen, nullable=False) 
    created_at: datetime = Field(default_factory=lambda:datetime.now(timezone.utc).replace(tzinfo=None), nullable=False)

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
