# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import time
from enum import Enum
import asyncio
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select, insert
from fakeredis.aioredis import FakeRedis
from email.message import EmailMessage
from models.general import (
    string_as_uuid,
    RefreshToken, User, 
    Alert, AlertType, AlertedUser,
    Message)
from services.localization import alert_langmap, localize_new_alert_mail
from services.network import (
    get_user_fcm_token,
    notify_single_client,
    notify_many_clients,
    send_mail_message
)
from core.btask_events import (
    log_alert_search_closest_chiefs_done,
    log_alert_error_searching_closest_chiefs,
    log_alert_error_checking_closest_chiefs,
    log_alert_orphan_ids_found_in_checking_closest_chiefs,
    log_alert_error_saving_closest_chief,
    log_alert_no_chief_manager_to_notify,
    log_alert_error_notifying_chief_manager,
    log_alert_notify_chief_manager,
    log_alert_search_nearby_users_done,
    log_alert_error_searching_nearby_users,
    log_alert_error_checking_nearby_users,
    log_alert_orphan_ids_found_in_checking_nearby_users,
    log_alert_error_saving_nearby_users,
    log_alert_no_nearby_users_to_notify,
    log_alert_error_notifying_nearby_users,
    log_alert_notify_nearby_users,
    log_alert_no_sender_to_notify,
    log_alert_error_notifying_sender,
    log_alert_notify_sender,
    log_alert_success_sending_mail_to_chief_manager,
    log_alert_error_sending_mail_to_chief_manager,
    log_alert_notify_about_closure,
    log_alert_error_notifying_about_closure,
    log_alert_error_finalizing_expansion,
    log_alert_notify_on_new_message,
    log_alert_error_notifying_on_new_message
)
from core.settings import settings
from core.dbmgr import (
    cluster, redis, RedisHandleTypeError,
    get_all_redis_chief_locations_keys,
    get_all_redis_user_locations_keys,
    get_all_redis_spec_locations_keys_for_a_role
    )

class AlertOperation(str, Enum):
    create = "create"
    expand = "expand"
    message = "message" # not used
    close = "close" # not used

alert_notification_templates = alert_langmap

# We search for chiefs within a very large radius, 
# to be sure to find at least one closest chief (because a chief must be alerted, even if he is outside the alert radius)
GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM = 10000

