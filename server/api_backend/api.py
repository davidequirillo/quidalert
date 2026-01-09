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
from middleware.request_ctx import RequestContextMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from fastapi.templating import Jinja2Templates
import config
from core.logging import setup_logging
from core.commons import AppSettings
from core.security_events import (
    log_password_reset_success,
    log_password_reset_locked,
    log_delete_user_to_refresh_registration
)
import services.localization as i18n
from models.general import (UserBase, UserIn, User, UserOut, UserLanguage,
    PasswordResetRequest, PasswordResetConfirm)
from services.security import (get_password_hash, check_password_with_hash,  
    generate_activation_token, activation_expiry, ensure_utc,
    generate_reset_code, reset_code_expiry, otp_hmac, otp_verify, 
    RESET_LOCK_HOURS, COOLDOWN_SECONDS)
from core.dbmgr import get_session, get_engine
from services.network import send_activation_mail, send_reset_code_mail, send_reset_successful_mail

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
        AppSettings.email_pepper = os.environ.get("EMAIL_PEPPER", default=AppSettings.email_pepper)
        AppSettings.otp_pepper = os.environ.get("OTP_PEPPER", AppSettings.otp_pepper)
    else:
        pass # production settings are already in AppSettings from config.py
    setup_logging()

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

app.add_middleware(RequestContextMiddleware)
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

@app.get("/api/user/{user_id}") # login will be required
async def get_user(user_id: str, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    return user

@app.delete("/api/user/{user_id}") # login will be required
def delete_user(user_id: str, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return {"message": "User deleted"}
    return {"message": "User not found"}

@app.put("/api/user/{user_id}") # login will be required
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

@app.post("/api/register")
def register_user(user_in: UserIn, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    # We will return a unique registration message for almost all cases, for security
    reg_message = "If email address is valid, you will receive an activation mail message"
    is_an_admin = False
    # If database is empty and password is correct we insert the admin
    if db_session.exec(select(User).limit(1)).first() is None:
        if (user_in.password == AppSettings.adminpass):
            is_an_admin = True
    else: # else we check the email address existence in a whitelist
        pass
        # todo: if user_in.email is not in whitelist: 
        # return message
    existing_user = db_session.exec(
        select(User).where(User.email == user_in.email)
    ).first()
    if existing_user and existing_user.is_active:
        return { "message": reg_message }
    password_hashed = get_password_hash(user_in.password)
    act_token = generate_activation_token()
    act_expires_at = activation_expiry()
    now = datetime.now(timezone.utc)
    if (existing_user and (not existing_user.is_active)):
        if ((existing_user.activation_expires_at) and 
            (ensure_utc(existing_user.activation_expires_at) < now)):
                db_session.delete(existing_user)
                log_delete_user_to_refresh_registration(existing_user.email)
        else:
            return { "message": reg_message }
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
    background_tasks.add_task(send_activation_mail, user.email, act_token, user.language)
    return { "message": reg_message }

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
        title=i18n.langmap[user.language]["act_done_title"]
        message=i18n.langmap[user.language]["act_done"]
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

@app.post("/password-reset/request")
def request_password_reset(data: PasswordResetRequest, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    mail_exists_str = "If email exists, you will receive a mail verification code"
    user = db_session.exec(
        select(User).where(User.email == data.email)).first()
    if not user:
        return {"message": mail_exists_str }
    now = datetime.now(timezone.utc)
    if user.reset_locked_until and ensure_utc(user.reset_locked_until) > now:
        return {"message": mail_exists_str }
    
    if ((not user.reset_code_hash) or 
        (not user.reset_expires_at) or 
            (now > ensure_utc(user.reset_expires_at))):
                code = generate_reset_code()
                code_hash = otp_hmac(code) 
                expires_at = reset_code_expiry()
                user.reset_code_hash = code_hash
                user.reset_expires_at = expires_at
    # Cooldown check to avoid potential DoS attacks to the mail service
    can_send = ((not user.last_reset_asked_at) or 
        ((now - user.last_reset_asked_at).total_seconds() > COOLDOWN_SECONDS)) 
    if can_send:
        user.last_reset_asked_at = now
    db_session.add(user)
    db_session.commit()  
    if can_send: 
        background_tasks.add_task(send_reset_code_mail, user.email, code, user.language)
    
    return {"message": mail_exists_str}

@app.post("/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(
        select(User).where(User.email == data.email)).first()
    if not user:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    now = datetime.now(timezone.utc)
    if user.reset_locked_until and ensure_utc(user.reset_locked_until) > now:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    if ((not user.reset_code_hash) or 
            (not user.reset_expires_at) or 
                (ensure_utc(user.reset_expires_at) < now)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid"
        )
    if (otp_verify(data.code, user.reset_code_hash)):
        user.reset_attempts += 1
        if user.reset_attempts > 3:
            user.reset_code = None
            user.reset_expires_at = None
            user.reset_locked_until = now + timedelta(hours=RESET_LOCK_HOURS)
            user.reset_attempts = 0
            log_password_reset_locked(user.email)
        db_session.add(user)
        db_session.commit()
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    
    hashed = get_password_hash(data.new_password)
    user.password_hash = hashed
    user.reset_code = None
    user.reset_expires_at = None
    user.reset_locked_until = None
    user.reset_attempts = 0
    user.last_reset_done_at = now
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    log_password_reset_success(user.email)

    background_tasks.add_task(send_reset_successful_mail, user.email, user.language)

    return {"message": "Password reset successful"}
