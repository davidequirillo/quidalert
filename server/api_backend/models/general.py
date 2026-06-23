# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import re
from datetime import datetime, timezone
from typing import List, Optional
from enum import Enum
import uuid_utils as uuid_pkg
import uuid
from pydantic import BaseModel, EmailStr, field_validator, model_validator
from sqlmodel import SQLModel, Field, Index
from services.security import now_tz_naive

class UserRole(str, Enum):
    firefighter = "firefighter"
    wateroperator = "wateroperator"
    usar = "usar"
    alpinrescuer = "alpinerescuer"
    medic = "medic"
    military = "military"
    policeman = "policeman"
    volunteer = "volunteer"
    citizen = "citizen"

class UserLanguage(str, Enum):
    en = "en"
    it = "it"

class UserStatus(str, Enum):
    ok = "ok"
    unreliable = "unreliable"
    blocked = "blocked"

class UserType(str, Enum):
    base = "base"
    admin = "admin"
    officer = "officer"
    chief = "chief"

class AlertType(str, Enum):
    local = "local" # A local alert is a normal alert with coordinates and radius, that can be created by any user, with chief and nearby users alerted
    managed = "managed" # A managed alert is like a local alert, but it's created only by a chief, with custom gps location, and can be managed by him (he becomes the "alert manager")
    general = "general" # A general alert is an alert without coordinates and radius (coordinates and radius not considered), that can only be created by chiefs, and is meant to be used for general information that is not related to a specific location, but it's globally relevant
    empty = "empty" # An empty alert is a special type of alert without radius (radius not considered, but gps location considered), that can be created by chiefs. Alert is created without including or notifying nearby users. It's useful to create empty alerts to be expanded later by the chief

class UserBase(SQLModel, table=False):
    firstname: str = Field(nullable=False, min_length=2, max_length=64)
    surname: str = Field(nullable=False, min_length=2, max_length=64)
    email: EmailStr = Field(index=True, nullable=False, unique=True, min_length=3, max_length=128)
    language: str = Field(default=UserLanguage.en.value, nullable=False)

    @field_validator("language")
    @classmethod
    def validate_language(cls, s):
        if not s in [UserLanguage.en.value, UserLanguage.it.value]:
            raise ValueError("Wrong language")
        return s

def validate_password_strength(s):
    if not re.search(r"[A-Z]", s):
        raise ValueError("Password must contain at least an uppercase character")
    if not re.search(r"[a-z]", s):
        raise ValueError("Password must contain at least a lowercase character")
    if not re.search(r"[0-9]", s):
        raise ValueError("Password must contain at least a digit")
    if not re.search(r"[!@#$%\^&*()\[\],;+=.?\":{}|<>_\-]", s):
        raise ValueError("Password must contain a special character")
    return s

class UserIn(UserBase, table=False):
    password: str = Field(min_length=10, max_length=256)

    @field_validator("password")
    @classmethod
    def validate_password(cls, s):
        return validate_password_strength(s)

class UserInCompleteProfile(BaseModel):
    firstname: str = Field(min_length=2, max_length=64)
    surname: str = Field(min_length=2, max_length=64)
    street: str = Field(min_length=2, max_length=256)
    postal_code: str = Field(min_length=2, max_length=16)
    city: str = Field(min_length=2, max_length=64)
    province: str = Field(min_length=2, max_length=64)
    country: Optional[str] = Field(default=None, min_length=0, max_length=64)
    birthdate: str # YYYY-MM-DD
    phone: str = Field(min_length=6, max_length=32)

    @field_validator("phone")
    @classmethod
    def validate_phone(cls, s):
        if not re.match(r"^\+?[0-9\s\-]+$", s):
            raise ValueError("Invalid phone number format")
        return s
    
    @field_validator("birthdate")
    @classmethod
    def validate_birthdate(cls, s):
        if not re.match(r"^\d{4}-\d{2}-\d{2}$", s):
            raise ValueError("Invalid birthdate format, must be YYYY-MM-DD")
        return s

def string_as_uuid(s):
    try:
        return uuid.UUID(s)
    except:
        raise ValueError("Invalid UUID format")

