# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from datetime import timedelta
from fastapi import (FastAPI, Depends,
    Request, HTTPException, BackgroundTasks)
from fastapi import status as http_status
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.middleware.cors import CORSMiddleware
from middleware.request_ctx import RequestContextMiddleware
from contextlib import asynccontextmanager
from sqlmodel import Session, select, desc
from fastapi.templating import Jinja2Templates
import firebase_admin
from apscheduler.schedulers.asyncio import AsyncIOScheduler
from apscheduler.triggers.cron import CronTrigger
from core.settings import settings
from core.logging import setup_logging, get_client_ip
from core import api_events, security_events
import services.localization as i18n
from models.general import (string_as_uuid, UserIn, User, UserLanguage, 
    PasswordResetRequest, PasswordResetConfirm, 
    RefreshToken, LoginSchema, RefreshTokenWrapper, FcmTokenWrapper,
    WhiteListEntry
    )
from services.security import (
    LOGIN_LOCK_HOURS, get_password_hash, check_password_against_hash, generate_random_token, get_token_hash, 
    generate_activation_token, activation_expiry, 
    now_tz_naive, from_timestamp_to_datetime_tz_naive, 
    generate_otp_code, otp_expiry, otp_hmac, otp_verify,
    RESET_LOCK_HOURS, MAIL_COOLDOWN_SECONDS,
    create_access_token, create_geoposition_token, create_refresh_token, decode_token, MAX_ACTIVE_REFRESH_TOKENS,
    check_token_against_hash, create_login_token,
    TokenExpiredException, TokenNotValidException
    )
from core import dbmgr, bucketmgr
from services.network import (
    send_activation_mail, send_reset_code_mail, send_reset_successful_mail,
    send_login_successful_mail, send_login_code_mail
    )
from services.periodics import do_locations_cleanup, do_demotions_cleanup
from core.exceptions import (
    token_expired_exception, token_not_valid_exception,
    credentials_exception, two_factor_locked_exception,
    two_factor_not_valid_exception, two_factor_required_response,
    forbidden_exception, invalid_request_exception
    )
from dependencies import get_db_session, get_current_user
from routers import users, alerts, terms, whitelist_entries

def init_logging_and_others():
    setup_logging()

async def init_engines(app: FastAPI):
    print("Initializing database engine...")
    app.state.db_engine = dbmgr.get_engine()
    print("Initializing redis handle...")
    app.state.redis_handle = dbmgr.get_redis_handle()
    if settings.redis_mode == "cluster":
        print("Redis cluster mode enabled")
    else:
        print("Redis single mode enabled")
    print("Testing redis connection...")
    try:
        redis_is_ok = await dbmgr.ping_redis(app.state.redis_handle)
        if redis_is_ok:
            print("Redis connection successful")
        else:
            print("Redis ping failed")
    except Exception as e:
        print(f"Redis connection failed: {e}")
    print("Initializing s3 client...")
    app.state.s3_client = bucketmgr.build_s3_client()
    print("Initializing Firebase Admin SDK...")
    fbase_path = settings.firebase_keys_path
    firebase_cred = firebase_admin.credentials.Certificate(fbase_path)
    if not firebase_admin._apps:
        firebase_admin.initialize_app(firebase_cred)
        print("Firebase Admin SDK initialized")
    else:
        print("Firebase Admin SDK already initialized")
    print("Initializing periodic tasks scheduler...")
    app.state.scheduler = AsyncIOScheduler()
    app.state.scheduler.add_job(
        do_locations_cleanup,
        trigger=CronTrigger(hour=19, minute=35), 
        args=[app.state.redis_handle],
        id="cleanup_expired_locations_job_v1",
    )
    app.state.scheduler.add_job(
        do_demotions_cleanup,
        trigger=CronTrigger(hour=17, minute=30), 
        args=[app.state.redis_handle],
        id="cleanup_expired_demotions_job_v1",
    )
    print("Starting periodic tasks scheduler...")
    app.state.scheduler.start()

async def shutdown_engines(app: FastAPI):
    print("Shutting down periodic tasks scheduler..")
    if app.state.scheduler:
        app.state.scheduler.shutdown()
    print("Shutting down s3 client...")
    if app.state.s3_client:
        app.state.s3_client.close()
    print("Shutting down redis...")
    if app.state.redis_handle:
        await dbmgr.shutdown_redis_handle(app.state.redis_handle)
    print("Shutting down postgres database...")
    if app.state.db_engine:
        app.state.db_engine.dispose()
    app.state.s3_client = None
    app.state.db_engine = None
    app.state.redis_handle = None
    app.state.scheduler = None

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up api framework...")
    is_testing = (settings.app_mode == "testing")
    if not is_testing:
        init_logging_and_others()
    if not is_testing:
        await init_engines(app)
    yield
    if not is_testing:
        await shutdown_engines(app)
    print("API shutdown complete")

