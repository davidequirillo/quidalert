# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from datetime import timedelta
import html
from fastapi import (FastAPI, Depends,
    Request, Response, 
    HTTPException, status, BackgroundTasks, 
    File, UploadFile, Form)
from fastapi.concurrency import run_in_threadpool
from fastapi.responses import FileResponse, HTMLResponse, StreamingResponse
from fastapi.security import OAuth2PasswordRequestForm, OAuth2PasswordBearer
from fastapi.middleware.cors import CORSMiddleware
from middleware.request_ctx import RequestContextMiddleware
from contextlib import asynccontextmanager
import uuid as uuid_pkg
from sqlmodel import Session, select, update, delete, desc, col
from fastapi.templating import Jinja2Templates
from jwt.exceptions import (
    InvalidTokenError, ExpiredSignatureError,
    InvalidSubjectError, InvalidIssuedAtError,
    InvalidJTIError
)
from core.settings import settings
from core.logging import setup_logging
from core.security_events import (
    get_client_ip,
    log_password_reset_code_generation,
    log_password_reset_successful,
    log_password_reset_locked,
    log_deleted_user_to_renew_registration,
    log_login_successful,
    log_login_code_generation,
    log_login_locked,
    log_login_token_generation
)
import services.localization as i18n
from models.general import (Alert, UserBase, UserIn, User, UserOut, UserOutSmall, UserLanguage,
    PasswordResetRequest, PasswordResetConfirm, 
    RefreshToken, LoginSchema, RefreshTokenWrapper,
    WhiteListEntry, EmailListDict,
    UserInCompleteProfile, PromotionSchema
    )
from services.security import (
    LOGIN_LOCK_HOURS, get_password_hash, check_password_against_hash, generate_random_token, get_token_hash, 
    generate_activation_token, activation_expiry, 
    now_tz_naive, from_timestamp_to_datetime_tz_naive, 
    generate_otp_code, otp_expiry, otp_hmac, otp_verify, get_email_hash, check_email_against_hash,
    RESET_LOCK_HOURS, MAIL_COOLDOWN_SECONDS,
    create_access_token, create_refresh_token, decode_token, MAX_ACTIVE_REFRESH_TOKENS,
    check_token_against_hash, create_login_token
    )
from core import dbmgr, bucketmgr
from services.network import (
    send_activation_mail, send_reset_code_mail, send_reset_successful_mail,
    send_login_successful_mail, send_login_code_mail
    )
from core.exceptions import (
    token_expired_exception, token_not_valid_exception,
    credentials_exception, two_factor_locked_exception,
    two_factor_not_valid_exception, two_factor_required_response,
    forbidden_exception,
    invalid_file_type_exception, bad_file_upload_exception,
    unsafe_file_exception, file_too_large_exception
    )
from services.fileutils import (
    MAX_FILE_SIZE, MAX_SMALL_FILE_SIZE, 
    )

def init_settings():
    setup_logging()

@asynccontextmanager
async def lifespan(app: FastAPI):
    print("Starting up api framework...")
    init_settings()
    app.state.db_engine = dbmgr.get_engine()
    app.state.s3_client = bucketmgr.get_s3_client()
    yield
    print("Shutting down api framework...")
    app.state.db_engine.dispose()
    app.state.db_engine = None
    app.state.s3_client = None

app = FastAPI(lifespan=lifespan)

app.add_middleware(RequestContextMiddleware)
app.add_middleware(CORSMiddleware,
    allow_origins=settings.cors_allow_origins, 
    allow_credentials=False,
    allow_methods=["GET", "POST", "PUT", "DELETE"],
    allow_headers=["Authorization", "Content-Type"])

def get_db_session():
    engine = app.state.db_engine
    yield from dbmgr.get_session(engine)

def get_s3_client():
    return app.state.s3_client

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="api/auth/login")
api_dirpath = "."
templates = Jinja2Templates(directory=os.path.join(api_dirpath, "templates"))
FILES_DIR = "./files"

