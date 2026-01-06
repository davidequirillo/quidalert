# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from typing import Optional
from enum import Enum
from sqlmodel import SQLModel, Field
from datetime import datetime, timezone
from pydantic import EmailStr, field_validator, model_validator
from passlib.context import CryptContext
import bcrypt

def get_password_hash(password):
    return bcrypt.hashpw(
        bytes(password, encoding="utf-8"),
        bcrypt.gensalt(),
    ).decode(encoding="utf-8")

def verify_password(plain_password, hashed_password):
    return bcrypt.checkpw(
        bytes(plain_password, encoding="utf-8"),
        bytes(hashed_password, encoding="utf-8"),
    )

class UserType(str, Enum):
    fireman = "fireman"
    wateroperator = "wateroperator"
    usar = "usar"
    alpinrescuer = "alpinerescuer"
    medic = "medic"
    military = "military"
    policeman = "policeman"
    volunteer = "volunteer"
    official = "official"
    citizen = "citizen"

class UserStatus(str, Enum):
    ok = "ok"
    unreliable = "unreliable"
    blocked = "blocked"

class UserBase(SQLModel, table=False):
    firstname: str = Field(nullable=False, min_length=2, max_length=64)
    surname: str = Field(nullable=False, min_length=2, max_length=64)
    email: EmailStr = Field(index=True, nullable=False, unique=True, min_length=3, max_length=128)

class UserIn(UserBase, table=False):
    password: str = Field(min_length=10, max_length=256)

class UserOut(UserBase, table=False):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    is_admin: bool = Field(default=False, nullable=False)
    type: str = Field(default=UserType.citizen, nullable=False)
    status: str = Field(default=UserStatus.ok, nullable=False)

class User(UserOut, table=True):
    __tablename__: str = 'users'
    password_hash: str = Field(nullable=False)
    gps_lat: float | None = Field(default=None, nullable=True)
    gps_lon: float | None = Field(default=None, nullable=True)    
    
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
