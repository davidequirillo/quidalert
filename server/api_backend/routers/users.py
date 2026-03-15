# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, any_, desc, select, update
from starlette import status as http_status
from starlette.exceptions import HTTPException
from models.general import Alert, EmailListDict, PromotionSchema, User, UserInCompleteProfile, UserOut, UserOutPaginated, UserOutWithAlerts
from dependencies import get_db_session, get_current_user, get_redis_session
from core.exceptions import forbidden_exception
from core.dbmgr import get_redis_chief_locations_key, REDIS_MUTEX_CHIEF_UPDATE_KEY
from services.security import now_tz_naive

router = APIRouter(
    tags=["Users"]
)

@router.get("/api/user/profile", response_model=UserOut | None, status_code=http_status.HTTP_200_OK)
def get_profile(current_user: User = Depends(get_current_user)):
    return current_user

@router.put("/api/user/profile")
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

@router.get("/api/users", response_model=UserOutPaginated, status_code=http_status.HTTP_200_OK)
def get_users(
            email: str | None = None,
            firstname: str | None = None,
            surname: str | None = None,
            authorizer: str | None = None,
            type: str | None = None,
            role: str | None = None,
            status: str | None = None,
            last_seen_id: str | None = None,
            limit: int = 100,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if limit not in [10, 100, 1000]:
        limit = 100
    next_cursor = None
    if email and (email != ""):
        users = db_session.exec(
            select(User).where(User.email == email.lower())).all()
        return { 'users': users, 'next_cursor': next_cursor }
    statement = select(User)
    if not current_user.is_admin: # officers can see (in bulk) only users they authorized
        statement = statement.where(User.authorized_by == current_user.email)
    if authorizer:
        statement = statement.where(User.authorized_by == authorizer.lower()) 
    if last_seen_id:
        statement = statement.where(User.id < last_seen_id) # type: ignore
    if firstname and (firstname != ""):
        statement = statement.where(User.firstname == firstname) 
    if surname and (surname != ""):
        statement = statement.where(User.surname == surname) 
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
        if status == "ok":
            statement = statement.where(User.is_reliable == True) 
        elif status == "unreliable":
            statement = statement.where(User.is_reliable == False) 
        elif status == "blocked":
            statement = statement.where(User.is_blocked == True)
    statement = statement.order_by(desc(User.id)).limit(limit)
    users = db_session.exec(statement).all()
    if users:
        next_cursor = str(users[-1].id)
    return { 'users': users, 'next_cursor': next_cursor }

@router.post("/api/users/get-by-emails", response_model=UserOutPaginated, status_code=http_status.HTTP_200_OK)
def get_users_by_emails(
            dict: EmailListDict,
            last_seen_id: str | None = None,
            limit: int = 100,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if limit not in [10, 100, 1000]:
        limit = 100
    next_cursor = None
    statement = select(User)
    if (last_seen_id):
        statement = statement.where(User.id < last_seen_id) # type: ignore
    statement = statement.where(User.email == any_(dict.emails))
    statement = statement.order_by(desc(User.id)).limit(limit)
    users = db_session.exec(statement).all()
    if users:
        next_cursor = str(users[-1].id)
    return { 'users': users, 'next_cursor': next_cursor }
    
@router.get("/api/user/{user_id}", response_model=UserOutWithAlerts, status_code=http_status.HTTP_200_OK)
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

@router.post("/api/users/promote") # promote/demote users in bulk according to filters and promotion schema
async def promote_users(
            promotion_schema: PromotionSchema,
            email: str | None = None,
            firstname: str | None = None,
            surname: str | None = None,
            authorizer: str | None = None,
            type: str | None = None,
            role: str | None = None,
            status: str | None = None,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session),
            redis_client = Depends(get_redis_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if (promotion_schema.type) and (promotion_schema.type != ""):
        if not current_user.is_admin: # officers cannot change users type
            raise forbidden_exception()
    def db_update_logic(): 
        if (current_user.is_admin):
            statement = update(User)
        else: # officers can update only users authorized by them
            statement = update(User).where(User.authorized_by == current_user.email) # type: ignore
        if email and (email != ""):
            statement = statement.where(
                User.email == email.lower()) # type: ignore
        if authorizer and (authorizer != ""):
            statement = statement.where(User.authorized_by == authorizer.lower()) # type: ignore
        if firstname and (firstname != ""):
            statement = statement.where(User.firstname == firstname) # type: ignore 
        if surname and (surname != ""):
            statement = statement.where(User.surname == surname) # type: ignore 
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
            if status == "ok":
                statement = statement.where(User.is_reliable == True) # type: ignore 
            elif status == "unreliable":
                statement = statement.where(User.is_reliable == False) # type: ignore
            elif status == "blocked":
                statement = statement.where(User.is_blocked == True) # type: ignore
        # update fields according to promotion schema
        if (promotion_schema.type == "admin"):
            statement = statement.values(is_admin=True, is_officer=False, is_chief=False)
        elif (promotion_schema.type == "officer"):
            statement = statement.values(is_officer=True, is_admin=False, is_chief=False)
        elif (promotion_schema.type == "chief"):
            statement = statement.values(is_chief=True, is_admin=False, is_officer=False)
        elif (promotion_schema.type == "base"):
            statement = statement.values(is_chief=False, is_admin=False, is_officer=False)
        if promotion_schema.role:
            statement = statement.values(role = promotion_schema.role)
        if promotion_schema.status:
            if promotion_schema.status == "ok":
                statement = statement.values(is_reliable=True, is_blocked=False)
            elif promotion_schema.status == "unreliable":
                statement = statement.values(is_reliable=False, is_blocked=False)
            elif promotion_schema.status == "blocked":
                statement = statement.values(is_blocked=True, is_reliable=False)
        if promotion_schema.notes is not None:
            statement = statement.values(notes = promotion_schema.notes)
        if promotion_schema.authorizer:
            auth_user = db_session.exec(
                select(User).where( # check if authorizer (an admin, or an officer) exists
                    User.email == promotion_schema.authorizer.lower()
                )).first()
            if auth_user:
                if ((auth_user.is_admin) or (auth_user.is_officer)):
                    statement = statement.values(authorized_by = promotion_schema.authorizer.lower(), authorized_at = now_tz_naive())
            else:
                return None, {"message": "Authorizer email not valid", "updated_count": 0}
        statement = statement.values(updated_by = current_user.email, updated_at = now_tz_naive())
        if promotion_schema.type:
            statement = statement.returning(User.id, User.is_chief) # type: ignore
            result = db_session.exec(statement)
            critical_updated_rows = result.all() 
            updated_count = len(critical_updated_rows)       
        else:
            result = db_session.exec(statement)
            critical_updated_rows = None # we don't need them if type is not changed
            updated_count = result.rowcount
        return critical_updated_rows, {"message": "Operation completed", "updated_count": updated_count}
    if current_user.is_admin and promotion_schema.type:
        # we use a redis lock to avoid concurrent updates 
        # to user roles, that could cause inconsistencies 
        # in the chief locations list in redis
        async with redis_client.lock( 
            REDIS_MUTEX_CHIEF_UPDATE_KEY,
            timeout=60, # lock timeout (max time to hold the lock)
            sleep=5, # sleep time between lock acquisition attempts
            blocking_timeout=60 # max time to wait for the lock
            ):
            try: 
                crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
                if crit_upd_rows:
                    async with redis_client.pipeline(transaction=False) as pipe:
                        for user_id, chief_value in crit_upd_rows:
                            if chief_value == False:
                                user_id_str = str(user_id)
                                chief_key = get_redis_chief_locations_key(user_id_str)
                                pipe.zrem(chief_key, user_id_str)
                        await pipe.execute()
                await run_in_threadpool(db_session.commit)
            except Exception as e:
                print(f"Error: {e}") # todo: proper logging
                await run_in_threadpool(db_session.rollback)
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error updating user roles"
                )
        return msg_obj
    else:
        try:
            crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
            await run_in_threadpool(db_session.commit)
        except Exception as e:
            print(f"Error: {e}") # todo: proper logging
            await run_in_threadpool(db_session.rollback)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating user roles"
            )
        return msg_obj

@router.post("/api/users/promote-by-emails") # promote/demote users in bulk (by a list of emails)
async def promote_users_by_emails(
            emails: list[str],
            update_fields: PromotionSchema,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session),
            redis_client = Depends(get_redis_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if (update_fields.type):
        if not current_user.is_admin: # officers cannot change users type
            raise forbidden_exception()
    def db_update_logic(): 
        if len(emails) == 0:
            return None, {"message": "No emails provided", "updated_count": 0}
        if (current_user.is_admin):
            statement = update(User)
        else: # officers can update only users authorized by them
            statement = update(User).where(User.authorized_by == current_user.email) # type: ignore
        statement = statement.where(User.email == any_(emails)) # type:ignore
        # update fields according to promotion schema
        if (update_fields.type == "admin"):
            statement = statement.values(is_admin=True, is_officer=False, is_chief=False)
        elif (update_fields.type == "officer"):
            statement = statement.values(is_officer=True, is_admin=False, is_chief=False)
        elif (update_fields.type == "chief"):
            statement = statement.values(is_chief=True, is_admin=False, is_officer=False)
        elif (update_fields.type == "base"):
            statement = statement.values(is_chief=False, is_admin=False, is_officer=False)
        if update_fields.role:
            statement = statement.values(role = update_fields.role)
        if update_fields.status:
            if update_fields.status == "ok":
                statement = statement.values(is_reliable=True, is_blocked=False)
            elif update_fields.status == "unreliable":
                statement = statement.values(is_reliable=False, is_blocked=False)
            elif update_fields.status == "blocked":
                statement = statement.values(is_blocked=True, is_reliable=False)
        if update_fields.notes is not None:
            statement = statement.values(notes = update_fields.notes)
        if update_fields.authorizer:
            auth_user = db_session.exec(
                select(User).where( # check if authorizer (an admin, or an officer) exists
                    User.email == update_fields.authorizer.lower()
                )).first()
            if auth_user:
                if ((auth_user.is_admin) or (auth_user.is_officer)):
                    statement = statement.values(authorized_by = update_fields.authorizer.lower(), authorized_at = now_tz_naive())
            else:
                return None, {"message": "Authorizer email not valid", "updated_count": 0}
        statement = statement.values(updated_by = current_user.email, updated_at = now_tz_naive())
        if update_fields.type:
            statement = statement.returning(User.id, User.is_chief) # type: ignore
            result = db_session.exec(statement)
            critical_updated_rows = result.all() 
            updated_count = len(critical_updated_rows)       
        else:
            result = db_session.exec(statement)
            critical_updated_rows = None # we don't need them if type is not changed
            updated_count = result.rowcount
        return critical_updated_rows, {"message": "Operation completed", "updated_count": updated_count}
    if current_user.is_admin and update_fields.type:
        # we use a redis lock to avoid concurrent updates 
        # to user roles, that could cause inconsistencies 
        # in the chief locations list in redis
        async with redis_client.lock( 
            REDIS_MUTEX_CHIEF_UPDATE_KEY,
            timeout=60, # lock timeout (max time to hold the lock)
            sleep=5, # sleep time between lock acquisition attempts
            blocking_timeout=60 # max time to wait for the lock
            ):
            try: 
                crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
                if crit_upd_rows:
                    async with redis_client.pipeline(transaction=False) as pipe:
                        for user_id, chief_value in crit_upd_rows:
                            if chief_value == False:
                                user_id_str = str(user_id)
                                chief_key = get_redis_chief_locations_key(user_id_str)
                                pipe.zrem(chief_key, user_id_str)
                        await pipe.execute()
                await run_in_threadpool(db_session.commit)
            except Exception as e:
                print(f"Error: {e}") # todo: proper logging
                await run_in_threadpool(db_session.rollback)
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error updating user roles"
                )
        return msg_obj
    else:
        try:
            crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
            await run_in_threadpool(db_session.commit)
        except Exception as e:
            print(f"Error: {e}") # todo: proper logging
            await run_in_threadpool(db_session.rollback)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating user roles"
            )
        return msg_obj