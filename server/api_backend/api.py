# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from dotenv import load_dotenv
from fastapi import (FastAPI, Depends, 
    Request, Response, HTTPException, status)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select
import config
from lib.commons import AppSettings
from lib.models import get_password_hash, UserBase, UserIn, User, UserOut
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
async def get_terms(request: Request, response: Response):
    lang = request.headers.get('Accept-Language');
    if not lang in AppSettings.languages:
        lang = "en"
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    files_dir = os.path.join(os.path.dirname(__file__), "..")
    fpath = os.path.join(files_dir, f"files/terms_{lang}.md")
    if not os.path.exists(fpath):
        fpath += ".example"
    return FileResponse(fpath)

@app.get("/api/users")
async def get_users(db_session: Session = Depends(get_db_session)):
    users = db_session.exec(select(User)).all()
    return users

@app.get("/api/user/{user_id}")
async def get_user(user_id: str, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    return user

@app.delete("/api/user/{user_id}")
def delete_user(user_id: str, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return {"message": "User deleted"}
    return {"message": "User not found"}

@app.put("/api/user/{user_id}")
def update_user(user_id: str, user_new: UserBase, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        user.firstname = user_new.firstname
        user.surname = user_new.surname
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)
        return user
    return {"message": "User not found"}

@app.post("/api/register", response_model=UserOut, status_code=status.HTTP_201_CREATED)
def register_user(user_in: UserIn, db_session: Session = Depends(get_db_session)):
    existing_user = db_session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    if existing_user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    password_hashed = get_password_hash(user_in.password)
    user = User(
        firstname=user_in.firstname,
        surname=user_in.surname,
        email=user_in.email,
        password_hash=password_hashed,
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    return user
