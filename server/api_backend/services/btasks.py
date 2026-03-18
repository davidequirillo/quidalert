# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import uuid
import redis.asyncio as redis
from sqlmodel import Session, select, insert, update
from firebase_admin import messaging
from core.settings import settings
from models.general import (
    RefreshToken, User, UserLanguage, 
    Alert, AlertedUser)
from core.btask_events import (
    log_alert_error_searching_closest_chief,
    log_alert_error_searching_nearby_users,
    log_alert_error_saving_chief_and_users,
    log_alert_orphan_ids_found_in_saving_chief_and_users,
    log_alert_no_user_to_notify,
    log_alert_no_chief_to_notify,
    log_alert_no_nearby_users_to_notify,
    log_alert_no_sender_to_notify,
    log_alert_error_notifying_chief,
    log_alert_error_notifying_nearby_users,
    log_alert_warning_notifying_nearby_users,
    log_alert_error_notifying_sender,
    log_alert_notify_chief,
    log_alert_notify_nearby_users,
    log_alert_notify_sender)

from core.dbmgr import (
    get_all_redis_chief_locations_keys,
    get_all_redis_user_locations_keys)

alert_notification_templates = {
    "en": {
        "no_chief_available_with_nearby_users": "No chief is available, but there are other users nearby who have been notified. Contact emergency services by phone if the situation is serious.",
        "no_chief_available_no_nearby_users": "No chief is available and there are no other users nearby to notify. Contact emergency services by phone if the situation is serious.",
        "chief_and_users_notified": "The closest chief and nearby users have been notified about the new alert.",
        "chief_notified": "The closest chief has been notified about the new alert.",
        "alert_prefix": "{name} has created a new alert:"
    },
    "it": {
        "no_chief_available_with_nearby_users": "Nessun capo è disponibile, ma ci sono altri utenti nelle vicinanze che sono stati notificati. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "no_chief_available_no_nearby_users": "Nessun capo è disponibile e non ci sono altri utenti nelle vicinanze da notificare. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "chief_and_users_notified": "Il capo più vicino e gli utenti nelle vicinanze sono stati notificati della nuova allerta.",
        "chief_notified": "Il capo più vicino è stato notificato della nuova allerta.",
        "alert_prefix": "{name} ha creato una nuova allerta:"
    }
}

def task_alert_search_and_notify( # notify chief and nearby users about the new alert
            alert: Alert, user: User, request_info: dict,
            db_engine, redis_pool):    
    if alert.is_closed:
        return
    nearby_users_can_be_notified = False
    chief_can_be_notified = False
    sender_can_be_notified = False # sender: the user who created the alert
    chief, nearby_users = asyncio.run(
        get_closest_chief_and_nearby_users(
            alert, request_info, redis_pool)
        )
    sender = { # info about the user who created the alert, to be used in logging and notifications
        "user_id": str(user.id),
        "distance_km": 0,
        "location": {
            "latitude": alert.latitude,
            "longitude": alert.longitude
            }
    }
    users = nearby_users if nearby_users else []
    users.append(sender)
    if (chief):
        users.append(chief)
    users_to_fcm_tokens = check_users_against_db_and_save(alert, users, request_info, db_engine)
    if not users_to_fcm_tokens:
        log_alert_no_user_to_notify(str(alert.id), request_info)
        return
    if users_to_fcm_tokens.get(sender["user_id"]):
        sender_can_be_notified = True
    else:
        log_alert_no_sender_to_notify(str(alert.id), request_info)
    if chief and users_to_fcm_tokens.get(chief["user_id"]):
        chief_can_be_notified = True
    else:
        log_alert_no_chief_to_notify(str(alert.id), request_info)
    for u in users_to_fcm_tokens.keys():
        if (u != sender["user_id"]) and ((not chief) or (u != chief["user_id"])):
            nearby_users_can_be_notified = True
            break
    if not nearby_users_can_be_notified:
        log_alert_no_nearby_users_to_notify(str(alert.id), request_info)
    if (chief_can_be_notified) or (nearby_users_can_be_notified):
        description = alert.description if len(alert.description) <= 100 else alert.description[:100] + "..."
        msg_for_nearby_prefix = alert_notification_templates[user.language]["alert_prefix"].format(
            name=user.firstname + " " + user.surname)
        msg_for_nearby= msg_for_nearby_prefix + " " + description
        if chief and chief_can_be_notified:
            try:
                chief_user_id = chief["user_id"]
                chief_fcm_token = users_to_fcm_tokens[chief_user_id]
                chief_can_be_notified = notify_chief(alert, chief_user_id, chief_fcm_token, msg_for_nearby, request_info, db_engine)
            except Exception as e:
                chief_can_be_notified = False
                log_alert_error_notifying_chief(str(alert.id), request_info, detail=str(e))
        if nearby_users_can_be_notified:
            try:
                users_to_fcm_tokens.pop(sender["user_id"], None) # remove the alert's sender from nearby users
                if chief:
                    users_to_fcm_tokens.pop(chief["user_id"], None) # remove the chief from nearby users
                user_ids = list(users_to_fcm_tokens.keys())
                fcm_tokens = list(users_to_fcm_tokens.values())
                notification_count = notify_nearby_users(alert, user_ids, fcm_tokens, msg_for_nearby, request_info, db_engine)
                if not notification_count or notification_count <= 0:
                    nearby_users_can_be_notified = False
                else:
                    nearby_users_can_be_notified = True
            except Exception as e:
                nearby_users_can_be_notified = False
                log_alert_error_notifying_nearby_users(str(alert.id), request_info, detail=str(e))
    if sender_can_be_notified:
        if not chief_can_be_notified:
            if nearby_users_can_be_notified:
                msg_for_user = alert_notification_templates[user.language]["no_chief_available_with_nearby_users"]
            else:
                msg_for_user = alert_notification_templates[user.language]["no_chief_available_no_nearby_users"]
        else:
            if nearby_users_can_be_notified:
                msg_for_user = alert_notification_templates[user.language]["chief_and_users_notified"]
            else:
                msg_for_user = alert_notification_templates[user.language]["chief_notified"]
        fcm_token = users_to_fcm_tokens[sender["user_id"]]
        try:
            notify_sender(alert, sender["user_id"], fcm_token, msg_for_user, request_info, db_engine) # notify the user who created the alert
        except Exception as e:
            log_alert_error_notifying_sender(str(alert.id), request_info, detail=str(e))
    
