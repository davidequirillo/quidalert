# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from datetime import datetime, timezone, timedelta
from dotenv import load_dotenv
from fastapi import (FastAPI, Depends, 
    Request, Response, HTTPException, status, BackgroundTasks)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.middleware.cors import CORSMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from fastapi.templating import Jinja2Templates
import config
from lib.commons import AppSettings
import lib.localization as i18n
from lib.models import (get_password_hash, check_password_with_hash,  
    generate_activation_token, activation_expiry, ensure_utc,
    UserBase, UserIn, User, UserOut, UserLanguage)
from lib.dbmgr import get_session, get_engine
from lib.network import send_activation_mail

api_dirname = os.path.dirname(__file__)

def init_settings():
    if config.APP_MODE != "production":
        load_dotenv()
        AppSettings.is_development = True
        AppSettings.protocol = "http"
        AppSettings.server_name = os.environ.get("HOST", default=AppSettings.server_name)
        AppSettings.server_port = int(os.environ.get("PORT", default=AppSettings.server_port))
        AppSettings.app_log_level = os.environ.get("APP_LOG_LEVEL", default=AppSettings.app_log_level)
        AppSettings.db_url = os.environ.get("DB_URL", default=AppSettings.db_url)
        AppSettings.smtp_host = os.environ.get("SMTP_HOST", default=AppSettings.smtp_host)
        AppSettings.smtp_port = int(os.environ.get("SMTP_PORT", default=AppSettings.smtp_port))
        AppSettings.smtp_from = os.environ.get("SMTP_FROM", default=AppSettings.smtp_from)
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

templates = Jinja2Templates(directory=os.path.join(api_dirname, "templates"))

@app.get("/api/terms")
async def get_terms(request: Request, response: Response):
    lang = request.headers.get('Accept-Language');
    if (lang != UserLanguage.en) and (lang != UserLanguage.it):
        lang = UserLanguage.en
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    files_dir = os.path.join(os.path.dirname(__file__), "..")
    fpath = os.path.join(files_dir, f"files/terms_{lang}.md")
    if not os.path.exists(fpath):
        fpath += ".example"
    return FileResponse(fpath)

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
def register_user(user_in: UserIn, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    is_an_admin = False
    # if database is empty and password is correct we insert the admin
    if db_session.exec(select(User).limit(1)).first() is None:
        if (user_in.password == AppSettings.adminpass):
            is_an_admin = True
    else: # else we check the email address existence in a whitelist
        pass
        # todo: if user_in.email not in whitelist: 
        #   we raise a http exception (401 - not authorized)      
    existing_user = db_session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    if (existing_user) and (existing_user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Email already registered",
        )
    password_hashed = get_password_hash(user_in.password)
    act_token = generate_activation_token()
    act_expires_at = activation_expiry()
    if (existing_user): # existing user not active, due to expired activation code
        user = existing_user
        user.firstname=user_in.firstname
        user.surname=user_in.surname
        user.email=user_in.email
        user.language=user_in.language
        user.password_hash=password_hashed
        user.is_admin = is_an_admin
        user.is_active=False
        user.activation_code=act_token
        user.activation_expires_at=act_expires_at
    else:    
        user = User(
            firstname=user_in.firstname,
            surname=user_in.surname,
            email=user_in.email,
            language=user_in.language,
            password_hash=password_hashed,
            is_admin = is_an_admin,
            is_active=False,
            activation_code=act_token,
            activation_expires_at=act_expires_at
        )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    
    background_tasks.add_task(send_activation_mail, user.email, act_token, user.language)
    
    return user

@app.get("/activate", response_class=HTMLResponse)
def activate_user(request: Request, email: str, token: str, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(
        select(User).where(User.email == email)).first()
    if not user:
        language = UserLanguage.en
        style_class="error"
        title="Activation code not valid"
        message="Activation code not valid"
    elif (not user.activation_code) or (user.activation_code != token):
        language=UserLanguage.en
        style_class="error"
        title="Activation code not valid"
        message="Activation code not valid"
    elif user.is_active:
        language=user.language
        style_class="warning"
        title=i18n.langmap[user.language]["act_already_title"]
        message=i18n.langmap[user.language]["act_already"]
    elif (not user.activation_expires_at) or (ensure_utc(user.activation_expires_at) < datetime.now(timezone.utc)):
        language=user.language
        style_class="error"
        title=i18n.langmap[user.language]["act_expired_title"]
        message=i18n.langmap[user.language]["act_expired"]
    else:
        language=user.language
        style_class="success"
        title=i18n.langmap[user.language]["act_success_title"]
        message=i18n.langmap[user.language]["act_success"]
        user.is_active = True
        db_session.add(user)
        db_session.commit()
        db_session.refresh(user)

    return templates.TemplateResponse(
        "activation_result.html",
        {
            "request": request,
            "language": language,
            "title": title,
            "message": message,
            "status_class": style_class,
            "footer": i18n.langmap[language]["mail_ignore"],
            "login_url": None
        },
    )