## CREATE ALERT BTASK: this is the main function that will be executed as a background task when a new alert is created.
async def task_alert_search_and_notify(
            alert: Alert, current_user: User, request_info: dict,
            db_engine, redis_handle):    
    if (alert.id is None) or (alert.is_closed):
        return
    nearby_users_can_be_notified = False
    chief_can_be_notified = False
    # The alert sender is the user who created the alert 
    # (the "current_user", the one who called the API endpoint to create the alert)
    sender_can_be_notified = False
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(alert, request_info, redis_handle)
    with Session(db_engine) as db_session:
        sender_fcm_token = await run_in_threadpool(
            get_sender_fcm_token, 
            alert, current_user.id, request_info, db_session)
        # For local alerts, we keep the first closest chief as alert manager and save him to database (table alerted_users)
        # For non-local alerts, the user who created the alert is the alert manager, so we don't need to search for a chief or save him to database as alert manager
        if (alert.type == AlertType.local.value):
            chief, chief_fcm_token, chief_email = await run_in_threadpool(
                save_first_chief_in_db, 
                alert, closest_chiefs, request_info, db_session)
        else:
            chief, chief_fcm_token, chief_email = {
                "user_id": current_user.id,
                "distance_km": 0.0,
                "location": {
                    "latitude": alert.latitude,
                    "longitude": alert.longitude
                }
            }, sender_fcm_token, current_user.email
        # To avoid duplicates or errors, we check if nearby users contains the chief (alert manager), and we delete him from nearby users list
        if chief:
            nearby_users = [u for u in nearby_users if u["user_id"] != chief["user_id"]]
        # We save nearby users in database as "alerted users" and we get their fcm tokens
        nearby_users_to_fcm_tokens = await run_in_threadpool(
            save_nearby_users_in_db, 
            alert, nearby_users, request_info, db_session)
        if sender_fcm_token:
            sender_can_be_notified = True
        else:
            log_alert_no_sender_to_notify(str(alert.id), AlertOperation.create.value, request_info)
        if (alert.type == AlertType.local.value): 
            if chief and chief_email and chief_fcm_token:
                chief_can_be_notified = True
            else:
                log_alert_no_chief_manager_to_notify(str(alert.id), AlertOperation.create.value, request_info)
        if nearby_users_to_fcm_tokens:
            nearby_users_can_be_notified = True
        else:
            log_alert_no_nearby_users_to_notify(str(alert.id), None, AlertOperation.create.value, request_info)
        if settings.app_mode == "development":
            await asyncio.sleep(10) # line executed only in development-mode, to simulate a long processing time, for manual testing purposes
        # Now we set the alert as not pending anymore, because we have already searched for chiefs and nearby users, and we have saved them in database
        # Note: we don't pass the "alert" object to the function, because it is a copy of the original alert object coming from api endpoint, 
        # so, we need to retrieve the original alert object from database, to update its is_pending field (see function "set_alert_as_not_pending_anymore")
        await run_in_threadpool(
            set_alert_as_not_pending_anymore, 
            alert.id, request_info, db_session)
        if (chief_can_be_notified) or (nearby_users_can_be_notified):
            # We prepare the message to be sent to chief and nearby users
            # Note: as language we use the caller's (current_user) language for simplicity, not the language of each client receiving the notification. 
            description = alert.description if (len(alert.description) <= 100) else (alert.description[:100] + "...")
            message_prefix = alert_notification_templates[current_user.language]["new_alert_prefix"].format(
                name=current_user.firstname + " " + current_user.surname)
            message = message_prefix + " " + description
            if chief and chief_can_be_notified:
                try:
                    chief_id = chief["user_id"]
                    await run_in_threadpool(
                        notify_chief_manager, 
                        chief_id, chief_fcm_token, 
                        language=current_user.language, alert=alert, content=message, 
                        request_info=request_info, db_session=db_session)
                    log_alert_notify_chief_manager(str(alert.id), AlertOperation.create.value, request_info, detail=f"Closest chief {chief_id} notified successfully")
                except Exception as e:
                    chief_can_be_notified = False
                    log_alert_error_notifying_chief_manager(str(alert.id), AlertOperation.create.value, request_info, detail=str(e))
                try:
                    await run_in_threadpool(
                        send_mail_to_chief_manager,
                        chief_id, chief_email, 
                        language=current_user.language, alert=alert, sender=current_user, 
                        request_info=request_info)
                except Exception as e:
                    pass # exception already logged inside send_mail_to_chief_manager function, so we don't need to log it again here
            if nearby_users_can_be_notified:
                try:
                    user_ids = list(nearby_users_to_fcm_tokens.keys())
                    fcm_tokens = list(nearby_users_to_fcm_tokens.values())
                    notification_count = await run_in_threadpool(
                        notify_nearby_users,
                        user_ids, fcm_tokens,
                        language=current_user.language, alert=alert, content=message, 
                        request_info=request_info, db_session=db_session)
                    if notification_count <= 0:
                        nearby_users_can_be_notified = False
                    log_alert_notify_nearby_users(str(alert.id), None, AlertOperation.create.value, request_info, detail=f"Nearby users notified successfully, {notification_count} out of {len(user_ids)} users notified on alert creation")
                except Exception as e:
                    nearby_users_can_be_notified = False
                    log_alert_error_notifying_nearby_users(str(alert.id), None, AlertOperation.create.value, request_info, detail=str(e))
        if sender_can_be_notified:
            msg_for_sender = ""
            if alert.type == AlertType.local.value:
                if not chief_can_be_notified:
                    if nearby_users_can_be_notified:
                        msg_for_sender = alert_notification_templates[current_user.language]["no_chief_available_but_nearby_users"]
                    else:
                        msg_for_sender = alert_notification_templates[current_user.language]["no_chief_available_no_nearby_users"]
                else:
                    if nearby_users_can_be_notified:
                        msg_for_sender = alert_notification_templates[current_user.language]["chief_and_nearby_users_notified"]
                    else:
                        msg_for_sender = alert_notification_templates[current_user.language]["only_chief_notified"]
            else:
                if nearby_users_can_be_notified:
                    msg_for_sender = alert_notification_templates[current_user.language]["nearby_users_notified"]
                else:
                    msg_for_sender = alert_notification_templates[current_user.language]["no_nearby_users_available"]
            try:
                await run_in_threadpool(
                    notify_sender, 
                    str(current_user.id), sender_fcm_token, 
                    language=current_user.language, alert=alert, content=msg_for_sender, 
                    request_info=request_info, db_session=db_session) # notify the user who created the alert
                log_alert_notify_sender(str(alert.id), AlertOperation.create.value, request_info, detail=f"Sender {current_user.id} notified successfully")
            except Exception as e:
                log_alert_error_notifying_sender(str(alert.id), AlertOperation.create.value, request_info, detail=str(e))
    return

async def get_closest_chiefs_and_nearby_users(alert, request_info, redis_handle):
    chiefs, users = [], []
    if isinstance(redis_handle, cluster.RedisCluster):
        chiefs = await get_closest_chiefs(alert, request_info, redis_handle)
        users = await get_nearby_users(alert, request_info, redis_handle)
        return chiefs, users
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            chiefs = await get_closest_chiefs(alert, request_info, redis_session)
            users = await get_nearby_users(alert, request_info, redis_session)
        return chiefs, users
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        chiefs = await get_closest_chiefs(alert, request_info, redis_handle)
        users = await get_nearby_users(alert, request_info, redis_handle)
        return chiefs, users
    else:
        raise RedisHandleTypeError(redis_handle)
        
