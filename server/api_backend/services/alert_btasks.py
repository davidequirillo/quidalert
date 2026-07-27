# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
from fastapi.concurrency import run_in_threadpool
from sqlmodel import Session, select, insert
from fakeredis.aioredis import FakeRedis
from models.general import (
    string_as_uuid,
    RefreshToken, User, 
    Alert, AlertType, AlertedUser)
from services.network import (
    notify_single_client,
    notify_many_clients
)
from core.btask_events import (
    log_alert_search_closest_chiefs_done,
    log_alert_search_nearby_users_done,
    log_alert_error_searching_closest_chiefs,
    log_alert_error_checking_closest_chiefs,
    log_alert_orphan_ids_found_in_checking_closest_chiefs,
    log_alert_error_saving_closest_chief,
    log_alert_no_closest_chief_to_notify,
    log_alert_error_notifying_closest_chief,
    log_alert_notify_closest_chief,
    log_alert_error_searching_nearby_users,
    log_alert_error_checking_nearby_users,
    log_alert_orphan_ids_found_in_checking_nearby_users,
    log_alert_error_saving_nearby_users,
    log_alert_no_nearby_users_to_notify,
    log_alert_error_notifying_nearby_users,
    log_alert_notify_nearby_users,
    log_alert_no_sender_to_notify,
    log_alert_error_notifying_sender,
    log_alert_notify_sender
)
from core.settings import settings

from core.dbmgr import (
    cluster, redis, RedisHandleTypeError,
    get_all_redis_chief_locations_keys,
    get_all_redis_user_locations_keys)

alert_notification_templates = {
    "en": {
        "alert_prefix": "{name} has created a new alert:",
        "no_chief_available_but_nearby_users": "No chief is available, but there are other users nearby who have been notified. Contact emergency services by phone if the situation is serious.",
        "no_chief_available_no_nearby_users": "No chief is available and there are no other users nearby to notify. Contact emergency services by phone if the situation is serious.",
        "chief_and_nearby_users_notified": "The closest chief and nearby users have been notified about the new alert.",
        "only_chief_notified": "The closest chief has been notified about the new alert, but there are no nearby users to notify.",
        "nearby_users_notified": "Nearby users have been notified about the new alert.",
        "no_nearby_users_available": "There are no nearby users to notify about the new alert."
    },
    "it": {
        "alert_prefix": "{name} ha creato una nuova allerta:",
        "no_chief_available_but_nearby_users": "Nessun capo è disponibile, ma ci sono altri utenti nelle vicinanze che sono stati notificati. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "no_chief_available_no_nearby_users": "Nessun capo è disponibile e non ci sono altri utenti nelle vicinanze da notificare. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "chief_and_nearby_users_notified": "Il capo più vicino e gli utenti nelle vicinanze sono stati notificati riguardo alla nuova allerta.",
        "only_chief_notified": "Il capo più vicino è stato notificato riguardo alla nuova allerta, ma non ci sono utenti nelle vicinanze da notificare.",
        "nearby_users_notified": "Gli utenti nelle vicinanze sono stati notificati riguardo alla nuova allerta.",
        "no_nearby_users_available": "Non ci sono utenti nelle vicinanze da notificare riguardo alla nuova allerta."
    }
}

# We search for chiefs within a very large radius, 
# to be sure to find at least one closest chief (because a chief must be alerted, even if he is outside the alert radius)
GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM = 10000