def get_current_user(access_token: str = Depends(oauth2_scheme),
                    db_session: Session = Depends(get_db_session)):
    try:
        token_data = decode_token(access_token)
    except ExpiredSignatureError:
        raise token_expired_exception() # we raise a specific error
    except InvalidTokenError:
        raise token_not_valid_exception()
    except:
        token_data = None
    if token_data is None:
        raise token_not_valid_exception() 
    user_id = token_data.get("sub")
    token_iat = token_data.get("iat")
    token_exp = token_data.get("exp")
    token_type = token_data.get("type")
    if (not user_id) or (not token_iat) or (not token_exp) or \
        (not token_type) or (token_type != "access"): 
            raise token_not_valid_exception() 
    statement = select(User).where(User.id == user_id)
    user = db_session.exec(statement).first()
    if user is None:
        raise token_not_valid_exception()
    token_iat_dt = from_timestamp_to_datetime_tz_naive(token_iat)   
    if token_iat_dt < user.last_reset_done_at:
        raise token_expired_exception()    
    return user

def check_refresh_token(token_data: dict | None, db_session: Session):
    if token_data is None:
        raise InvalidTokenError
    user_id = token_data.get("sub")
    token_iat = token_data.get("iat")
    token_exp = token_data.get("exp")
    token_type = token_data.get("type")
    token_jti = token_data.get("jti")
    token_raw_secret = token_data.get("raw")
    if (not user_id) or (not token_iat) or (not token_exp) or \
        (not token_type) or (token_type != "refresh") or \
            (not token_jti) or (not token_raw_secret): 
        raise InvalidTokenError
    statement = select(User).where(User.id == user_id)
    user = db_session.exec(statement).first()
    if user is None:
        raise InvalidSubjectError
    token_iat_dt = from_timestamp_to_datetime_tz_naive(token_iat)
    if token_iat_dt < user.last_reset_done_at:
        raise InvalidIssuedAtError
    q = select(RefreshToken).where(
        (RefreshToken.id == token_jti) and (RefreshToken.user_id == user.id))
    refresh_token = db_session.exec(q).first()
    if (refresh_token is None) or (refresh_token.is_revoked):
        raise ExpiredSignatureError
    if not check_token_against_hash(token_raw_secret, refresh_token.raw_hash):
        raise InvalidJTIError
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
    return True

@app.post("/api/auth/refresh")
def refresh_auth_tokens(
            wrapper: RefreshTokenWrapper, 
            db_session: Session = Depends(get_db_session)):
    try:
        token_data = decode_token(wrapper.refresh_token)
    except ExpiredSignatureError:
        raise token_expired_exception()
    except InvalidTokenError:
        raise token_not_valid_exception()
    except:
        token_data = None
    try: # check token validity (it returns user and database refresh token)
        user, rtoken = check_refresh_token(token_data, db_session)
    except InvalidIssuedAtError or ExpiredSignatureError:
        raise token_expired_exception()
    except:
        raise token_not_valid_exception()
    now = now_tz_naive()
    new_raw_secret = generate_random_token()
    new_raw_secret_hash = get_token_hash(new_raw_secret)
    rtoken.raw_hash = new_raw_secret_hash
    rtoken.ip_address=get_client_ip()
    rtoken.updated_at=now
    user.last_refresh_at = now
    db_session.add(user)
    db_session.add(rtoken)
    db_session.commit()
    new_access_token = create_access_token(str(user.id))
    new_refresh_token = create_refresh_token(
        str(user.id), str(rtoken.id), 
        new_raw_secret, created_at=now)
    return {
        "access_token": new_access_token,
        "refresh_token": new_refresh_token,
        "token_type": "bearer"
    }

