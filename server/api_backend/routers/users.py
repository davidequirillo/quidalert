# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import APIRouter, Depends
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, desc, select, update
from starlette import status as http_status
from starlette.exceptions import HTTPException
from models.general import (
    string_as_uuid,
    Alert, 
    EmailListDict,
    PromotionSchema, User, 
    UsersOutPaginated, UserOutWithAlerts,
    UserStatus, UserType, UserRole
)
from dependencies import get_db_session, get_current_user, get_redis_session
from core.exceptions import forbidden_exception, not_found_exception, invalid_request_exception
from core.dbmgr import (
    get_redis_chief_locations_key, 
    REDIS_MUTEX_CHIEF_UPDATE_KEY,
    get_redis_chief_demotions_key)
from core import api_events
from services.security import ensure_tz_aware, now_tz_naive

EMAIL_LIST_MAX_LENGTH_FOR_SEARCH = 10000

router = APIRouter(
    tags=["Users"]
)

@router.get("/api/users", response_model=UsersOutPaginated, status_code=http_status.HTTP_200_OK)
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
    if type and (type not in [UserType.admin.value, UserType.officer.value, UserType.chief.value]):
        raise invalid_request_exception(detail=f"Invalid search: '{type}' type not admitted")
    if role and (role not in [r.value for r in UserRole]):
        raise invalid_request_exception(detail=f"Invalid search: '{role}' role not admitted")
    if status and (status not in [UserStatus.unreliable.value, UserStatus.blocked.value]):
        raise invalid_request_exception(detail=f"Invalid search: '{status}' status not admitted")
    if firstname and not surname:
        raise invalid_request_exception(detail="Invalid search: firstname cannot be used without surname")
    if authorizer and (not current_user.is_admin):
        raise forbidden_exception(detail="Only admins can filter by authorizer")
    if limit not in [10, 100, 1000]:
        limit = 100
    next_cursor = None
    if email:
        users = db_session.exec(
            select(User).where(User.email == email.lower())).all()
        return { 'users': users, 'next_cursor': next_cursor }
    statement = select(User)
    if not current_user.is_admin: # officers can see (in bulk) only users they authorized
        statement = statement.where(User.authorized_by == current_user.email)
    if authorizer:
        statement = statement.where(User.authorized_by == authorizer.lower()) 
    if surname:
        if firstname:
            statement = statement.where(User.surname == surname, User.firstname == firstname)
        else:
            statement = statement.where(User.surname == surname)
    if type:
        if type == UserType.admin.value:
            statement = statement.where(User.is_admin == True) 
        elif type == UserType.officer.value:
            statement = statement.where(User.is_officer == True) 
        elif type == UserType.chief.value:
            statement = statement.where(User.is_chief == True)
    if role:
        statement = statement.where(User.role == role)
    if status:
        if status == UserStatus.unreliable.value:
            statement = statement.where(User.is_reliable == False) 
        elif status == UserStatus.blocked.value:
            statement = statement.where(User.is_blocked == True)
    if last_seen_id:
        try:
            last_seen_id_as_uuid = string_as_uuid(last_seen_id)
            statement = statement.where(User.id < last_seen_id_as_uuid) # type: ignore
        except ValueError:
            raise not_found_exception(detail="Last seen id not valid")
    statement = statement.order_by(desc(User.id)).limit(limit)
    users = db_session.exec(statement).all()
    if users:
        next_cursor = str(users[-1].id)
    return { 'users': users, 'next_cursor': next_cursor }