class UserOut(UserBase, table=False):
    id: uuid.UUID = Field(
        default_factory=lambda: uuid.UUID(bytes=uuid_pkg.uuid7().bytes),
        primary_key=True,
        nullable=False
    )
    is_superuser: bool = Field(default=False, nullable=False)
    is_admin: bool = Field(default=False, nullable=False)
    is_officer: bool = Field(default=False, nullable=False)
    is_chief: bool = Field(default=False, nullable=False)
    role: str = Field(default=UserRole.citizen.value, nullable=False)
    is_reliable: bool = Field(default=True, nullable=False)
    # At the moment, we don't think about overflow issues with the reliability score:
    # it's quite hard to reach very high values or very low values, and in case we can easily change the type to a bigger integer
    reliability_score: int = Field(default=100, nullable=False)
    last_reliability_score_at: Optional[datetime] = Field(default=None)
    is_blocked: bool = Field(default=False, nullable=False)
    is_active: bool = Field(default=False, nullable=False)
    activation_expires_at: Optional[datetime] = Field(default=None)
    reset_expires_at: Optional[datetime] = Field(default=None)
    reset_attempts: int = Field(default=0, nullable=False)
    reset_locked_until: Optional[datetime] = Field(default=None)
    last_reset_mail_code_at: Optional[datetime] = Field(default=None)
    last_reset_done_at: datetime = Field(
        default_factory=lambda: now_tz_naive(), nullable=False   
    )
    last_reset_mail_confirmation_at: Optional[datetime] = Field(default=None)  
    login_expires_at: Optional[datetime] = Field(default=None)
    login_2fa_attempts: int = Field(default=0, nullable=False)
    login_locked_until: Optional[datetime] = Field(default=None)
    last_login_mail_code_at: Optional[datetime] = Field(default=None) 
    last_login_done_at: Optional[datetime] = Field(default=None)   
    last_2fa_success_at: Optional[datetime] = Field(default=None)
    last_login_mail_confirmation_at: Optional[datetime] = Field(default=None)
    last_refresh_at: Optional[datetime] = Field(default=None)
    created_at: datetime = Field(
        default_factory=lambda: now_tz_naive(), nullable=False
    )
    updated_by: Optional[EmailStr] = Field(default=None, nullable=True)
    updated_at: Optional[datetime] = Field(default=None, nullable=True)
    authorized_by: Optional[EmailStr] = Field(default=None, nullable=True)
    authorized_at: Optional[datetime] = Field(default=None, nullable=True)
    street: Optional[str] = Field(default=None, min_length=2, max_length=256)
    postal_code: Optional[str] = Field(default=None, min_length=2, max_length=16)
    city: Optional[str] = Field(default=None, min_length=2, max_length=64)
    province: Optional[str] = Field(default=None, min_length=2, max_length=64)
    country: Optional[str] = Field(default=None, min_length=2, max_length=64)
    birthdate: Optional[str] = Field(default=None, min_length=10, max_length=10) # YYYY-MM-DD
    phone: Optional[str] = Field(default=None, min_length=6, max_length=32)
    notes: Optional[str] = Field(default=None, min_length=0, max_length=256, nullable=True)
    
    __table_args__ = (
        Index("ix_users_authorized_by_id", "authorized_by", "id"),
    )
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, s):
        if not s in [t.value for t in UserRole]:
            raise ValueError("Wrong role")
        return s

class UserOutSmall(BaseModel):
    id: uuid.UUID
    firstname: str
    surname: str
    email: EmailStr
    authorized_by: Optional[EmailStr] = None
    authorized_at: Optional[datetime] = None
    is_admin: bool
    is_officer: bool
    is_chief: bool
    role: str
    is_reliable: bool
    is_blocked: bool
    reliability_score: int
    phone: Optional[str] = None

class UsersOutPaginated(BaseModel):
    users: List[UserOutSmall]
    next_cursor: Optional[uuid.UUID] = None

USER_NEGATIVE_RELIABILITY_SCORE_TTL_DAYS = 180
USER_NEGATIVE_RELIABILITY_SCORE_RESET_VALUE = 15

class User(UserOut, table=True):
    __tablename__: str = 'users'
    password_hash: str = Field(nullable=False)
    activation_code: Optional[str] = Field(default=None)    
    reset_code_hash: Optional[str] = Field(default=None)
    login_code_hash: Optional[str] = Field(default=None)

class PasswordResetRequest(BaseModel):
    email: EmailStr