@app.post("/api/auth/revoke")
def revoke_token(
            wrapper: RefreshTokenWrapper,
            db_session: Session = Depends(get_db_session)):
    try:
        token_data = decode_token(wrapper.refresh_token)
    except ExpiredSignatureError:
        raise token_expired_exception()
    except InvalidTokenError:
        raise token_not_valid_exception()
    except:
        token_data = None
    try: # check token validity (it returns user and database refresh token)
        _, rtoken = check_refresh_token(token_data, db_session)
    except InvalidIssuedAtError or ExpiredSignatureError:
        raise token_expired_exception()
    except:
        raise token_not_valid_exception()
    rtoken.is_revoked = True
    db_session.add(rtoken)
    db_session.commit()    
    return {"detail": "Logout successful"}

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
        raise credentials_exception()
    # if the 2FA code is present, we must verify it to generate a login token
    if data.login_code:
        if user.login_locked_until and now < user.login_locked_until:
            raise two_factor_locked_exception()
        if ((not user.login_code_hash) or 
                (not user.login_expires_at) or 
                    (now > user.login_expires_at)):
            raise two_factor_not_valid_exception()
        if (not otp_verify(data.login_code, user.login_code_hash)):
            user.login_2fa_attempts += 1
            if user.login_2fa_attempts > 3:
                user.login_code_hash = None
                user.login_expires_at = None
                user.login_locked_until = now + timedelta(hours=LOGIN_LOCK_HOURS)
                user.login_2fa_attempts = 0
                log_login_locked(str(user.id))
            db_session.add(user)
            db_session.commit()
            raise two_factor_not_valid_exception()
        new_login_token = create_login_token(str(user.id))
        user.login_code_hash = None
        user.login_expires_at = None
        user.login_locked_until = None
        user.login_2fa_attempts = 0
        skip_2fa = True # 2FA verified successfully
        log_login_token_generation(str(user.id))
    # if a valid login_token is provided, we skip 2FA check
    elif data.login_token:
        try:
            token_data = decode_token(data.login_token)
        except ExpiredSignatureError:
            token_data = None
        except InvalidTokenError:
            token_data = None
        except:
            token_data = None
        if check_login_token(token_data, user):
            skip_2fa = True
        else:
            skip_2fa = False
    else:
        skip_2fa = False
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
                log_login_code_generation(str(user.id)) 
        if code:
            user.last_login_mail_code_at = now
            db_session.add(user)
            db_session.commit()
            background_tasks.add_task(send_login_code_mail, user.email, code, user.language)
        return two_factor_required_response()
    q = select(RefreshToken).where(RefreshToken.user_id == user.id).order_by(desc(RefreshToken.updated_at))
    active_tokens = db_session.exec(q).all()
    if len(active_tokens) >= MAX_ACTIVE_REFRESH_TOKENS:
        oldest_token = active_tokens[-1]
        db_session.delete(oldest_token)
        db_session.flush()
    refresh_token_id = uuid_pkg.uuid4()
    raw_random_str = generate_random_token()
    raw_str_hash = get_token_hash(raw_random_str)
    refresh_token = RefreshToken(
        id=refresh_token_id,
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
    atoken = create_access_token(str(user.id))
    rtoken = create_refresh_token(
        str(user.id), str(refresh_token_id), 
        raw_random_str, created_at=now)
    log_login_successful(str(user.id))
    if can_send:
        background_tasks.add_task(send_login_successful_mail, user.email, user.language)
    return {"access_token": atoken, "refresh_token": rtoken, "login_token": new_login_token, "token_type": "bearer"}

@app.post("/api/register")
def register_user(user_in: UserIn, background_tasks: BackgroundTasks, db_session: Session = Depends(get_db_session)):
    # We will return a unique registration message for almost all cases, for security
    reg_message = "If email address is valid, you will receive an activation mail message"
    is_an_admin = False
    is_the_superuser = False
    is_in_whitelist = False 
    auth_by = None # authorized by
    auth_at = None # authorized at
    if user_in.email and user_in.email.strip() != "":
        email_lowercase = user_in.email.lower()
    else:
        email_lowercase = ""
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
    existing_user = db_session.exec(
        select(User).where(User.email == email_lowercase)
    ).first()
    if existing_user and existing_user.is_active:
        return { "message": reg_message }
    password_hashed = get_password_hash(user_in.password)
    act_token = generate_activation_token()
    act_expires_at = activation_expiry()
    now = now_tz_naive()
    log_deleted_user = False
    if (existing_user and (not existing_user.is_active)):
        if (existing_user.activation_expires_at and 
            (existing_user.activation_expires_at < now)):
                db_session.delete(existing_user)
                db_session.flush()
                log_deleted_user = True
        else:
            return { "message": reg_message }
    user = User(
        firstname=user_in.firstname,
        surname=user_in.surname,
        email=email_lowercase,
        email_hash=get_email_hash(email_lowercase),
        language=user_in.language,
        password_hash=password_hashed,
        is_superuser=is_the_superuser,
        is_admin = is_an_admin,
        is_active=False,
        activation_code=act_token,
        activation_expires_at=act_expires_at,
        authorized_by=auth_by,
        authorized_at=auth_at
    )
    db_session.add(user)
    db_session.commit()
    if log_deleted_user:
        log_deleted_user_to_renew_registration(user.email)
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
                code = generate_otp_code(10)
                code_hash = otp_hmac(code) 
                expires_at = otp_expiry()
                user.reset_code_hash = code_hash
                user.reset_expires_at = expires_at
                log_password_reset_code_generation(str(user.id))
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
            log_password_reset_locked(str(user.id))
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
    log_password_reset_successful(str(user.id))
    if can_send:
        background_tasks.add_task(send_reset_successful_mail, user.email, user.language)

    return {"message": "Password reset successful"}

@app.get("/api/terms")
def get_terms(request: Request,
            response: Response,
            s3_client = Depends(get_s3_client),
            ):
    lang = request.headers.get('Accept-Language')
    if (lang != UserLanguage.en) and (lang != UserLanguage.it):
        lang = UserLanguage.en
    response.headers["Content-Type"] = "text/markdown; charset=utf-8"
    try:
        obj = s3_client.get_object(
            Bucket=settings.minio_bucket_name, 
            Key=f"terms_{lang}.md")
    except Exception:
        obj = None
    if not obj:
        fpath = os.path.join(FILES_DIR, f"terms_{lang}.md.example")
        return FileResponse(fpath)
    else:
        content = obj["Body"]
        return StreamingResponse(content=content, media_type="text/markdown; charset=utf-8")

@app.post("/api/terms") # upload legal terms file (multipart/form-data)
async def upload_terms(file: UploadFile = File(...), 
        language: str = Form(...), 
        current_user: User = Depends(get_current_user),
        s3_client=Depends(get_s3_client)
    ):
    if not current_user.is_admin:
        raise forbidden_exception()
    if (file is None) or (file.filename is None) or (file.filename == ""):
        raise bad_file_upload_exception()
    if not file.filename.endswith(('.md', '.markdown')):
        raise invalid_file_type_exception()
    if file.content_type not in ["text/markdown", "text/plain"]:
        raise invalid_file_type_exception()
    content = await file.read()
    file_size = len(content)
    if file_size > MAX_SMALL_FILE_SIZE:
        raise file_too_large_exception(MAX_SMALL_FILE_SIZE)
    try:
        text_content = content.decode("utf-8")
    except UnicodeDecodeError:
        raise bad_file_upload_exception()
    safe_text = html.escape(text_content)
    lang = language
    if (lang != UserLanguage.en) and (lang != UserLanguage.it):
        lang = UserLanguage.en
    fname = f"terms_{lang}.md"
    try:
        await run_in_threadpool(
            lambda: s3_client.put_object(
                Body=safe_text.encode("utf-8"), 
                Bucket=settings.minio_bucket_name, 
                Key=fname,
                ContentType=file.content_type
            )
        )   
    except Exception as e:
        raise HTTPException(
            status_code=status.HTTP_500_INTERNAL_SERVER_ERROR,
            detail="Error uploading file to S3"
        )
    return {"message": "Terms uploaded successfully"}

@app.get("/api/whitelist-entries", response_model=list[WhiteListEntry])
def get_whitelist_entries(
                email: str | None = None,
                authorizer: str | None = None,
                offset: int = 0,
                limit: int = 100,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if offset < 0:
        offset = 0
    if limit not in [10, 100, 1000]:
        limit = 100
    if email and (email != ""):
        entries = db_session.exec(
            select(WhiteListEntry).where(
                WhiteListEntry.email == email.lower())).all()    
    elif (authorizer and (authorizer != "")):
        if current_user.is_admin:
            authorizer_email = authorizer.lower()
        else: # officers can see (in bulk) only their created entries
            authorizer_email = current_user.email
        entries = db_session.exec(
            select(WhiteListEntry).where(
                WhiteListEntry.created_by == authorizer_email
                    ).offset(offset).limit(limit)).all()
    else:
        if (not current_user.is_admin):
            # officers can see (in bulk) only their created entries
            entries = db_session.exec(
                select(WhiteListEntry).where(
                    WhiteListEntry.created_by == current_user.email
                        ).offset(offset).limit(limit)).all()
        else:
            entries = db_session.exec(
                select(WhiteListEntry).offset(offset).limit(limit)
                    ).all()
    return entries

@app.post("/api/whitelist-entries")
def add_whitelist_entries(
                dict: EmailListDict,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    failed_emails = []
    added_count = 0
    existing_count = 0
    for e in dict.emails:
        try:
            if (e is None) or (e.strip() == ""):
                continue
            entry = WhiteListEntry(email=e.lower(), created_by=current_user.email)
            if db_session.exec(
                select(WhiteListEntry).where(WhiteListEntry.email == entry.email)
            ).first():
                existing_count += 1
                continue # skip entry if already exists
            db_session.add(entry)
            added_count += 1
        except Exception:
            failed_emails.append(e)
            continue
    if added_count > 0:
        db_session.commit()
    return {
        "message": "Entries processed",
        "total_count": len(dict.emails),
        "added_count": added_count,
        "existing_count": existing_count,
        "failed_count": len(failed_emails), 
        "failed_emails": failed_emails
    }

@app.delete("/api/whitelist-entries")
def delete_whitelist_entries(
                email: str | None = None,
                my_entries: str | None = None,
                all: str | None = None,
                current_user: User = Depends(get_current_user),
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    deleted_count = 0
    total_count = 0
    if email and (email != ""):
        q = select(WhiteListEntry).where(WhiteListEntry.email == email.lower())
        entry = db_session.exec(q).first()
        if entry: # officers can delete only their own entries
            total_count = 1
            if (not current_user.is_admin) and (entry.created_by != current_user.email):
                raise forbidden_exception()
            db_session.delete(entry)
            db_session.commit()
            deleted_count = 1
    elif my_entries and (my_entries.lower() == "yes"):
        statement = delete(WhiteListEntry).where(WhiteListEntry.created_by == current_user.email) # type: ignore
        result = db_session.exec(statement)
        deleted_count = result.rowcount
        total_count = deleted_count
        db_session.commit()
    elif all and (all.lower() == "yes"):
        if not current_user.is_admin: # officers cannot delete all entries
            raise forbidden_exception()
        statement = delete(WhiteListEntry).where(True) # type: ignore
        result = db_session.exec(statement)
        deleted_count = result.rowcount
        total_count = deleted_count
        db_session.commit()
    return {
        "message": "Entries deleted",
        "total_count": total_count,
        "deleted_count": deleted_count
    }

@app.get("/api/user/profile", response_model=UserOut | None, status_code=status.HTTP_200_OK)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@app.put("/api/user/profile")
def update_profile(user_data: UserInCompleteProfile, 
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    current_user.firstname = user_data.firstname
    current_user.surname = user_data.surname
    current_user.street = user_data.street
    current_user.postal_code = user_data.postal_code
    current_user.city = user_data.city
    current_user.province = user_data.province
    current_user.country = user_data.country
    current_user.birthdate = user_data.birthdate
    current_user.phone = user_data.phone
    db_session.add(current_user)
    db_session.commit()
    return { "message": "Profile updated" }

@app.get("/api/users", response_model=list[UserOutSmall], status_code=status.HTTP_200_OK)
def get_users(
            email: str | None = None,
            firstname: str | None = None,
            surname: str | None = None,
            authorizer: str | None = None,
            type: str | None = None,
            role: str | None = None,
            status: str | None = None,
            offset: int = 0,
            limit: int = 100,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if offset < 0:
        offset = 0
    if limit not in [10, 100, 1000]:
        limit = 100
    if email and (email != ""):
        users = db_session.exec(
            select(User).where(User.email == email.lower())).all()
        return users
    if (current_user.is_admin):
        statement = select(User)
    else: # officers can see (in bulk) only users they authorized
        statement = select(User).where(User.authorized_by == current_user.email)
    if firstname and (firstname != ""):
        statement = statement.where(User.firstname == firstname) 
    if surname and (surname != ""):
        statement = statement.where(User.surname == surname) 
    if authorizer and (authorizer != ""):
        statement = statement.where(User.authorized_by == authorizer.lower()) 
    if type and (type != ""):
        if type == "admin":
            statement = statement.where(User.is_admin == True) 
        elif type == "officer":
            statement = statement.where(User.is_officer == True) 
        elif type == "chief":
            statement = statement.where(User.is_chief == True)
    if role and (role != ""):
        statement = statement.where(User.role == role)
    if status and (status != ""):
        statement = statement.where(User.status == status)
    users = db_session.exec(statement.offset(offset).limit(limit)).all()
    return users

@app.post("/api/get-users-by-emails", response_model=list[UserOutSmall], status_code=status.HTTP_200_OK)
def get_users_by_emails(
            dict: EmailListDict,
            offset: int = 0,
            limit: int = 100,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if offset < 0:
        offset = 0
    if limit not in [10, 100, 1000]:
        limit = 100
    statement = select(User).where(User.email.in_(dict.emails)).offset(offset).limit(limit) # type: ignore
    users = db_session.exec(statement).all()
    return users
    
@app.get("/api/user/{user_id}")
def get_user(user_id: str, 
            current_user: User = Depends(get_current_user),
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    user = db_session.exec(select(User).where(User.id == user_id)).first()
    recent_alerts = db_session.exec(
        select(Alert).where(Alert.user_id == user_id).order_by(desc(Alert.created_at)).limit(5)
    ).all()
    return {"user": user, "alerts": recent_alerts}

@app.post("/api/promote-users")
def promote_users(
            promotion_schema: PromotionSchema,
            email: str | None = None,
            firstname: str | None = None,
            surname: str | None = None,
            authorizer: str | None = None,
            type: str | None = None,
            role: str | None = None,
            status: str | None = None,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if (promotion_schema.type):
        if not current_user.is_admin: # officers cannot change users type
            raise forbidden_exception()
    if (current_user.is_admin):
        statement = update(User)
    else: # officers can update only users authorized by them
        statement = update(User).where(User.authorized_by == current_user.email) # type: ignore
    if email and (email != ""):
        statement = statement.where(
                User.email == email.lower()) # type: ignore
    if firstname and (firstname != ""):
        statement = statement.where(User.firstname == firstname) # type: ignore 
    if surname and (surname != ""):
        statement = statement.where(User.surname == surname) # type: ignore
    if authorizer and (authorizer != ""):
        statement = statement.where(User.authorized_by == authorizer.lower()) # type: ignore 
    if type and (type != ""):
        if type == "admin":
            statement = statement.where(User.is_admin == True) # type: ignore 
        elif type == "officer":
            statement = statement.where(User.is_officer == True) # type: ignore
        elif type == "chief":
            statement = statement.where(User.is_chief == True) # type: ignore
    if role and (role != ""):
        statement = statement.where(User.role == role) # type: ignore
    if status and (status != ""):
        statement = statement.where(User.status == status) # type: ignore
    # update fields according to promotion schema
    if (promotion_schema.type == "admin"):
        statement = statement.values(is_admin=True)
    elif (promotion_schema.type == "officer"):
        statement = statement.values(is_officer=True)
    elif (promotion_schema.type == "chief"):
        statement = statement.values(is_chief=True)
    if promotion_schema.role:
        statement = statement.values(role = promotion_schema.role)
    if promotion_schema.status:
        statement = statement.values(status = promotion_schema.status)
    if promotion_schema.authorizer:
        authorizer_user = db_session.exec(
            select(User).where(
                User.email == promotion_schema.authorizer.lower()
            )).first() # check if authorizer exists
        if authorizer_user:
            statement = statement.values(authorized_by = promotion_schema.authorizer.lower(), authorized_at = now_tz_naive())
        else:
            return {"message": "Authorizer email not valid", "updated_count": 0}
    statement = statement.values(updated_by = current_user.email, updated_at = now_tz_naive())
    result = db_session.exec(statement)
    updated_count = result.rowcount
    return {"message": "Operation completed", "updated_count": updated_count}

@app.post("/api/promote-users-by-emails")
def promote_users_by_emails(
            dict: EmailListDict,
            promotion_schema: PromotionSchema,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if (promotion_schema.type):
        if not current_user.is_admin: # officers cannot change users type
            raise forbidden_exception()
    if (current_user.is_admin):
        statement = update(User)
    else: # officers can update only users authorized by them
        statement = update(User).where(User.authorized_by == current_user.email) # type: ignore
    statement = statement.where(User.email.in_(dict.emails)) # type: ignore
    # update fields according to promotion schema
    if (promotion_schema.type == "admin"):
        statement = statement.values(is_admin=True)
    elif (promotion_schema.type == "officer"):
        statement = statement.values(is_officer=True)
    elif (promotion_schema.type == "chief"):
        statement = statement.values(is_chief=True)
    if promotion_schema.role:
        statement = statement.values(role = promotion_schema.role)
    if promotion_schema.status:
        statement = statement.values(status = promotion_schema.status)
    if promotion_schema.authorizer:
        authorizer_user = db_session.exec(
            select(User).where(
                User.email == promotion_schema.authorizer.lower()
            )).first() # check if authorizer exists
        if authorizer_user:
            statement = statement.values(authorized_by = promotion_schema.authorizer.lower(), authorized_at = now_tz_naive())
        else:
            return {"message": "Authorizer email not valid", "updated_count": 0}
    statement = statement.values(updated_by = current_user.email, updated_at = now_tz_naive())
    result = db_session.exec(statement)
    updated_count = result.rowcount
    return {"message": "Operation completed", "updated_count": updated_count}