## CREATE ALERT BTASK: This is the main function that will be executed as a background task when a new alert is created.
async def task_alert_search_and_notify(
            alert: Alert, user: User, request_info: dict,
            db_engine, redis_handle):    
    if (alert.id is None) or (alert.is_closed):
        return
    nearby_users_can_be_notified = False
    chief_can_be_notified = False
    sender_can_be_notified = False # sender: the user who created the alert
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(alert, request_info, redis_handle)
    with Session(db_engine) as db_session:
        sender_fcm_token = await run_in_threadpool(
            get_sender_fcm_token, 
            alert, user, request_info, db_session)
        # For local alerts, we keep the first closest chief as alert manager and save him to database (table alerted_users)
        # For non-local alerts, the user who created the alert is the alert manager, so we don't need to search for a chief or save him to database as alert manager
        if (alert.type == AlertType.local.value):
            chief, chief_fcm_token = await run_in_threadpool(
                save_first_chief_in_db, 
                alert, closest_chiefs, request_info, db_session)
        else:
            chief, chief_fcm_token = {
                "user_id": user.id,
                "distance_km": 0.0,
                "location": {
                    "latitude": alert.latitude,
                    "longitude": alert.longitude
                }
            }, sender_fcm_token
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
            log_alert_no_sender_to_notify(str(alert.id), request_info)
        if (alert.type == AlertType.local.value): 
            if chief and chief_fcm_token:
                chief_can_be_notified = True
            else:
                log_alert_no_closest_chief_to_notify(str(alert.id), request_info)
        if nearby_users_to_fcm_tokens.keys():
            nearby_users_can_be_notified = True
        else:
            log_alert_no_nearby_users_to_notify(str(alert.id), request_info)
        if settings.app_mode == "development":
            await asyncio.sleep(10) # line executed only in development-mode, to simulate a long processing time, for manual testing purposes
        # Now we set the alert as not pending anymore, because we have already searched for chiefs and nearby users, and we have saved them in database
        # Note: we don't pass the "alert" object to the function, because it is a copy of the original alert object coming from api endpoint, 
        # so, we need to retrieve the original alert object from database, to update its is_pending field (see function "set_alert_as_not_pending_anymore")
        await run_in_threadpool(
            set_alert_as_not_pending_anymore, 
            alert.id, request_info, db_session)
        if (chief_can_be_notified) or (nearby_users_can_be_notified):
            description = alert.description if (len(alert.description) <= 100) else (alert.description[:100] + "...")
            message_prefix = alert_notification_templates[user.language]["alert_prefix"].format(
                name=user.firstname + " " + user.surname)
            message = message_prefix + " " + description
            if chief and chief_can_be_notified:
                try:
                    chief_id = chief["user_id"]
                    await run_in_threadpool(
                        notify_chief, 
                        alert, chief_id, chief_fcm_token, 
                        message, request_info, db_session)
                    log_alert_notify_closest_chief(str(alert.id), request_info, detail=f"Closest chief {chief_id} notified successfully")
                except Exception as e:
                    chief_can_be_notified = False
                    log_alert_error_notifying_closest_chief(str(alert.id), request_info, detail=str(e))
            if nearby_users_can_be_notified:
                try:
                    user_ids = list(nearby_users_to_fcm_tokens.keys())
                    fcm_tokens = list(nearby_users_to_fcm_tokens.values())
                    notification_count = await run_in_threadpool(
                        notify_nearby_users,
                        alert, user_ids, fcm_tokens, 
                        message, request_info, db_session)
                    if notification_count <= 0:
                        nearby_users_can_be_notified = False
                    log_alert_notify_nearby_users(str(alert.id), request_info, detail=f"{notification_count} nearby users notified successfully, total nearby users: {len(user_ids)}")
                except Exception as e:
                    nearby_users_can_be_notified = False
                    log_alert_error_notifying_nearby_users(str(alert.id), request_info, detail=str(e))
        if sender_can_be_notified:
            if alert.type == AlertType.local.value:
                if not chief_can_be_notified:
                    if nearby_users_can_be_notified:
                        msg_for_sender = alert_notification_templates[user.language]["no_chief_available_but_nearby_users"]
                    else:
                        msg_for_sender = alert_notification_templates[user.language]["no_chief_available_no_nearby_users"]
                else:
                    if nearby_users_can_be_notified:
                        msg_for_sender = alert_notification_templates[user.language]["chief_and_nearby_users_notified"]
                    else:
                        msg_for_sender = alert_notification_templates[user.language]["only_chief_notified"]
            else:
                if nearby_users_can_be_notified:
                    msg_for_sender = alert_notification_templates[user.language]["nearby_users_notified"]
                else:
                    msg_for_sender = alert_notification_templates[user.language]["no_nearby_users_available"]
            try:
                await run_in_threadpool(
                    notify_sender, 
                    alert, str(user.id), sender_fcm_token, 
                    msg_for_sender, request_info, db_session) # notify the user who created the alert
                log_alert_notify_sender(str(alert.id), request_info, detail=f"Sender {user.id} notified successfully")
            except Exception as e:
                log_alert_error_notifying_sender(str(alert.id), request_info, detail=str(e))
    
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
        
async def get_closest_chiefs(alert, request_info, redis_client):
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
        