app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_allow_origins, 
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"])

api_dirpath = "."
templates = Jinja2Templates(directory=os.path.join(api_dirpath, "templates"))

def check_refresh_token(token_data: dict | None, db_session: Session):
    if token_data is None:
        raise TokenNotValidException()
    user_id = token_data.get("sub")
    token_iat = token_data.get("iat")
    token_exp = token_data.get("exp")
    token_type = token_data.get("type")
    token_jti = token_data.get("jti")
    token_raw_secret = token_data.get("raw")
    if (not user_id) or (not token_iat) or (not token_exp) or \
        (not token_type) or (token_type != "refresh") or \
            (not token_jti) or (not token_raw_secret): 
        raise TokenNotValidException()
    user_id_as_uuid = string_as_uuid(user_id)
    token_jti_as_uuid = string_as_uuid(token_jti)
    statement = select(User).where(User.id == user_id_as_uuid)
    user = db_session.exec(statement).first()
    if user is None:
        raise TokenNotValidException()
    token_iat_dt = from_timestamp_to_datetime_tz_naive(token_iat)
    if token_iat_dt < user.last_reset_done_at:
        raise TokenExpiredException()
    q = select(RefreshToken).where(
        (RefreshToken.id == token_jti_as_uuid) and (RefreshToken.user_id == user.id))
    refresh_token = db_session.exec(q).first()
    if (refresh_token is None):
        raise TokenNotValidException
    if (refresh_token.is_revoked):
        raise TokenExpiredException()
    if not check_token_against_hash(token_raw_secret, refresh_token.raw_hash):
        raise TokenNotValidException()
    return (user, refresh_token) # user and db refresh token

def check_login_token(token_data: dict | None, user: User):
    if token_data is None:
        return False
    user_id = token_data.get("sub")
    token_iat = token_data.get("iat")
    token_exp = token_data.get("exp")
    token_type = token_data.get("type")
    if (not user_id) or (not token_iat) or (not token_exp) \
            or (not token_type) or (token_type != "login"):
        return False
    if user_id != str(user.id):
        return False
    token_iat_dt = from_timestamp_to_datetime_tz_naive(token_iat)
    if token_iat_dt < user.last_reset_done_at:
        return False
    if user.last_2fa_success_at and token_iat_dt < user.last_2fa_success_at:
        return False
    return True

# ENDPOINTS FROM DIFFERENT MODULES (users, alerts, etc.)
app.include_router(users.router)
app.include_router(alerts.router)
app.include_router(terms.router)
app.include_router(whitelist_entries.router)

# AUTHENTICATION ENDPOINTS (login, tokens, device)
@app.post("/api/auth/refresh")
def refresh_auth_tokens(
            wrapper: RefreshTokenWrapper, 
            db_session: Session = Depends(get_db_session)):
    try:
        token_data = decode_token(wrapper.refresh_token)
    except TokenExpiredException:
        raise token_expired_exception()
    except TokenNotValidException:
        raise token_not_valid_exception()
    except:
        token_data = None
    try: # check token validity (it returns user and database refresh token)
        user, rtoken = check_refresh_token(token_data, db_session)
    except TokenExpiredException:
        raise token_expired_exception()
    except TokenNotValidException:
        raise token_not_valid_exception()
    except:
        raise token_not_valid_exception()
    now = now_tz_naive()
    new_raw_secret = generate_random_token()
    new_raw_secret_hash = get_token_hash(new_raw_secret)
    rtoken.raw_hash = new_raw_secret_hash
    rtoken.ip_address=get_client_ip()
    rtoken.updated_at=now
    user.last_refresh_at=now
    db_session.add(user)
    db_session.add(rtoken)
    db_session.commit()
    new_access_token = create_access_token(str(user.id))
    new_gps_token = create_geoposition_token(
        str(user.id), user.is_chief, user.role)
    new_refresh_token = create_refresh_token(
        str(user.id), str(rtoken.id), 
        new_raw_secret, issued_at=now)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "gps_token": new_gps_token,
        "token_type": "bearer"
    }

@app.post("/api/auth/revoke")
def revoke_token(
            wrapper: RefreshTokenWrapper,
            db_session: Session = Depends(get_db_session)):
    try:
        token_data = decode_token(wrapper.refresh_token)
    except TokenExpiredException:
        raise token_expired_exception()
    except TokenNotValidException:
        raise token_not_valid_exception()
    except:
        token_data = None
    try: # check token validity (it returns user and database refresh token)
        _, rtoken = check_refresh_token(token_data, db_session)
    except TokenExpiredException:
        raise token_expired_exception()
    except TokenNotValidException:
        raise token_not_valid_exception()
    except:
        raise token_not_valid_exception()
    rtoken.is_revoked = True
    rtoken.fcm_token = None
    rtoken.fcm_token_updated_at = None
    rtoken.updated_at = now_tz_naive()
    db_session.add(rtoken)
    db_session.commit()    
    return {"message": "Logout successful"}