async def get_closest_chiefs(alert, request_info, redis_client): # Redis client can be a redis handle (in cluster mode) or a redis session from pool (in single mode)
    closest_chiefs = []
    if (alert.type != AlertType.local.value):
        # For non-local alerts, we don't need to search for chiefs, because only chiefs can create non-local alerts
        # If a chief create a non-local alert, he becomes the alert managers,
        # so, we don't need to search for other chiefs to notify, because the chief who created the alert is the one who will manage it
        return []
    # We obtain all shards keys for chiefs locations
    shard_keys = get_all_redis_chief_locations_keys()
    try:    
        # 1. Preparation: we create the tasks (one for each shard) to search for the closest chief in each shard in parallel 
        tasks = [
            redis_client.geosearch(
                name=key,
                longitude=alert.longitude,
                latitude=alert.latitude,
                radius=GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM, # very large radius, to be sure to find a closest chief
                unit="km",
                sort="asc",
                count=100, # we search for the closest 100 chiefs
                withdist=True,
                withcoord=True
            ) for key in shard_keys
        ]
        # 2. Parallel execution
        sharded_results = await asyncio.gather(*tasks)
        # 3. Gather
        all_candidates = []
        for results in sharded_results:
            if results:
                all_candidates.extend(results)
        if not all_candidates:
            raise Exception(f"No chiefs found within {GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM} km radius")
        # 4. Sorting
        all_candidates.sort(key=lambda x: x[1]) # x[1] is the distance
        # 5. Filtering: we keep only the closest 100 chiefs (in case there are more than 100 chiefs in total across all shards)
        if len(all_candidates) > 100:
            all_candidates = all_candidates[:100]
        for user_id, distance, coords in all_candidates:
            if user_id != str(alert.user_id): # we exclude the user who created the alert (if he is a chief) from the list of closest chiefs, to avoid duplicates or errors
                closest_chiefs.append({
                    "user_id": user_id,
                    "distance_km": round(distance, 3),
                    "location": {
                        "latitude": coords[1], # Redis returns (lon, lat)
                        "longitude": coords[0]
                    }
                })
        log_alert_search_closest_chiefs_done(str(alert.id), request_info, detail=f"{len(closest_chiefs)} closest chiefs found and sorted successfully")
        return closest_chiefs
    except Exception as e:
        log_alert_error_searching_closest_chiefs(str(alert.id), request_info, detail=str(e))
        return []
        
async def get_nearby_users(
        alert, request_info, redis_client, 
        radius=None, role=None, is_expanded=False, 
        search_num=1000): # Redis client can be a redis handle (in cluster mode) or a redis session from pool (in single mode)
    """
    Searches for users near a specific alert across all shards in parallel.
    This is the core of the universal scaling architecture.
    This function is used both for alert creation and alert expansion, with different parameters.
    If radius is None, it uses the radius of alert object (alert.radius), otherwise it uses the specified radius (useful for alert expansion). 
    If role is specified, it searches for users with that role (specialists, examples: "medics", "firefighters", "policemen", etc.), otherwise it searches for all users (role=None).
    If is_expanded is True, it indicates that the function is being called during alert expansion.
    """
    operation_name = AlertOperation.expand.value if is_expanded else AlertOperation.create.value
    nearby_users = []
    # Note: in alert creation, the alert sender is equal to the caller (current_user), 
    # but in alert expansion, the alert sender can be different from the caller (current_user), 
    # so we need to exclude both from the list of nearby users, to avoid duplicates or errors
    alert_sender_id: str = str(alert.user_id) # the user who created the alert (the sender) is excluded from the list of nearby users, to avoid duplicates or errors
    caller_id: str = request_info["user_id"] # the user who expands the alert (the caller, current_user) is excluded from the list of nearby users, to avoid duplicates or errors
    # We obtain all shards keys for user locations
    if role:
        shard_keys = get_all_redis_spec_locations_keys_for_a_role(role)
    else:
        shard_keys = get_all_redis_user_locations_keys()
    try:
        # 1. Preparation: we create the tasks (one for each shard)
        tasks = [
            redis_client.geosearch(
                name=key,
                longitude=alert.longitude,
                latitude=alert.latitude,
                radius=radius if radius is not None else alert.radius,
                unit="km",
                sort="asc",
                count=search_num, 
                withdist=True,
                withcoord=True
            ) for key in shard_keys
        ] 
        # 2. Parallel execution
        sharded_results = await asyncio.gather(*tasks)
        # 3. Unification of the results for each shard
        all_matches = []
        for results in sharded_results:
            if results:
                all_matches.extend(results)
        # 4. Sorting results, based on distance (x[1] contains the distance)
        all_matches.sort(key=lambda x: x[1])
        # 5. Filtering: we keep only the first "search_num" entries
        if len(all_matches) > search_num:
            all_matches = all_matches[:search_num]
        for user_id, distance, coords in all_matches:
            if (user_id != alert_sender_id) and (user_id != caller_id):
                nearby_users.append({
                    "user_id": user_id,
                    "distance_km": round(distance, 3),
                    "location": {
                        "latitude": coords[1],  # Redis returns (lon, lat)
                        "longitude": coords[0]
                    }
                })
        log_alert_search_nearby_users_done(str(alert.id), role, operation_name, request_info, detail=f"{len(nearby_users)} nearby users found and sorted successfully")
        return nearby_users
    except Exception as e:
        log_alert_error_searching_nearby_users(str(alert.id), role, operation_name, request_info, detail=str(e))
        return []