async def get_nearby_users(alert, request_info, redis_client):
    """
    Searches for users near a specific alert across all shards in parallel.
    This is the core of the universal scaling architecture.
    """
    nearby_users = []
    # We obtain all shards keys for user locations
    shard_keys = get_all_redis_user_locations_keys()
    try:
        # 1. Preparation: we create the tasks (one for each shard)
        tasks = [
            redis_client.geosearch(
                name=key,
                longitude=alert.longitude,
                latitude=alert.latitude,
                radius=alert.radius,
                unit="km",
                sort="asc",
                count=1000, 
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
        # 5. Filtering: we keep only the first 1000 entries
        if len(all_matches) > 1000:
            all_matches = all_matches[:1000]
        for user_id, distance, coords in all_matches:
            if user_id != str(alert.user_id): # we exclude the user who created the alert from the list of nearby users, to avoid duplicates or errors
                nearby_users.append({
                    "user_id": user_id,
                    "distance_km": round(distance, 3),
                    "location": {
                        "latitude": coords[1],  # Redis returns (lon, lat)
                        "longitude": coords[0]
                    }
                })
        log_alert_search_nearby_users_done(str(alert.id), request_info, detail=f"{len(nearby_users)} nearby users found and sorted successfully")
        return nearby_users
    except Exception as e:
        log_alert_error_searching_nearby_users(str(alert.id), request_info, detail=str(e))
        return []

def save_first_chief_in_db(alert, closest_chiefs, request_info, db_session):
    if not closest_chiefs:
        return None, None
    chief = None
    fcm_token = None
    chief_ids_as_uuid = []
    for c in closest_chiefs:
        try:
            uuid = string_as_uuid(c["user_id"])
            chief_ids_as_uuid.append(uuid)
        except Exception as e:
            log_alert_error_checking_closest_chiefs(str(alert.id), request_info, detail=f"Error converting chief user_id string to UUID: {e}")
            continue
    statement = (select(User.id, RefreshToken.fcm_token)
    .join(RefreshToken, RefreshToken.user_id == User.id) # type: ignore
    .where(User.id.in_(chief_ids_as_uuid)) # type: ignore
    .where(User.is_chief == True, RefreshToken.fcm_token != None))
    try:
        db_results = db_session.exec(statement).all()
        chiefs_to_tokens = {str(row[0]): row[1] for row in db_results}
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
                fcm_token = chiefs_to_tokens.get(c["user_id"])
                break
    except Exception as e:
        log_alert_error_checking_closest_chiefs(str(alert.id), request_info, detail=str(e))
        chief = None
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
        fcm_token = None
    return chief, fcm_token

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
        log_alert_error_saving_nearby_users(str(alert_id), request_info, detail=f"Error setting alert pending status to False: {e}")
    return

def save_nearby_users_in_db(alert, users, request_info, db_session):
    if not users:
        return {}
    ids_as_uuid = []
    users_to_distances = {}
    users_to_tokens = {}
    for u in users:
        try:
            uuid = string_as_uuid(u["user_id"])
            ids_as_uuid.append(uuid)
            users_to_distances[str(uuid)] = u["distance_km"]
        except Exception as e:
            log_alert_error_checking_nearby_users(str(alert.id), request_info, detail=f"Error converting user_id string to UUID: {e}")
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
            log_alert_orphan_ids_found_in_checking_nearby_users(str(alert.id), request_info, detail=err_detail)
    except Exception as e:
        log_alert_error_checking_nearby_users(str(alert.id), request_info, detail=str(e))
        users_to_tokens = {}
    try:
        if users_to_tokens and existing_ids_in_db:
            valid_data_for_db_bulk_insert = []
            for u_id in existing_ids_in_db:
                try:
                    user_uuid = string_as_uuid(u_id)
                    user_distance = users_to_distances.get(u_id, 0.0)
                except Exception as e:
                    log_alert_error_saving_nearby_users(str(alert.id), request_info, detail=f"Error converting user_id string to UUID: {e}")
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
                # bulk insert nearby users into alerted_users table 
                stmt = insert(AlertedUser)
                db_session.exec(stmt, params=valid_data_for_db_bulk_insert)
                db_session.commit()
    except Exception as e:
        db_session.rollback()
        log_alert_error_saving_nearby_users(str(alert.id), request_info, detail=str(e))
        users_to_tokens = {}
    return users_to_tokens

def get_sender_fcm_token(alert, sender, request_info, db_session):
    fcm_token = None
    statement = select(RefreshToken).where(
        RefreshToken.user_id == sender.id).where(
            RefreshToken.fcm_token != None)
    try:
        rtoken = db_session.exec(statement).first()
        if rtoken:
            fcm_token = rtoken.fcm_token
    except Exception as e:
        log_alert_error_notifying_sender(str(alert.id), request_info, detail=str(e))
    return fcm_token
    
def notify_nearby_users(alert, user_ids, fcm_tokens, message: str, request_info, db_session):
    msg_title = "New Alert"
    msg_body = message
    msg_data = {
        "type": "new_alert",
        "alert_id": str(alert.id)
    }
    success_count = notify_many_clients(
        user_ids, fcm_tokens, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)
    return success_count

def notify_chief(alert, user_id, fcm_token, message: str, request_info, db_session):  
    msg_title = "New Alert"
    msg_body = message
    msg_data = {
        "type": "new_alert",
        "alert_id": str(alert.id)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

def notify_sender(alert, user_id, fcm_token, message: str, request_info, db_session):
    msg_title = "New Alert"
    msg_body = message
    msg_data = {
        "type": "new_alert",
        "alert_id": str(alert.id)
    }
    return notify_single_client(
        user_id, fcm_token, 
        msg_title, msg_body, msg_data, 
        request_info, db_session)

## CLOSE ALERT BTASK: This is the main function that will be executed as a background task when an alert is closed.
async def task_alert_notify_after_closure(
            alert: Alert, user: User, request_info: dict,
            db_engine, redis_handle):    
    if (alert.id is None) or (not alert.is_closed):
        return
    