async def get_closest_chief_and_nearby_users(alert, request_info, redis_pool):
    chief, users = None, []
    if settings.redis_mode == "cluster":
        chief = await get_closest_chief(alert, request_info, redis_pool)
        users = await get_nearby_users(alert, request_info, redis_pool)
        return chief, users
    else:
        async with redis.Redis(connection_pool=redis_pool, decode_responses=True) as redis_client:
            chief = await get_closest_chief(alert, request_info, redis_client)
            users = await get_nearby_users(alert, request_info, redis_client)
        return chief, users

async def get_closest_chief(alert, request_info, redis_client):
    # We obtain all shards keys for chief locations
    shard_keys = get_all_redis_chief_locations_keys()
    try:    
        # 1. Preparation: we create the tasks (one for each shard) to search for the closest chief in each shard in parallel 
        tasks = [
            redis_client.geosearch(
                name=key,
                longitude=alert.longitude,
                latitude=alert.latitude,
                radius=10000, 
                unit="km",
                sort="asc",
                count=10, # we search for the closest 10 chiefs
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
            raise Exception("No chiefs found within 10,000 km radius")
        # 4. Sorting
        all_candidates.sort(key=lambda x: x[1]) # x[1] is the distance
        user_id, distance, coords = all_candidates[0]
        return {
            "user_id": user_id,
            "distance_km": round(distance, 3),
            "location": {
                "latitude": coords[1],
                "longitude": coords[0]
            }
        }
    except Exception as e:
        log_alert_error_searching_closest_chief(str(alert.id), request_info, detail=str(e))
        return None
        
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
        for user_id, distance, coords in all_matches[:1000]:
            nearby_users.append({
                "user_id": user_id,
                "distance_km": round(distance, 3),
                "location": {
                    "latitude": coords[1],  # Redis returns (lon, lat)
                    "longitude": coords[0]
                }
            })
        return nearby_users
    except Exception as e:
        log_alert_error_searching_nearby_users(str(alert.id), request_info, detail=str(e))
        return []

def check_users_against_db_and_save(alert, users, request_info, db_engine):
    ids = [u["user_id"] for u in users]
    ids_as_uuid = []
    for uid in ids:
        try:
            ids_as_uuid.append(uuid.UUID(uid))
        except Exception as e:
            log_alert_error_saving_chief_and_users(str(alert.id), request_info, detail=f"Error converting user_id string to UUID: {e}")
            continue
    users_to_tokens = []
    with Session(db_engine) as db_session:
        statement = (select(User.id, RefreshToken.fcm_token)
            .join(RefreshToken, RefreshToken.user_id == User.id) # type: ignore
            .where(User.id.in_(ids_as_uuid)) # type: ignore
            .where(RefreshToken.fcm_token != None))
        try:
            db_results = db_session.exec(statement).all()
            users_to_tokens = {row[0]: row[1] for row in db_results}
            # Identification of orphans 
            # Who is in Redis, but not in Postgres? (very rare event)
            existing_ids_in_db = set(users_to_tokens.keys())
            orphans = [uid for uid in ids_as_uuid if uid not in existing_ids_in_db]
            if orphans:
                err_detail = f"Orphan user_ids found (in Redis but not in Postgres): {orphans}"
                log_alert_orphan_ids_found_in_saving_chief_and_users(str(alert.id), request_info, detail=err_detail)
            valid_data_for_db_bulk_insert = []
            for u_id in existing_ids_in_db:
                if u_id != alert.user_id: # don't insert the user who created the alert into alerted_users table (we insert only the chief and nearby users)
                    valid_data_for_db_bulk_insert.append({
                        "alert_id": alert.id,
                        "user_id": u_id,
                        "vote": 0,
                        "closing_vote": 0
                    })
            if valid_data_for_db_bulk_insert:
                # bulk insert chief and nearby users into alerted_users table 
                stmt = insert(AlertedUser)
                db_session.exec(stmt, params=valid_data_for_db_bulk_insert)
                db_session.commit()
        except Exception as e:
            log_alert_error_saving_chief_and_users(str(alert.id), request_info, detail=str(e))
            users_to_tokens = None
    return users_to_tokens
    
def notify_nearby_users(alert, user_ids, fcm_tokens, message: str, request_info, db_engine):
    success_count = 0
    failure_count = 0
    # Firebase allows sending notifications to a maximum of 500 tokens at a time
    for i in range(0, len(fcm_tokens), 500):
        chunk_tokens = fcm_tokens[i:i+500]
        chunk_user_ids = user_ids[i:i+500]
        push_msg = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Alert",
                body=message
            ),
            data={
                "type": "alert",
                "route": "/alerts/recents"
            },
            tokens=chunk_tokens
        )
        response = messaging.send_each_for_multicast(push_msg)
        if response.failure_count > 0:
            tokens_to_delete_by_ids = []
            tokens_to_delete = []
            for index, res in enumerate(response.responses):
                if not res.success:
                    if res.exception.code == 'messaging/registration-token-not-registered':
                        tokens_to_delete_by_ids.append(chunk_user_ids[index])
                        tokens_to_delete.append(chunk_tokens[index])
            if tokens_to_delete_by_ids:
                with Session(db_engine) as db_session:
                # We clean unregistered FCM tokens (by ids in...) from database
                    statement = update(RefreshToken).where(
                        RefreshToken.user_id.in_(tokens_to_delete_by_ids) # type:ignore
                        ).where(RefreshToken.fcm_token.in_(tokens_to_delete) # type:ignore
                        ).values(
                            fcm_token=None, fcm_token_updated_at=None)
                    db_session.exec(statement)
                    db_session.commit()
                log_alert_warning_notifying_nearby_users(str(alert.id), request_info, detail=f"Invalid FCM tokens deleted from db: {tokens_to_delete}")
        success_count += response.success_count
        failure_count += response.failure_count
    log_alert_notify_nearby_users(str(alert.id), request_info, detail=f"{success_count} success, {failure_count} failures")
    return success_count