class PasswordResetConfirm(BaseModel):
    email: EmailStr = Field(min_length=3, max_length=128)
    code: str = Field(min_length=10, max_length=10)
    new_password: str = Field(min_length=10, max_length=256)

    @field_validator("code")
    @classmethod
    def validate_code(cls, value: str) -> str:
        if not re.fullmatch(r"\d{10}", value):
            raise ValueError(f"Code must be a 10-digit number")
        return value

    @field_validator("new_password")
    @classmethod
    def validate_password(cls, s):
        return validate_password_strength(s)

class RefreshToken(SQLModel, table=True):
    __tablename__: str = 'refresh_tokens'
    
    id: uuid.UUID = Field(
        default_factory=lambda: uuid.UUID(bytes=uuid_pkg.uuid7().bytes),
        primary_key=True,
        nullable=False
    )
    user_id: uuid.UUID = Field(foreign_key="users.id", nullable=False, index=True)
    raw_hash: str = Field(nullable=False) # a random token hash    
    ip_address: Optional[str] = Field(default=None)
    device_info: Optional[str] = Field(default=None)
    fcm_token: Optional[str] = Field(default=None)
    fcm_token_updated_at: Optional[datetime] = Field(default=None)
    updated_at: datetime = Field(
        default_factory=lambda: now_tz_naive()
    )
    is_revoked: bool = Field(default=False)

class LoginSchema(BaseModel):
    email: EmailStr
    password: str
    login_code: Optional[str] = Field(default=None, min_length=6, max_length=6) # 2FA code
    login_token: Optional[str] = Field(default=None) # jwt token to skip 2FA
    device_model: Optional[str] = Field(default=None, min_length=0, max_length=256)
    language: Optional[str] = Field(default=None, min_length=2, max_length=8)

    @field_validator("login_code")
    @classmethod
    def validate_login_code(cls, value: str) -> str:
        if (value is None):
            return value
        if not re.fullmatch(r"\d{6}", value):
            raise ValueError(f"Code must be a 6-digit number")
        return value
    
    @field_validator("language")
    @classmethod
    def validate_language(cls, s):
        if (s is None):
            return s
        if not s in [UserLanguage.en.value, UserLanguage.it.value]:
            raise ValueError("Wrong language")
        return s

class RefreshTokenWrapper(BaseModel):
    refresh_token: str

class FcmTokenWrapper(BaseModel):
    fcm_token: str
    
class WhiteListEntry(SQLModel, table=True):
    __tablename__: str = 'whitelist_entries'
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    email: EmailStr = Field(nullable=False, index=True, unique=True, min_length=3, max_length=128)
    created_by: EmailStr = Field(nullable=False, min_length=3, max_length=128)
    created_at: datetime = Field(default_factory=lambda: now_tz_naive(), nullable=False)

    __table_args__ = (
        Index("ix_whitelist_entries_created_by_id", "created_by", "id"),
    )

class EmailListDict(BaseModel):
    emails: List[str]

class PromotionSchema(BaseModel):
    type: Optional[str] = None
    role: Optional[str] = None
    status: Optional[str] = None
    notes: Optional[str] = None
    authorizer: Optional[EmailStr] = None

    @field_validator("type")
    @classmethod
    def validate_type(cls, s):
        if not s in [t.value for t in UserType]:
            raise ValueError("Wrong type")
        return s
    
    @field_validator("role")
    @classmethod
    def validate_role(cls, s):
        if not s in [t.value for t in UserRole]:
            raise ValueError("Wrong role")
        return s
    
    @field_validator("status")
    @classmethod
    def validate_status(cls, s):
        if not s in [t.value for t in UserStatus]:
            raise ValueError("Wrong status")
        return s
    
    @field_validator("notes")
    @classmethod
    def validate_notes(cls, s):
        if (s is not None) and (len(s) > 256):
            raise ValueError("Notes must be at most 256 characters")
        return s
    
    @model_validator(mode="after")
    def check_not_empty(self):
        if ((self.type is None) and (self.role is None) and
            (self.status is None) and (self.notes is None) and
            (self.authorizer is None)):
                raise ValueError("Promotion schema is empty")
        return self

class ChangeStatusSchema(BaseModel):
    status: str

    @field_validator("status")
    @classmethod
    def validate_status(cls, s):
        if not s in [t.value for t in UserStatus]:
            raise ValueError("Wrong status")
        return s

