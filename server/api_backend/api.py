# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from datetime import timedelta
from fastapi import (FastAPI, Depends, 
    Request, Response, HTTPException, status, BackgroundTasks)
from fastapi.responses import FileResponse, HTMLResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from middleware.request_ctx import RequestContextMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select
from fastapi.templating import Jinja2Templates
from core.settings import settings
from core.logging import setup_logging
from core.security_events import (
    log_password_reset_code_generation,
    log_password_reset_success,
    log_password_reset_locked,
    log_delete_user_to_refresh_registration
)
import services.localization as i18n
from models.general import (UserBase, UserIn, User, UserOut, UserLanguage,
    PasswordResetRequest, PasswordResetConfirm)
from services.security import (get_password_hash, check_password_against_hash,  
    generate_activation_token, activation_expiry, now_tz_naive,
    generate_reset_code, reset_code_expiry, otp_hmac, otp_verify, get_email_hash, check_email_against_hash,
    RESET_LOCK_HOURS, MAIL_COOLDOWN_SECONDS,
    create_access_token, create_refresh_token, decode_token)
from core.dbmgr import get_session, get_engine
from services.network import send_activation_mail, send_reset_code_mail, send_reset_successful_mail

def init_settings():
    setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up api framework...")
    init_settings()
    app.state.db_engine = get_engine(settings.db_url)
    yield
    print("Shutting down api framework...")
    app.state.db_engine.dispose()
    app.state.db_engine = None

app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_allow_origins, 
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"])

def get_db_session():
    engine = app.state.db_engine
    yield from get_session(engine)

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/login")
credentials_exception = HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid credentials",
            headers={"WWW-Authenticate": "Bearer"})

async def get_current_user(token: str = Depends(oauth2_scheme),
                    db_session: Session = Depends(get_session)):
    token_data = decode_token(token)
    if token_data is None:
        raise credentials_exception
    email_hash: str = token_data.get("sub")
    if email_hash is None:
        raise credentials_exception
        
    statement = select(User).where(User.email_hash == email_hash)
    user = db_session.exec(statement).first()
    if user is None:
        raise credentials_exception
    return user

api_dirname = os.path.dirname(__file__)
templates = Jinja2Templates(directory=os.path.join(api_dirname, "templates"))

@app.get("/api/terms")
async def get_terms(request: Request, response: Response):
    lang = request.headers.get('Accept-Language')
    if (lang != UserLanguage.en) and (lang != UserLanguage.it):
        lang = UserLanguage.en
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    files_dir = os.path.join(os.path.dirname(__file__), "..")
    fpath = os.path.join(files_dir, f"files/terms_{lang}.md")
    if not os.path.exists(fpath):
        fpath += ".example"
    return FileResponse(fpath)
 
@app.post("/api/login")
async def login(form_data: OAuth2PasswordRequestForm = Depends(), 
                session: Session = Depends(get_db_session)):
    q = select(User).where(User.email == form_data.username)
    user = session.exec(q).first()
    if ((not user) or (not user.is_active) or 
            (not check_password_against_hash(form_data.password, user.password_hash))):
        raise credentials_exception
    access_token = create_access_token(user.email_hash)
    refresh_token = create_refresh_token(user.email_hash)
    return {"access_token": access_token, "refresh_token": refresh_token, "token_type": "bearer"}

@app.get("/api/user/{user_id}", response_model=UserOut | None, status_code=status.HTTP_200_OK)
async def get_user(user_id: str, 
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if not current_user.is_admin:
        raise credentials_exception
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    return user

@app.delete("/api/user/{user_id}")
def delete_user(user_id: str, 
                current_user: User = Depends(get_current_user), 
                db_session: Session = Depends(get_db_session)):
    if not current_user.is_admin:
        raise credentials_exception
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    if user:
        db_session.delete(user)
        db_session.commit()
        return {"message": "User deleted"}
    return {"message": "User not found"}

@app.put("/api/user/{user_id}", response_model=UserOut | None, status_code=status.HTTP_200_OK)
def update_user(user_id: str, user_new: UserBase, 
                current_user: User = Depends(get_current_user), 
                db_session: Session = Depends(get_db_session)):
    if not current_user.is_admin:
        raise credentials_exception
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
        if (user_in.password == settings.admin_pass):
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
    now = now_tz_naive()
    if (existing_user and (not existing_user.is_active)):
        if (existing_user.activation_expires_at and 
            (existing_user.activation_expires_at < now)):
                db_session.delete(existing_user)
                db_session.commit()
                log_delete_user_to_refresh_registration(existing_user.email)
        else:
            return { "message": reg_message }
    user = User(
        firstname=user_in.firstname,
        surname=user_in.surname,
        email=user_in.email,
        email_hash=get_email_hash(user_in.email),
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

@app.get("/api/activate", response_class=HTMLResponse)
def activate_user(request: Request, email: str, token: str, db_session: Session = Depends(get_db_session)):
    now = now_tz_naive()
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
    elif (not user.activation_expires_at) or (user.activation_expires_at < now):
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

@app.post("/api/password-reset/request")
def request_password_reset(data: PasswordResetRequest, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    if_mail_exists_str = "If email exists, you will receive a mail verification code"
    user = db_session.exec(
        select(User).where(User.email == data.email)).first()
    if (not user) or (not user.is_active):
        return {"message": if_mail_exists_str }
    now = now_tz_naive()
    if user.reset_locked_until and (now < user.reset_locked_until):
        return {"message": if_mail_exists_str }
    code = None
    if ((not user.reset_code_hash) or 
        (not user.reset_expires_at) or 
            (now > user.reset_expires_at)):
                code = generate_reset_code()
                code_hash = otp_hmac(code) 
                expires_at = reset_code_expiry()
                user.reset_code_hash = code_hash
                user.reset_expires_at = expires_at
                log_password_reset_code_generation(user.email)
    if code:
        user.last_reset_mail_code_at = now
        db_session.add(user)
        db_session.commit()   
        background_tasks.add_task(send_reset_code_mail, user.email, code, user.language)
    
    return {"message": if_mail_exists_str}

@app.post("/api/password-reset/confirm")
def confirm_password_reset(data: PasswordResetConfirm, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    user = db_session.exec(
        select(User).where(User.email == data.email)).first()
    if (not user) or (not user.is_active):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    now = now_tz_naive()
    if user.reset_locked_until and now < user.reset_locked_until:
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    if ((not user.reset_code_hash) or 
            (not user.reset_expires_at) or 
                (now > user.reset_expires_at)):
        raise HTTPException(
            status_code=status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid"
        )
    if (not otp_verify(data.code, user.reset_code_hash)):
        user.reset_attempts += 1
        if user.reset_attempts > 3:
            user.reset_code_hash = None
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
    
    hashedpass = get_password_hash(data.new_password)
    user.password_hash = hashedpass
    user.reset_code_hash = None
    user.reset_expires_at = None
    user.reset_locked_until = None
    user.reset_attempts = 0
    user.last_reset_done_at = now
    # Cooldown check to avoid potential DoS attacks to the mail service
    can_send = ((not user.last_reset_mail_confirmation_at) or 
        ((now - user.last_reset_mail_confirmation_at).total_seconds() > MAIL_COOLDOWN_SECONDS)) 
    if can_send:
        user.last_reset_mail_confirmation_at = now
    db_session.add(user)
    db_session.commit()
    log_password_reset_success(user.email)
    if can_send:
        background_tasks.add_task(send_reset_successful_mail, user.email, user.language)

    return {"message": "Password reset successful"}