def save_first_chief_in_db(alert, closest_chiefs, request_info, db_session):
    if not closest_chiefs:
        return None, None, None
    chief = None
    email = None
    fcm_token = None
    chief_ids_as_uuid = []
    for c in closest_chiefs:
        try:
            uuid = string_as_uuid(c["user_id"])
            chief_ids_as_uuid.append(uuid)
        except Exception as e:
            log_alert_error_checking_closest_chiefs(str(alert.id), request_info, detail=f"Error converting chief user_id string to UUID: {e}")
            continue
    statement = (select(User.id, User.email, RefreshToken.fcm_token)
    .join(RefreshToken, RefreshToken.user_id == User.id) # type: ignore
    .where(User.id.in_(chief_ids_as_uuid)) # type: ignore
    .where(User.is_chief == True, RefreshToken.fcm_token != None))
    try:
        db_results = db_session.exec(statement).all()
        # user_id -> (email, fcm_token)
        chiefs_to_tokens = {str(row[0]): (row[1], row[2]) for row in db_results}
        # Identification of orphans 
        # Who is in Redis, but not in Postgres? (rare event)
        existing_ids_in_db = set(chiefs_to_tokens.keys())
        orphans = [uid for uid in chief_ids_as_uuid if str(uid) not in existing_ids_in_db]
        if orphans:
            err_detail = f"Orphan chiefs_ids found (in Redis but not in Postgres, causes: null fcm token, or they have been modified, or deleted): {orphans}"
            log_alert_orphan_ids_found_in_checking_closest_chiefs(str(alert.id), request_info, detail=err_detail)
        for c in closest_chiefs:
            if c["user_id"] in existing_ids_in_db:
                chief = c
                email, fcm_token = chiefs_to_tokens.get(c["user_id"], (None, None))
                break
    except Exception as e:
        log_alert_error_checking_closest_chiefs(str(alert.id), request_info, detail=str(e))
        chief = None
        email = None
        fcm_token = None
    try:
        if chief and fcm_token:
            chief_uuid = string_as_uuid(chief["user_id"])
            stmt = insert(AlertedUser).values(
                alert_id=alert.id,
                user_id=chief_uuid,
                distance=0.0,
                is_manager=True,
                vote=0,
                closing_vote=0
            )
            db_session.exec(stmt)
            db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_alert_error_saving_closest_chief(str(alert.id), request_info, detail=str(e))
        chief = None
        email = None
        fcm_token = None
    return chief, fcm_token, email

def set_alert_as_not_pending_anymore(alert_id, request_info, db_session):
    try: 
        statement = select(Alert).where(Alert.id == alert_id) 
        alert = db_session.exec(statement).first()
        if alert:
            alert.is_pending = False
            alert.spread_count += 1
            db_session.add(alert)
            db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_alert_error_saving_nearby_users(str(alert_id), None, AlertOperation.create.value, request_info, detail=f"Error setting alert pending status to False: {e}")
    return