class AlertIn(SQLModel, table=False):
    type: str = Field(default=AlertType.local.value, nullable=False)
    description: str = Field(nullable=False, min_length=1, max_length=512)
    latitude: float = Field(default=0.0, nullable=False)
    longitude: float = Field(default=0.0, nullable=False)
    radius: float = Field(default=1.0, nullable=False, gt=0, lt=50) # in kilometers
    address: Optional[str] = Field(default=None, nullable=True, min_length=0, max_length=256)

    @field_validator("description")
    @classmethod
    def validate_description(cls, s):
        if s.strip() == "":
            raise ValueError("Description cannot be empty")
        return s

    @field_validator("type")
    @classmethod
    def validate_type(cls, s):
        if not s in [t.value for t in AlertType]:
            raise ValueError("Wrong type")
        return s

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v
    
class AlertOut(AlertIn, table=False):
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    severity: int = Field(default=10, ge=0, le=10, nullable=False) # not used at the moment, but we can use it in the future to indicate the severity of the alert (0 = low, 10 = high)
    created_at: datetime = Field(default_factory=lambda: now_tz_naive(), nullable=False)
    is_pending: bool = Field(default=True, nullable=False) # "pending" means that the alert has been created but it's in processing phase (background task is running to spread the alert to nearby users)
    spread_count: int = Field(default=0, ge=0, le=3, nullable=False) # number of times the alert can spread to nearby users (adding new users to the alerted users list), max 3 spreads (initial alert + 3 spreads = max 4 "generations" of alerted users)
    is_closed: bool = Field(default=False, nullable=False)

class Alert(AlertOut, table=True):
    __tablename__: str = "alerts"
    user_id: Optional[uuid.UUID] = Field(
        foreign_key="users.id",
        ondelete="CASCADE", 
        nullable=False,
        index=True)

    __table_args__ = (Index("idx_alerts_created_at_lat_long", "created_at", "latitude", "longitude"),)

class UserOutWithAlerts(BaseModel):
    user: UserOut
    alerts: List[AlertOut]

class AlertedUser(SQLModel, table=True):
    __tablename__: str = "alerted_users"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(
        foreign_key="alerts.id", 
        ondelete="CASCADE",
        nullable=False,
        index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", 
        ondelete="CASCADE",
        nullable=False, 
        index=True
    )
    is_manager: bool = Field(default=False, nullable=False)
    # For all users: -1 = downvote, 0 = no vote, +1 = upvote
    # Chief can do a closing vote: his final vote can be -15, 0, +15;
    # We will think about the algorythm to use, 
    # to modify reliability score of involved users (alert sender and alerted users)
    vote: int = Field(default=0, ge=-1, le=+1, nullable=False)
    closing_vote: int = Field(default=0, ge=-15, le=+15, nullable=False)

class GpsTokenData(BaseModel):
    user_id: str # here we use a string instead of UUID
    user_is_chief: bool
    user_role: str

class GpsCoordinatesSchema(BaseModel):
    latitude: float
    longitude: float

    @field_validator("latitude")
    @classmethod
    def validate_latitude(cls, v):
        if not (-90 <= v <= 90):
            raise ValueError("Latitude must be between -90 and 90")
        return v

    @field_validator("longitude")
    @classmethod
    def validate_longitude(cls, v):
        if not (-180 <= v <= 180):
            raise ValueError("Longitude must be between -180 and 180")
        return v

class Message(SQLModel, table=True):
    __tablename__: str = "messages"
    id: Optional[int] = Field(default=None, primary_key=True)
    alert_id: int = Field(
        foreign_key="alerts.id", 
        ondelete="CASCADE",
        nullable=False,
        index=True
    )
    user_id: uuid.UUID = Field(
        foreign_key="users.id", 
        ondelete="CASCADE",
        nullable=False
    )
    content: str = Field(nullable=False, min_length=1, max_length=512)
    created_at: datetime = Field(default_factory=lambda: now_tz_naive(), nullable=False)

class AlertOutWithInfo(BaseModel):
    alert: AlertOut
    sender_firstname: str
    sender_surname: str
    sender_reliability_score: int
    sender: Optional[UserOutSmall] = None # the chief (alert manager) can view all sender info
    alerted_users: Optional[List[UserOutSmall]] = None # the chief (alert manager) can view all alerted users info
    alerted_users_number: int