@router.post("/api/users/get-by-emails", response_model=UsersOutPaginated, status_code=http_status.HTTP_200_OK)
def get_users_by_emails(
            email_list: EmailListDict,
            last_seen_id: str | None = None,
            limit: int = 100,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if len(email_list.emails) > EMAIL_LIST_MAX_LENGTH_FOR_SEARCH:
        raise invalid_request_exception(detail=f"Email list too long. Maximum allowed length is {EMAIL_LIST_MAX_LENGTH_FOR_SEARCH}")
    if limit not in [10, 100, 1000]:
        limit = 100
    next_cursor = None
    emails = [email.lower() for email in email_list.emails]
    statement = select(User)
    statement = statement.where(User.email.in_(emails)) # type:ignore
    if (last_seen_id):
        try:
            last_seen_id_as_uuid = string_as_uuid(last_seen_id)
            statement = statement.where(User.id < last_seen_id_as_uuid)
        except ValueError:
            raise not_found_exception(detail="Last seen id not valid")
    statement = statement.order_by(desc(User.id)).limit(limit)
    users = db_session.exec(statement).all()
    if users:
        next_cursor = str(users[-1].id)
    return { 'users': users, 'next_cursor': next_cursor }
    
@router.get("/api/users/{user_id}", response_model=UserOutWithAlerts, status_code=http_status.HTTP_200_OK)
def get_user(user_id: str, 
            current_user: User = Depends(get_current_user),
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    try:
        user_id_as_uuid = string_as_uuid(user_id)
    except ValueError:
        raise not_found_exception(detail="User id not valid")
    user = db_session.exec(select(User).where(User.id == user_id_as_uuid)).first()
    if not user:
        raise not_found_exception(detail="User not found")
    recent_alerts = db_session.exec(
        select(Alert).where(Alert.user_id == user_id_as_uuid).order_by(desc(Alert.created_at)).limit(5)
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
    if type and (type not in [UserType.admin.value, UserType.officer.value, UserType.chief.value]):
        raise invalid_request_exception(detail=f"Invalid search: '{type}' type not admitted")
    if role and (role not in [r.value for r in UserRole]):
        raise invalid_request_exception(detail=f"Invalid search: '{role}' role not admitted")
    if status and (status not in [UserStatus.unreliable.value, UserStatus.blocked.value]):
        raise invalid_request_exception(detail=f"Invalid search: '{status}' status not admitted")
    if firstname and not surname:
        raise invalid_request_exception(detail="Invalid search: firstname cannot be used without surname")
    if authorizer and (not current_user.is_admin):
        raise forbidden_exception(detail="Only admins can filter by authorizer")
    if (promotion_schema.type) and (not current_user.is_admin): # officers cannot change users type
        raise forbidden_exception()
    if (not email) and (not surname) and (not type) and (not role) and (not status):
        raise invalid_request_exception(detail="At least one search filter keyword must be provided to promote/demote users")
    def db_update_logic():
        if email:
            statement = update(User).where(User.email == email.lower()) # type:ignore
            if (not current_user.is_admin): # officers can update only users authorized by them
                statement = statement.where(User.authorized_by == current_user.email) # type: ignore
        else:
            if (current_user.is_admin):
                statement = update(User)
            else: # officers can update only users authorized by them
                statement = update(User).where(User.authorized_by == current_user.email) # type: ignore
            if authorizer:
                statement = statement.where(User.authorized_by == authorizer.lower()) # type: ignore
            if surname:
                if firstname:
                    statement = statement.where(User.surname == surname, User.firstname == firstname) # type: ignore
                else:
                    statement = statement.where(User.surname == surname) # type: ignore
            if type:
                if type == UserType.admin.value:
                    statement = statement.where(User.is_admin == True) # type: ignore 
                elif type == UserType.officer.value:
                    statement = statement.where(User.is_officer == True) # type: ignore
                elif type == UserType.chief.value:
                    statement = statement.where(User.is_chief == True) # type: ignore
            if role:
                statement = statement.where(User.role == role) # type: ignore
            if status: 
                if status == UserStatus.unreliable.value:
                    statement = statement.where(User.is_reliable == False) # type: ignore
                elif status == UserStatus.blocked.value:
                    statement = statement.where(User.is_blocked == True) # type: ignore
        # Update fields according to promotion schema
        if (promotion_schema.type == UserType.admin.value):
            statement = statement.values(is_admin=True, is_officer=False, is_chief=False)
        elif (promotion_schema.type == UserType.officer.value):
            statement = statement.values(is_officer=True, is_admin=False, is_chief=False)
        elif (promotion_schema.type == UserType.chief.value):
            statement = statement.values(is_chief=True, is_admin=False, is_officer=False)
        elif (promotion_schema.type == UserType.base.value):
            statement = statement.values(is_chief=False, is_admin=False, is_officer=False)
        if promotion_schema.role:
            # if promotion_schema.role is not in UserRole list, then we want to update the user to "base role", "citizen", so we set role to None
            if promotion_schema.role not in [t.value for t in UserRole]:
                statement = statement.values(role=None)
            else:
                statement = statement.values(role=promotion_schema.role)
        if promotion_schema.status:
            if promotion_schema.status == UserStatus.unreliable.value:
                statement = statement.values(is_reliable=False, is_blocked=False)
            elif promotion_schema.status == UserStatus.blocked.value:
                statement = statement.values(is_blocked=True, is_reliable=False)
            elif promotion_schema.status == UserStatus.ok.value:
                statement = statement.values(is_reliable=True, is_blocked=False)
        if promotion_schema.notes:
            statement = statement.values(notes = promotion_schema.notes)
        if promotion_schema.authorizer:
            auth_user = db_session.exec(
                select(User).where( # check if authorizer (an admin, or an officer) exists
                    User.email == promotion_schema.authorizer.lower()
                )).first()
            if auth_user and ((auth_user.is_admin) or (auth_user.is_officer)):
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
                            user_id_str = str(user_id)
                            chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
                            if chief_value == False:
                                chief_locations_key = get_redis_chief_locations_key(user_id_str)
                                chief_demoted_at = int(ensure_tz_aware(now_tz_naive()).timestamp())
                                pipe.zadd(chief_demotions_key, {user_id_str: chief_demoted_at})
                                pipe.zrem(chief_locations_key, user_id_str)
                            else:
                                pipe.zrem(chief_demotions_key, user_id_str)
                        await pipe.execute()
                await run_in_threadpool(db_session.commit)
            except Exception as e:
                api_events.log_promote_users_error(user_id=str(current_user.id), detail=f"{e}")
                await run_in_threadpool(db_session.rollback)
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error updating users (type) in bulk"
                )
        return msg_obj
    else:
        try:
            crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
            await run_in_threadpool(db_session.commit)
        except Exception as e:
            api_events.log_promote_users_error(user_id=str(current_user.id), detail=f"{e}")
            await run_in_threadpool(db_session.rollback)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating users in bulk"
            )
        return msg_obj

@router.post("/api/users/promote-by-emails") # promote/demote users in bulk (by a list of emails)
async def promote_users_by_emails(
            email_list: EmailListDict,
            update_fields: PromotionSchema,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session),
            redis_client = Depends(get_redis_session)):
    if (not current_user.is_admin) and (not current_user.is_officer):
        raise forbidden_exception()
    if len(email_list.emails) > EMAIL_LIST_MAX_LENGTH_FOR_SEARCH:
        raise invalid_request_exception(detail=f"Email list too long. Maximum allowed length is {EMAIL_LIST_MAX_LENGTH_FOR_SEARCH}")
    if (update_fields.type) and (not current_user.is_admin): # officers cannot change users type
        raise forbidden_exception()
    emails = [email.lower() for email in email_list.emails]
    def db_update_logic(): 
        if len(emails) == 0:
            return None, {"message": "No emails provided", "updated_count": 0}
        statement = update(User).where(User.email.in_(emails)) # type:ignore
        if (not current_user.is_admin): # officers can update only users authorized by them
            statement = statement.where(User.authorized_by == current_user.email) # type: ignore
        # update fields according to promotion schema
        if (update_fields.type == UserType.admin.value):
            statement = statement.values(is_admin=True, is_officer=False, is_chief=False)
        elif (update_fields.type == UserType.officer.value):
            statement = statement.values(is_officer=True, is_admin=False, is_chief=False)
        elif (update_fields.type == UserType.chief.value):
            statement = statement.values(is_chief=True, is_admin=False, is_officer=False)
        elif (update_fields.type == UserType.base.value):
            statement = statement.values(is_chief=False, is_admin=False, is_officer=False)
        if update_fields.role:
            # if update_fields.role is not in UserRole list, then we want to update the user to "base role", "citizen", so we set role to None
            if update_fields.role not in [t.value for t in UserRole]:
                statement = statement.values(role=None)
            else:
                statement = statement.values(role=update_fields.role)
        if update_fields.status:
            if update_fields.status == UserStatus.unreliable.value:
                statement = statement.values(is_reliable=False, is_blocked=False)
            elif update_fields.status == UserStatus.blocked.value:
                statement = statement.values(is_blocked=True, is_reliable=False)
            elif update_fields.status == UserStatus.ok.value:
                statement = statement.values(is_reliable=True, is_blocked=False)
        if update_fields.notes:
            statement = statement.values(notes = update_fields.notes)
        if update_fields.authorizer:
            auth_user = db_session.exec(
                select(User).where( # check if authorizer (an admin, or an officer) exists
                    User.email == update_fields.authorizer.lower()
                )).first()
            if auth_user and ((auth_user.is_admin) or (auth_user.is_officer)):
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
                            user_id_str = str(user_id)
                            chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
                            if chief_value == False:
                                chief_locations_key = get_redis_chief_locations_key(user_id_str)
                                chief_demoted_at = int(ensure_tz_aware(now_tz_naive()).timestamp())
                                pipe.zadd(chief_demotions_key, {user_id_str: chief_demoted_at})
                                pipe.zrem(chief_locations_key, user_id_str)
                            else:
                                pipe.zrem(chief_demotions_key, user_id_str)
                        await pipe.execute()
                await run_in_threadpool(db_session.commit)
            except Exception as e:
                api_events.log_promote_users_by_emails_error(user_id=str(current_user.id), detail=f"{e}")
                await run_in_threadpool(db_session.rollback)
                raise HTTPException(
                    status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                    detail="Error updating users type in bulk by emails"
                )
        return msg_obj
    else:
        try:
            crit_upd_rows, msg_obj = await run_in_threadpool(db_update_logic)
            await run_in_threadpool(db_session.commit)
        except Exception as e:
            api_events.log_promote_users_by_emails_error(user_id=str(current_user.id), detail=f"{e}")
            await run_in_threadpool(db_session.rollback)
            raise HTTPException(
                status_code=http_status.HTTP_500_INTERNAL_SERVER_ERROR,
                detail="Error updating users in bulk by emails"
            )
        return msg_obj