def save_nearby_users_in_db(alert, users, request_info, db_session, 
                role=None, is_expanded: bool = False):
    # We save nearby users in database as "alerted users" and we get their fcm tokens
    # This function is used both for alert creation and alert expansion, with different parameters.
    # If role is specified, it indicates we have search for users with that role (specialists, examples: "medics", "firefighters", "policemen", etc.), 
    # otherwise it indicates we have searched for all users (role=None).
    # If is_expanded is True, it indicates that the function is being called during alert expansion.
    # If is_expanded is True, obviously we add in the database (as alerted users) only the users who have not been alerted yet (to avoid duplicates or errors), 
    # so we check the database for already alerted users and we exclude them from the list of users to be added in the database.
    operation_name = AlertOperation.expand.value if is_expanded else AlertOperation.create.value
    if not users:
        return {}
    alerted_users_set = None
    if is_expanded:
        alerted_users_stmt = select(AlertedUser.user_id).where(AlertedUser.alert_id == alert.id)
        alerted_users_ids = db_session.exec(alerted_users_stmt).all()
        alerted_users_set = set(str(id) for id in alerted_users_ids)
    ids_as_uuid = []
    users_to_distances = {}
    users_to_tokens = {}
    for u in users:
        try:
            uuid = string_as_uuid(u["user_id"])
            if alerted_users_set and (str(uuid) in alerted_users_set):
                continue
            users_to_distances[str(uuid)] = u["distance_km"]
            ids_as_uuid.append(uuid)
        except Exception as e:
            log_alert_error_checking_nearby_users(str(alert.id), role, operation_name, request_info, detail=f"Error converting user_id string to UUID: {e}")
            continue
    existing_ids_in_db = set()
    try:
        statement = (select(User.id, RefreshToken.fcm_token)
                .join(RefreshToken, RefreshToken.user_id == User.id) # type: ignore
                .where(User.id.in_(ids_as_uuid)) # type: ignore
                .where(RefreshToken.fcm_token != None))
        db_results = db_session.exec(statement).all()
        users_to_tokens = {str(row[0]): row[1] for row in db_results}
        # Identification of orphans 
        # Who is in Redis, but not in Postgres? (rare event)
        existing_ids_in_db = set(users_to_tokens.keys())
        orphans = [uid for uid in ids_as_uuid if str(uid) not in existing_ids_in_db]
        if orphans:
            err_detail = f"Orphan user_ids found (in Redis but not in Postgres, causes: null fcm token, or they have been modified, or deleted): {orphans}"
            log_alert_orphan_ids_found_in_checking_nearby_users(str(alert.id), role, operation_name, request_info, detail=err_detail)
    except Exception as e:
        log_alert_error_checking_nearby_users(str(alert.id), role, operation_name, request_info, detail=str(e))
        users_to_tokens = {}
    try:
        if users_to_tokens and existing_ids_in_db:
            valid_data_for_db_bulk_insert = []
            for u_id in existing_ids_in_db:
                try:
                    user_uuid = string_as_uuid(u_id)
                    user_distance = users_to_distances.get(u_id, 0.0)
                except Exception as e:
                    log_alert_error_saving_nearby_users(str(alert.id), role, operation_name, request_info, detail=f"Error converting user_id string to UUID: {e}")
                    continue
                valid_data_for_db_bulk_insert.append({
                    "alert_id": alert.id,
                    "user_id": user_uuid,
                    "distance": user_distance,
                    "is_manager": False,
                    "vote": 0,
                    "closing_vote": 0
                })
            if valid_data_for_db_bulk_insert:
                # Bulk insert nearby users into alerted_users table 
                stmt = insert(AlertedUser)
                db_session.exec(stmt, params=valid_data_for_db_bulk_insert)
                db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_alert_error_saving_nearby_users(str(alert.id), role, operation_name, request_info, detail=str(e))
        users_to_tokens = {}
    return users_to_tokens

def get_sender_fcm_token(alert, user_id, request_info, db_session, operation=AlertOperation.create.value):
    try:
        fcm_token = get_user_fcm_token(user_id, db_session)
        return fcm_token
    except Exception as e:
        log_alert_error_notifying_sender(str(alert.id), operation, request_info, detail=str(e))
        return None
    