def notify_chief(alert, user_id, fcm_token, message: str, request_info, db_engine):
    return notify_single_user(alert, user_id, fcm_token, message, request_info, log_alert_notify_chief, log_alert_error_notifying_chief, db_engine)

def notify_sender(alert, user_id, fcm_token, message: str, request_info, db_engine):
    return notify_single_user(alert, user_id, fcm_token, message, request_info, log_alert_notify_sender, log_alert_error_notifying_sender, db_engine)

def notify_single_user(alert, user_id, fcm_token, message: str, request_info, log_success, log_error, db_engine):
    push_msg = messaging.Message(
        notification=messaging.Notification(
            title="Alert",
            body=message
        ),
        data={
            "type": "alert",
            "route": "/alerts/recents",
        },
        token=fcm_token,
    )
    try:
        response = messaging.send(push_msg)
        log_success(str(alert.id), request_info, detail=str(response))
        return True
    except messaging.UnregisteredError as e:
        with Session(db_engine) as db_session: # needed to do some cleaning (if there are invalid fcm tokens)
            # We clean unregistered FCM token from database
            statement = select(RefreshToken).where(
                RefreshToken.user_id == user_id).where(
                    RefreshToken.fcm_token == fcm_token)
            rtoken = db_session.exec(statement).first()
            if rtoken:
                rtoken.fcm_token = None
                rtoken.fcm_token_updated_at = None
                db_session.add(rtoken)
                db_session.commit()
        raise(e)
    except Exception as e:
        log_error(str(alert.id), request_info, detail=str(e))
        raise(e)
    
def task_alert_cleanup(
            alert: Alert, user: User, request_info: dict,
            db_engine, redis_pool):
    # alert cleanups
    return