@app.post("/api/auth/login")
def login(data: LoginSchema,
            background_tasks: BackgroundTasks,
            db_session: Session = Depends(get_db_session)):
    now = now_tz_naive()
    new_login_token = None
    q = select(User).where(User.email == data.email)
    user = db_session.exec(q).first()
    if ((not user) or (not user.is_active) or 
            (not check_password_against_hash(data.password, user.password_hash))):
        security_events.log_login_failed(str(user.id) if user else "unknown", reason="invalid_credentials")
        raise credentials_exception()
    # if the 2FA code is present, we must verify it to generate a login token
    skip_2fa = False
    if data.login_code:
        if user.login_locked_until and now < user.login_locked_until:
            raise two_factor_locked_exception()
        if ((not user.login_code_hash) or 
                (not user.login_expires_at) or 
                    (now > user.login_expires_at)):
            raise two_factor_not_valid_exception()
        if (not otp_verify(data.login_code, user.login_code_hash)):
            user.login_2fa_attempts += 1
            security_events.log_login_2fa_failed(str(user.id), reason="invalid_code", attempts=user.login_2fa_attempts)
            if user.login_2fa_attempts > 3:
                user.login_code_hash = None
                user.login_expires_at = None
                user.login_locked_until = now + timedelta(hours=LOGIN_LOCK_HOURS)
                user.login_2fa_attempts = 0
                security_events.log_login_locked(str(user.id))
            db_session.add(user)
            db_session.commit()
            raise two_factor_not_valid_exception()
        user.login_code_hash = None
        user.login_expires_at = None
        user.login_locked_until = None
        user.login_2fa_attempts = 0
        user.last_2fa_success_at = now
        new_login_token = create_login_token(str(user.id))
        skip_2fa = True # 2FA verified successfully
        security_events.log_login_token_generation(str(user.id))
    # if a valid login_token is provided, we skip 2FA check
    elif data.login_token:
        try:
            token_data = decode_token(data.login_token)
        except TokenExpiredException:
            token_data = None
        except TokenNotValidException:
            token_data = None
        except:
            token_data = None
        if check_login_token(token_data, user):
            skip_2fa = True 
            security_events.log_login_token_used(str(user.id))
    if (not skip_2fa):
        # check if login has locked due to too many failed attempts
        if user.login_locked_until and (now < user.login_locked_until):
            raise two_factor_locked_exception()
        code = None
        # generate and send 2FA code here
        if ((not user.login_code_hash) or 
            (not user.login_expires_at) or 
            (now > user.login_expires_at)):
                code = generate_otp_code(6)
                code_hash = otp_hmac(code) 
                expires_at = otp_expiry()
                user.login_code_hash = code_hash
                user.login_expires_at = expires_at
                security_events.log_login_code_generation(str(user.id))
        if code:
            user.last_login_mail_code_at = now
            db_session.add(user)
            db_session.commit()
            background_tasks.add_task(send_login_code_mail, user.email, code, user.language)
        return two_factor_required_response()
    if (user.is_blocked) and (not user.is_superuser):
        raise forbidden_exception()
    q = select(RefreshToken).where(RefreshToken.user_id == user.id).order_by(desc(RefreshToken.updated_at))
    active_tokens = db_session.exec(q).all()
    # IMPORTANT: at the moment MAX_ACTIVE_REFRESH_TOKENS is 1 
    # (we allow only 1 device, for simplicity)
    if len(active_tokens) >= MAX_ACTIVE_REFRESH_TOKENS:
        oldest_token = active_tokens[-1]
        db_session.delete(oldest_token)
        db_session.flush()
    raw_random_str = generate_random_token()
    raw_str_hash = get_token_hash(raw_random_str)
    refresh_token = RefreshToken(
        user_id=user.id,
        raw_hash=raw_str_hash,
        ip_address=get_client_ip(),
        device_info=data.device_model,
        updated_at=now
    )
    user.last_login_done_at = now
    user.last_refresh_at = now
    # Cooldown check to avoid potential DoS attacks to the mail service
    can_send = ((not user.last_login_mail_confirmation_at) or 
        ((now - user.last_login_mail_confirmation_at).total_seconds() > MAIL_COOLDOWN_SECONDS)) 
    if can_send:
        user.last_login_mail_confirmation_at = now
    db_session.add(refresh_token)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(refresh_token)
    atoken = create_access_token(str(user.id))
    gps_token = create_geoposition_token(
        str(user.id), user.is_chief, user.role)
    rtoken = create_refresh_token(
        str(user.id), str(refresh_token.id), 
        raw_random_str, issued_at=now)
    security_events.log_login_successful(str(user.id))
    if can_send:
        background_tasks.add_task(send_login_successful_mail, user.email, user.language)
    return {"access_token": atoken, "refresh_token": rtoken, "gps_token": gps_token, "login_token": new_login_token, "token_type": "bearer"}