def notify_nearby_users(
        user_ids, fcm_tokens,
        language: str, alert: Alert, content: str, 
        request_info, db_session):        
    action_label = alert_notification_templates[language]["new_alert_action_label"]
    msg_title = alert_notification_templates[language]["new_alert_title"]
    msg_body = content
    msg_data = {
        "origin": "new_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    success_count = notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)
    return success_count

def notify_chief_manager(user_id, fcm_token,
        language: str, alert: Alert, content: str, 
        request_info, db_session):
    action_label = alert_notification_templates[language]["new_alert_action_label"]
    msg_title = alert_notification_templates[language]["new_alert_title"]
    msg_body = content
    msg_data = {
        "origin": "new_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

def notify_sender(user_id, fcm_token,
        language: str, alert: Alert, content: str, 
        request_info, db_session):
    action_label = alert_notification_templates[language]["new_alert_action_label"]
    msg_title = alert_notification_templates[language]["new_alert_title"]
    msg_body = content
    msg_data = {
        "origin": "new_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

def send_mail_to_chief_manager(chief_id, chief_email, 
        language: str, alert: Alert, sender: User, 
        request_info: dict):
    msg = EmailMessage()
    msg["Subject"] = alert_langmap[language]["new_alert_mail_subject"]
    msg["From"] = settings.smtp_from
    msg["To"] = chief_email
    msg.set_content(localize_new_alert_mail(alert, sender, language))
    try:
        send_mail_message(msg)
        log_alert_success_sending_mail_to_chief_manager(str(alert.id), AlertOperation.create.value, request_info, detail=f"Email message sent successfully to chief {chief_id}")
    except Exception as e:
        log_alert_error_sending_mail_to_chief_manager(str(alert.id), AlertOperation.create.value, request_info, detail=f"Error sending email message to chief {chief_id}: {e}")

## CLOSE ALERT BTASK: this is the main function that will be executed as a background task when an alert is closed.
def task_alert_notify_about_closure(
            alert: Alert, closing_type: str, current_user: User, request_info: dict, db_engine):
    if (alert.id is None) or (not alert.is_closed):
        return
    users_to_notify_ids = []
    users_to_notify_fcm_tokens = []
    with Session(db_engine) as db_session:
        # The alert sender is the user who created the alert (the "alert.user_id"),
        # and he must be notified about the alert closure, if he is not the one who closed the alert (the current_user, the API caller)
        # The following predicate is true in local alerts.
        if alert.user_id != current_user.id:
            statement = (select(RefreshToken)
                    .where(RefreshToken.user_id == alert.user_id)
                    .where(RefreshToken.fcm_token != None))
            sender_rtoken = db_session.exec(statement).first()
            if sender_rtoken:
                users_to_notify_ids.append(str(sender_rtoken.user_id))
                users_to_notify_fcm_tokens.append(sender_rtoken.fcm_token)
        # For alerts, we notify all alerted users, except the alert manager, 
        # because if present, he is the one who closed the alert (the current_user, the API caller).
        statement = (select(AlertedUser.user_id, RefreshToken.fcm_token)
                .join(RefreshToken, RefreshToken.user_id == AlertedUser.user_id) # type: ignore
                .where(AlertedUser.alert_id == alert.id)
                .where(RefreshToken.fcm_token != None))
        db_results = db_session.exec(statement).all()
        for row in db_results:
            user_id, fcm_token = row
            if user_id != current_user.id:
                users_to_notify_ids.append(str(user_id))
                users_to_notify_fcm_tokens.append(fcm_token)
        if settings.app_mode == "development":
            time.sleep(10) # line executed only in development-mode, to simulate a long processing time, for manual testing purposes
        # We send notifications, using a multicast notification function. 
        # Note: as language we use the caller's (current_user) language for simplicity, not the language of each client receiving the notification.
        if users_to_notify_ids and users_to_notify_fcm_tokens:
            try:
                notification_count = notify_about_closure(
                        users_to_notify_ids, users_to_notify_fcm_tokens, 
                        language=current_user.language, alert=alert, closing_type=closing_type, 
                        request_info=request_info, db_session=db_session)
                log_alert_notify_about_closure(str(alert.id), request_info, detail=f"Alert closure successfully, {notification_count} out of {len(users_to_notify_ids)} users notified about closure")
            except Exception as e:
                log_alert_error_notifying_about_closure(str(alert.id), request_info, detail=str(e))

def notify_about_closure(user_ids, fcm_tokens, 
        language, alert, closing_type,  
        request_info, db_session):
    closing_type_label = alert_notification_templates[language].get(f"close_alert_{closing_type}_closure", "unknown")
    action_label = alert_notification_templates[language]["close_alert_action_label"]
    msg_title = alert_notification_templates[language]["close_alert_title"]
    msg_body = alert_notification_templates[language]["close_alert_text"].format(
                date=alert.created_at.strftime("%Y-%m-%d"),
                hour=alert.created_at.strftime("%H:%M"),
                closing_type=closing_type_label.lower()
            )
    msg_data = {
        "origin": "close_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id),
        "closing_type": closing_type
    }
    success_count = notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)
    return success_count

## EXPAND ALERT BTASK: This is the main function that will be executed as a background task when an alert is expanded.
async def task_alert_process_expansion(
        alert, current_user, radius, role,
        request_info, db_engine, redis_handle):
    if (alert.id is None) or (alert.is_closed):
        return
    # The chief manager is the caller (current_user) who is expanding the alert, 
    # the one who called the API endpoint to expand the alert.
    chief_fcm_token = None
    # The sender is the user who created the alert (the "alert.user_id"),
    # In non-local alerts (managed by chiefs), the sender is equal to the expanding caller (current_user),
    # but in local alerts, the alert sender can be different from the API expansion caller (current_user).
    sender_fcm_token = None
    # Get users (or specialists, if role is specified) who reside in the expansion area 
    # (not in the alert radius, but in the new radius defined by the chief manager who expands the alert)
    zone_users = await get_zone_users(alert, radius, role, request_info, redis_handle)
    with Session(db_engine) as db_session:
        chief_fcm_token = await run_in_threadpool(
                get_chief_manager_fcm_token, 
                alert, current_user.id, request_info, db_session, 
                operation=AlertOperation.expand.value)
        if alert.user_id != current_user.id:
            sender_fcm_token = await run_in_threadpool(
                get_sender_fcm_token, 
                alert, alert.user_id, request_info, db_session, 
                operation=AlertOperation.expand.value)
        # Zone_users_to_fcm_token contains only the new users saved in database as alerted users, 
        # not all the users found in the zone, because some of them may have been already alerted before 
        # (during alert creation or previous alert expansions)
        zone_users_to_fcm_tokens = await run_in_threadpool(
                    save_zone_users_in_db, 
                    alert, zone_users, role, request_info, db_session)
        zone_users_num = len(zone_users_to_fcm_tokens)
        if not chief_fcm_token:
            log_alert_no_chief_manager_to_notify(str(alert.id), AlertOperation.expand.value, request_info)
        if (not sender_fcm_token) and (alert.user_id != current_user.id):
            log_alert_no_sender_to_notify(str(alert.id), AlertOperation.expand.value, request_info)
        if (zone_users_num == 0):
            log_alert_no_nearby_users_to_notify(str(alert.id), role, AlertOperation.expand.value, request_info)
        if settings.app_mode == "development":
            await asyncio.sleep(10) # line executed only in development-mode, to simulate a long processing time, for manual testing purposes
        # Now we finalize alert expansion (setting it as not pending anymore, because we have searched for users in the zone, and we have saved them in database.
        # Note: we don't pass the "alert" object to the function, because it is a copy of the original alert object coming from api endpoint, 
        # so, we need to retrieve the original alert object from database, to update its is_pending field (see function "finalize_alert_expansion")
        await run_in_threadpool(
                finalize_alert_expansion,  
                alert.id, zone_users_num, request_info, db_session)
        if chief_fcm_token:
            try:
                await run_in_threadpool(
                    notify_chief_manager_about_expansion, 
                    str(current_user.id), chief_fcm_token, 
                    current_user.language, alert, radius, role, zone_users_num,
                    request_info, db_session)
                log_alert_notify_chief_manager(str(alert.id), AlertOperation.expand.value, request_info, detail=f"Chief manager {current_user.id} notified successfully")
            except Exception as e:
                log_alert_error_notifying_chief_manager(str(alert.id), AlertOperation.expand.value, request_info, detail=str(e))
        if sender_fcm_token and (alert.user_id != current_user.id):
            try:
                await run_in_threadpool(
                    notify_sender_about_expansion, 
                    str(alert.user_id), sender_fcm_token, 
                    current_user.language, alert, 
                    request_info, db_session)
                log_alert_notify_sender(str(alert.id), AlertOperation.expand.value, request_info, detail=f"Sender {alert.user_id} notified successfully")
            except Exception as e:
                log_alert_error_notifying_sender(str(alert.id), AlertOperation.expand.value, request_info, detail=str(e))
        if zone_users_to_fcm_tokens:
            try:
                user_ids = list(zone_users_to_fcm_tokens.keys())
                fcm_tokens = list(zone_users_to_fcm_tokens.values())
                notification_count = await run_in_threadpool(
                    notify_nearby_users_about_expansion,
                    user_ids, fcm_tokens,
                    current_user.language, alert, 
                    request_info, db_session)
                log_alert_notify_nearby_users(str(alert.id), role, AlertOperation.expand.value, request_info, detail=f"Nearby users notified successfully, {notification_count} out of {len(user_ids)} users notified on alert expansion")
            except Exception as e:
                log_alert_error_notifying_nearby_users(str(alert.id), role, AlertOperation.expand.value, request_info, detail=str(e))
    return

def get_chief_manager_fcm_token(alert, user_id, request_info, db_session, operation=AlertOperation.create.value):
    try:
        fcm_token = get_user_fcm_token(user_id, db_session)
        return fcm_token
    except Exception as e:
        log_alert_error_notifying_chief_manager(str(alert.id), operation, request_info, detail=str(e))
        return None

def finalize_alert_expansion(alert_id, users_num, request_info, db_session):
    try:
        statement = select(Alert).where(Alert.id == alert_id) 
        alert = db_session.exec(statement).first()
        if alert:
            alert.is_pending = False
            if users_num > 0:
                alert.spread_count += 1
                if alert.type == AlertType.empty.value:
                    alert.type = AlertType.managed.value
            db_session.add(alert)
            db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_alert_error_finalizing_expansion(str(alert_id), request_info, detail=str(e))

async def get_zone_users(alert, radius, role, request_info, redis_handle):
    # We search for users (or specialists) who are within a certain radius from the alert location, based on the role specified.
    # If no role is specified, we search for all nearby users.
    # We reuse "get_nearby_users" function, calling it with the correct parameters for expansion.
    nearby_users = []
    if isinstance(redis_handle, cluster.RedisCluster):
        nearby_users = await get_nearby_users(alert, request_info, redis_handle, 
                            radius=radius, role=role, is_expanded=True)
        return nearby_users
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            nearby_users = await get_nearby_users(alert, request_info, redis_session, 
                                radius=radius, role=role, is_expanded=True)
        return nearby_users
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        nearby_users = await get_nearby_users(alert, request_info, redis_handle, 
                            radius=radius, role=role, is_expanded=True)
        return nearby_users
    else:
        raise RedisHandleTypeError(redis_handle)

def save_zone_users_in_db(alert, users, role, request_info, db_session):
    # We save zone users in database as "alerted users" and we get their fcm tokens
    # The existing users in the database (already alerted users) are excluded from the list of users to be added in the database, to avoid duplicates or errors.
    # We reuse "save_nearby_users_in_db" function, calling it with the correct parameters for expansion.
    return save_nearby_users_in_db(alert, users, request_info, db_session, role=role, is_expanded=True)

def notify_chief_manager_about_expansion(user_id, fcm_token, 
            language: str, alert: Alert, radius: float, role: str, users_num: int,
            request_info, db_session):
    date_str = alert.created_at.strftime("%Y-%m-%d")
    hour_str = alert.created_at.strftime("%H:%M")
    action_label = alert_notification_templates[language]["expand_alert_action_label"]
    msg_title = alert_notification_templates[language]["expand_alert_title"]
    if role:
        msg_body = alert_notification_templates[language]["expand_alert_to_role_text"].format(
                date=date_str,
                hour=hour_str,
                radius=radius,
                role=role,
                users_num=users_num
            )
    else:
        msg_body = alert_notification_templates[language]["expand_alert_to_all_text"].format(
                date=date_str,
                hour=hour_str,
                radius=radius,
                users_num=users_num
            )
    msg_data = {
        "origin": "expand_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id),
        "radius": str(radius),
        "role": str(role),
        "users_num": str(users_num)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

def notify_sender_about_expansion(
        user_id, fcm_token, 
        language: str, alert: Alert, 
        request_info, db_session):
    date_str = alert.created_at.strftime("%Y-%m-%d")
    hour_str = alert.created_at.strftime("%H:%M")
    action_label = alert_notification_templates[language]["expand_alert_action_label"]
    msg_title = alert_notification_templates[language]["expand_alert_title"]
    msg_body = alert_notification_templates[language]["expand_alert_text"].format(date=date_str, hour=hour_str)
    msg_data = {
        "origin": "expand_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

def notify_nearby_users_about_expansion(
        user_ids, fcm_tokens,
        language: str, alert: Alert, 
        request_info, db_session):        
    date_str = alert.created_at.strftime("%Y-%m-%d")
    hour_str = alert.created_at.strftime("%H:%M")
    action_label = alert_notification_templates[language]["expand_alert_action_label"]
    msg_title = alert_notification_templates[language]["expand_alert_title"]
    msg_body = alert_notification_templates[language]["expand_alert_text"].format(date=date_str, hour=hour_str)
    msg_data = {
        "origin": "expand_alert",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    success_count = notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)
    return success_count

## ALERT MESSAGES BTASK: this is the main function that will be executed as a background task when a new alert message is sent.
def task_alert_notify_on_new_message(
        alert: Alert, message: Message, current_user: User, 
        request_info: dict, db_engine):
    if (alert.id is None) or (alert.is_closed):
        return
    users_to_notify_ids = []
    users_to_notify_fcm_tokens = []
    with Session(db_engine) as db_session:
        # The alert sender (alert creator) must be notified,
        # if he is not the one who sent the message (if he is not the current_user)
        if alert.user_id != current_user.id:
            statement = (select(RefreshToken)
                .where(RefreshToken.user_id == alert.user_id)
                .where(RefreshToken.fcm_token != None))
            sender_rtoken = db_session.exec(statement).first()
            if sender_rtoken:
                users_to_notify_ids.append(str(sender_rtoken.user_id))
                users_to_notify_fcm_tokens.append(sender_rtoken.fcm_token)
        # We notify all alerted users, except the current_user (the one who sent the message).
        statement = (select(AlertedUser.user_id, RefreshToken.fcm_token)
                .join(RefreshToken, RefreshToken.user_id == AlertedUser.user_id) # type: ignore
                .where(AlertedUser.alert_id == alert.id)
                .where(RefreshToken.fcm_token != None))
        db_results = db_session.exec(statement).all()
        for row in db_results:
            user_id, fcm_token = row
            if user_id != current_user.id:
                users_to_notify_ids.append(str(user_id))
                users_to_notify_fcm_tokens.append(fcm_token)
        if settings.app_mode == "development":
            time.sleep(10) # line executed only in development-mode, to simulate a long processing time, for manual testing purposes
        # We send notifications, using a multicast notification function. 
        # Note: as language we use the caller's (current_user) language for simplicity, not the language of each client receiving the notification.
        if users_to_notify_ids and users_to_notify_fcm_tokens:
            try:
                msg_content = message.content[:30] if len(message.content) > 30 else message.content
                msg_content += "..." if len(message.content) > 30 else ""
                curr_user_name = f"{current_user.firstname} {current_user.surname}"
                notification_count = notify_on_new_message(
                        users_to_notify_ids, users_to_notify_fcm_tokens, 
                        current_user.language, alert, curr_user_name, msg_content,
                        request_info, db_session)
                log_alert_notify_on_new_message(str(alert.id), request_info, detail=f"Alert message successfully sent to {notification_count} out of {len(users_to_notify_ids)} users")
            except Exception as e:
                log_alert_error_notifying_on_new_message(str(alert.id), request_info, detail=str(e))

def notify_on_new_message(user_ids, fcm_tokens, 
        language, alert, name: str, content: str,
        request_info, db_session):
    action_label = alert_notification_templates[language]["new_message_action_label"]
    msg_title = alert_notification_templates[language]["new_message_title"]
    msg_body = alert_notification_templates[language]["new_message_text"].format(
                name=name, # the name of the user who sent the message
                date=alert.created_at.strftime("%Y-%m-%d"),
                hour=alert.created_at.strftime("%H:%M"),
                text=content
            )
    msg_data = {
        "origin": "new_message",
        "action": "view_alert",
        "action_label": action_label,
        "alert_id": str(alert.id)
    }
    success_count = notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)
    return success_count
