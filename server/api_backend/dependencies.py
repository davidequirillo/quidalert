# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import Depends, Request
from fastapi.security import OAuth2PasswordBearer
from jwt import ExpiredSignatureError, InvalidTokenError
from sqlmodel import Session, select
from core import dbmgr
from core.exceptions import token_expired_exception
from models.general import User, GpsTokenData
from core.exceptions import token_not_valid_exception
from services.security import decode_token, from_timestamp_to_datetime_tz_naive

oauth2_scheme = OAuth2PasswordBearer(tokenUrl="/api/auth/login")
    
def get_db_session(request: Request):
    engine = request.app.state.db_engine
    yield from dbmgr.get_session(engine)

async def get_redis_session(request: Request):
    pool = request.app.state.redis_pool
    async with dbmgr.get_redis_conn(pool) as client:
        yield client

def get_s3_client(request: Request):
    return request.app.state.s3_client

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
    if user.is_superuser: # the superuser cannot be downgraded
        if ((user.is_admin == False) or 
                (user.is_reliable == False) or
                    (user.reliability_score < 100) or 
                        (user.is_blocked == True)):
            user.is_admin = True 
            user.is_reliable = True
            user.reliability_score = 100    
            user.is_blocked = False
            db_session.add(user)
            db_session.commit()
            db_session.refresh(user)
    return user

def get_geoposition_token_data(gps_token: str = Depends(oauth2_scheme)):
    try:
        token_data = decode_token(gps_token)
    except ExpiredSignatureError:
        raise token_expired_exception()
    except InvalidTokenError:
        raise token_not_valid_exception()
    except:
        raise token_not_valid_exception() 
    token_type = token_data.get("type")
    if (not token_type) or (token_type != "gps-update"): 
        raise token_not_valid_exception()
    user_id = token_data.get("sub")
    is_chief = token_data.get("user_is_chief") == 1
    user_role = token_data.get("user_role")
    if (not user_id) or (not user_role):
        raise token_not_valid_exception()
    return GpsTokenData(user_id=user_id, 
                    user_is_chief=is_chief, 
                    user_role=user_role)