@app.post("/api/register-device")
def register_device_for_push_notifications(
    data: FcmTokenWrapper,
    current_user: User = Depends(get_current_user),
    db_session: Session = Depends(get_db_session)
):
    fcm_token = data.fcm_token
    if not fcm_token:
        raise invalid_request_exception("FCM token is required")
    q = select(RefreshToken).where(RefreshToken.user_id == current_user.id)
    results = db_session.exec(q).all()
    if not results:
        raise token_not_valid_exception()
    rtoken = results[0] # at the moment we keep only one active refresh token per user (one device)
    rtoken.fcm_token = fcm_token
    rtoken.fcm_token_updated_at = now_tz_naive()
    db_session.add(rtoken)
    db_session.commit()
    return {"message": "Device registered for push notifications"}

# USER REGISTRATION ENDPOINTS (registration, activation, password change).
@app.post("/api/register")
def register_user(user_in: UserIn, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    # We will return a unique registration message for almost all cases, for security
    reg_message = "If email address is valid, you will receive an activation mail message"
    is_an_admin = False
    is_the_superuser = False
    is_in_whitelist = False 
    auth_by = None # authorized by
    auth_at = None # authorized at
    now = now_tz_naive()
    log_deleted_user = False
    if user_in.email and user_in.email.strip() != "":
        email_lowercase = user_in.email.strip().lower()
    else:
        email_lowercase = ""
    existing_user = db_session.exec(
        select(User).where(User.email == email_lowercase)
    ).first()
    if existing_user:
        if existing_user.is_active:
            return { "message": reg_message }
        else:
            if (existing_user.activation_expires_at and 
                    (existing_user.activation_expires_at < now)):
                db_session.delete(existing_user)
                db_session.flush()
                log_deleted_user = True
            else:
                return { "message": reg_message }
    # If database is empty and password is correct we insert the admin
    if db_session.exec(select(User).limit(1)).first() is None:
        if (user_in.password == settings.admin_pass):
            is_an_admin = True
            is_the_superuser = True
    else: # else we check the email address existence in a whitelist
        whitelist_entry = db_session.exec(
            select(WhiteListEntry).where(WhiteListEntry.email == email_lowercase)
        ).first()
        if whitelist_entry:
            auth_by = whitelist_entry.created_by
            auth_at = whitelist_entry.created_at
            is_in_whitelist = True
    if (not is_in_whitelist) and (not is_the_superuser):
        return { "message": reg_message }
    password_hashed = get_password_hash(user_in.password)
    act_token = generate_activation_token()
    act_expires_at = activation_expiry()
    user = User(
        firstname=user_in.firstname,
        surname=user_in.surname,
        email=email_lowercase,
        language=user_in.language,
        password_hash=password_hashed,
        is_superuser=is_the_superuser,
        is_admin=is_an_admin,
        is_active=False,
        activation_code=act_token,
        activation_expires_at=act_expires_at,
        authorized_by=auth_by,
        authorized_at=auth_at
    )
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    if log_deleted_user:
        api_events.log_deleted_user_to_renew_registration(str(user.id))
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
        request,
        "activation_result.html",
        {
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
                code = generate_otp_code(10)
                code_hash = otp_hmac(code) 
                expires_at = otp_expiry()
                user.reset_code_hash = code_hash
                user.reset_expires_at = expires_at
                security_events.log_password_reset_code_generation(str(user.id))
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
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    now = now_tz_naive()
    if user.reset_locked_until and now < user.reset_locked_until:
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid",
        )
    if ((not user.reset_code_hash) or 
            (not user.reset_expires_at) or 
                (now > user.reset_expires_at)):
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
            detail="Code or email not valid"
        )
    if (not otp_verify(data.code, user.reset_code_hash)):
        user.reset_attempts += 1
        security_events.log_password_reset_failed(str(user.id), reason="invalid_code", attempts=user.reset_attempts)
        if user.reset_attempts > 3:
            user.reset_code_hash = None
            user.reset_expires_at = None
            user.reset_locked_until = now + timedelta(hours=RESET_LOCK_HOURS)
            user.reset_attempts = 0
            security_events.log_password_reset_locked(str(user.id))
        db_session.add(user)
        db_session.commit()
        raise HTTPException(
            status_code=http_status.HTTP_400_BAD_REQUEST,
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
    security_events.log_password_reset_successful(str(user.id))
    if can_send:
        background_tasks.add_task(send_reset_successful_mail, user.email, user.language)
    return {"message": "Password reset successful"}
