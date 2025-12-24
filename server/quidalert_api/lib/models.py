# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from typing import Optional
from sqlmodel import SQLModel, Field
from datetime import datetime

class UserBase(SQLModel, table=False):
    email: str = Field(index=True, nullable=False, unique=True)
    firstname: str = Field(nullable=False)
    surname: str = Field(nullable=False)

class User(UserBase, table=True):
    __tablename__ = "users"
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    hashed_password: str = Field(nullable=False)
    geolocated_at: Optional[float] = Field(default=None, nullable=True)

class UserOut(UserBase, table=False):
    id: int # ID is required in output model

class Alert(SQLModel, table=True):
    __tablename__ = "alerts"
    id: Optional[int] = Field(default=None, primary_key=True, nullable=False)
    user_id: int = Field(foreign_key="users.id", nullable=False)
    message: str = Field(nullable=False)
    created_at: Optional[datetime] = Field(default_factory=lambda:datetime.now(datetime.timezone.utc), nullable=False)
