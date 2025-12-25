# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from dotenv import load_dotenv
from fastapi import FastAPI, Depends
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select
import config
from lib.commons import AppSettings
from lib.models import User, UserBase
from lib.dbmgr import get_session, get_engine

def init_settings():
    if config.APP_MODE != "production":
        load_dotenv()
        AppSettings.is_development = True
        AppSettings.server_name = os.environ.get("HOST", AppSettings.server_name)
        AppSettings.server_port = int(os.environ.get("PORT", AppSettings.server_port))
        AppSettings.app_log_level = os.environ.get("APP_LOG_LEVEL", AppSettings.app_log_level)
        AppSettings.db_url = os.environ.get("DB_URL", AppSettings.db_url)
    else:
        pass # production settings are already in AppSettings from config.py

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up api framework...")
    init_settings()
    app.state.db_engine = get_engine(AppSettings.db_url)
    yield
    print("Shutting down api framework...")
    app.state.db_engine.dispose()
    app.state.db_engine = None

app = FastAPI(lifespan=lifespan)

if (config.APP_MODE != "production"):
    AppSettings.cors_allow_origins = ["*"]

app.add_middleware(CORSMiddleware,
    allow_origins=AppSettings.cors_allow_origins, 
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"])

def get_db_session():
    engine = app.state.db_engine
    yield from get_session(engine)

@app.get("/api/terms")
async def get_terms():
    return {"message": "Terms and conditions content"}

@app.get("/api/users")
async def get_users(db_session: Session = Depends(get_session)):
    users = db_session.exec(select(User)).all()
    return users

@app.get("/api/user/{user_id}")
async def get_user(user_id: str, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    return user

@app.post("/api/user")
def create_user(user: User, db_session: Session = Depends(get_session)):
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user

@app.delete("/api/user/{user_id}")
def delete_user(user_id: str, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return {"message": "User deleted"}
    return {"message": "User not found"}

@app.put("/api/user/{user_id}")
def update_user(user_id: str, user_new: UserBase, db_session: Session = Depends(get_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        user.firstname = user_new.firstname
        user.surname = user_new.surname
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return {"message": "User not found"}
