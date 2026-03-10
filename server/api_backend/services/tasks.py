# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import uuid
import redis.asyncio as redis
from sqlmodel import Session, select, insert, update
from firebase_admin import messaging
from models.general import Alert, RefreshToken, User, UserLanguage, AlertedUser
from core.tasks_events import (
    log_alert_error_searching_closest_chief,
    log_alert_error_searching_nearby_users,
    log_alert_error_saving_chief_and_users,
    log_alert_orphan_ids_found_in_saving_chief_and_users,
    log_alert_no_user_to_notify,
    log_alert_no_chief_to_notify,
    log_alert_no_nearby_users_to_notify,
    log_alert_no_owner_to_notify,
    log_alert_error_notifying_chief,
    log_alert_error_notifying_nearby_users,
    log_alert_warning_notifying_nearby_users,
    log_alert_error_notifying_owner,
    log_alert_notify_chief,
    log_alert_notify_nearby_users,
    log_alert_notify_owner)

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
    owner_can_be_notified = False # owner: the user who created the alert
    chief, users = asyncio.run(
        get_closest_chief_and_nearby_users(alert, request_info, redis_pool))
    with Session(db_engine) as db_session:
        users_to_fcm_tokens = save_chief_and_users(alert, chief, users, request_info, db_session)
    if not users_to_fcm_tokens:
        log_alert_no_user_to_notify(str(alert.id), request_info)
        return
    if users_to_fcm_tokens.get(user.id):
        owner_can_be_notified = True
    else:
        log_alert_no_owner_to_notify(str(alert.id), request_info)
    if chief and users_to_fcm_tokens.get(chief["user_id"]):
        chief_can_be_notified = True
    else:
        log_alert_no_chief_to_notify(str(alert.id), request_info)
        if users_to_fcm_tokens:
            if users_to_fcm_tokens.get(user.id):
                if len(users_to_fcm_tokens) > 1:
                    nearby_users_can_be_notified = True
                else:
                    log_alert_no_nearby_users_to_notify(str(alert.id), request_info)
    with Session(db_engine) as db_session: # needed to do some cleaning (invalid fcm tokens)
        if (chief_can_be_notified) or (nearby_users_can_be_notified):
            description = alert.description if len(alert.description) <= 100 else alert.description[:100] + "..."
            msg_for_nearby_prefix = alert_notification_templates[user.language]["alert_prefix"].format(
                name=user.firstname + " " + user.surname)
            msg_for_nearby= msg_for_nearby_prefix + " " + description
            if chief and chief_can_be_notified:
                try:
                    chief_user_id = chief["user_id"]
                    chief_fcm_token = users_to_fcm_tokens[chief_user_id]
                    chief_can_be_notified = notify_chief(alert, chief_user_id, chief_fcm_token, msg_for_nearby, request_info, db_session)
                except Exception as e:
                    chief_can_be_notified = False
                    log_alert_error_notifying_chief(str(alert.id), request_info, detail=str(e))
            if users_to_fcm_tokens and nearby_users_can_be_notified:
                try: 
                    notification_count = notify_nearby_users(alert, users_to_fcm_tokens, msg_for_nearby, request_info, db_session)
                    if not notification_count or notification_count <= 0:
                        nearby_users_can_be_notified = False
                    else:
                        nearby_users_can_be_notified = True
                except Exception as e:
                    nearby_users_can_be_notified = False
                    log_alert_error_notifying_nearby_users(str(alert.id), request_info, detail=str(e))
        if owner_can_be_notified:
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
            fcm_token = users_to_fcm_tokens[user.id]
            try:
                notify_owner(alert, user.id, fcm_token, msg_for_user, request_info, db_session) # notify the user who created the alert
            except Exception as e:
                log_alert_error_notifying_owner(str(alert.id), request_info, detail=str(e))
        db_session.commit()
    
async def get_closest_chief_and_nearby_users(alert, request_info, redis_pool):    
    async with redis.Redis(connection_pool=redis_pool, decode_responses=True) as redis_client:
        chief = await get_closest_chief(alert, request_info, redis_client)
        users = await get_nearby_users(alert, request_info, redis_client)
    return chief, users

async def get_closest_chief(alert, request_info, redis_client):
    try:
        results = await redis_client.geosearch(
            name="chief_locations",
            longitude=alert.longitude,
            latitude=alert.latitude,
            radius=10000, # Max radius in km to search for chiefs (10,000 km is basically the whole world)
            unit="km",
            sort="asc", # Sort by distance (closest first)    
            count=1,
            withdist=True,
            withcoord=True)
        if not results:
            raise Exception("No chiefs found within 10,000 km radius")
        user_id, distance, coords = results[0]
        closest_chief = {
            "user_id": user_id,
            "distance_km": round(distance, 3),
            "location": {
                "latitude": coords[1], # redis returns (longitude, latitude) format
                "longitude": coords[0]
            }
        }
        return closest_chief
    except Exception as e:
        log_alert_error_searching_closest_chief(str(alert.id), request_info, detail=str(e))
        return None
        
async def get_nearby_users(alert, request_info, redis_client):
    nearby_users = []
    try:
        results = await redis_client.geosearch(
            name="user_locations",
            longitude=alert.longitude,
            latitude=alert.latitude,
            radius=alert.radius,
            unit="km",
            sort="asc", # Sort by distance (closest first)
            count=1000, # Max number of nearby users to return
            withdist=True,
            withcoord=True)   
        for user_id, distance, coords in results:
            nearby_users.append({
                "user_id": user_id,
                "distance_km": round(distance, 3),
                "location": {
                    "latitude": coords[1], # redis returns (longitude, latitude) format
                    "longitude": coords[0]
                }
            })
        return nearby_users
    except Exception as e:
        log_alert_error_searching_nearby_users(str(alert.id), request_info, detail=str(e))
        return None

def save_chief_and_users(alert, chief, users, request_info, db_session):   
    if users:
        users.append(chief) # also include the chief in the list of users to save and notify (if chief is not None) 
    else:
        users = [chief] if chief else []
    ids = [u["user_id"] for u in users]
    ids_as_uuid = []
    for uid in ids:
        try:
            ids_as_uuid.append(uuid.UUID(uid))
        except Exception as e:
            log_alert_error_saving_chief_and_users(str(alert.id), request_info, detail=f"Error converting user_id string to UUID: {e}")
            continue
    ids_as_uuid.append(alert.user_id) # also include the user who created the alert
    statement = (
        select(User.id, RefreshToken.fcm_token)
        .join(RefreshToken, RefreshToken.user_id == User.id) # type: ignore
        .where(User.id.in_(ids_as_uuid)) # type: ignore
        .where(RefreshToken.fcm_token != None)
    )
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
            db_session.execute(
                insert(AlertedUser), 
                valid_data_for_db_bulk_insert)
            db_session.commit()
            return users_to_tokens
    except Exception as e:
        log_alert_error_saving_chief_and_users(str(alert.id), request_info, detail=str(e))
        return None
    
def notify_nearby_users(alert, users_to_tokens, message: str, request_info, db_session):
    del users_to_tokens[alert.user_id] # remove the alert's owner from nearby users
    user_ids = list(users_to_tokens.keys())
    tokens = list(users_to_tokens.values())
    success_count = 0
    failure_count = 0
    # Firebase allows sending notifications to a maximum of 500 tokens at a time
    for i in range(0, len(tokens), 500):
        chunk_tokens = tokens[i:i+500]
        chunk_user_ids = user_ids[i:i+500]
        push_msg = messaging.MulticastMessage(
            notification=messaging.Notification(
                title="Alert",
                body=message
            ),
            data={
                "type": "alert",
                "route": "/proximity-map",
                "click_action": "FLUTTER_NOTIFICATION_CLICK"
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
                # We clean unregistered FCM tokens (by ids in...) from database
                statement = update(RefreshToken).where(
                    RefreshToken.user_id.in_(tokens_to_delete_by_ids)).values( # type:ignore
                        fcm_token=None, fcm_token_updated_at=None)
                db_session.execute(statement)
                db_session.flush()
                log_alert_warning_notifying_nearby_users(str(alert.id), request_info, detail=f"Invalid FCM tokens deleted from db: {tokens_to_delete}")
        success_count += response.success_count
        failure_count += response.failure_count
    log_alert_notify_nearby_users(str(alert.id), request_info, detail=f"{success_count} success, {failure_count} failures")
    return success_count

def notify_chief(alert, user_id, fcm_token, message: str, request_info, db_session):
    return notify_single_user(alert, user_id, fcm_token, message, request_info, log_alert_notify_chief, log_alert_error_notifying_chief, db_session)

def notify_owner(alert, user_id, fcm_token, message: str, request_info, db_session):
    return notify_single_user(alert, user_id, fcm_token, message, request_info, log_alert_notify_owner, log_alert_error_notifying_owner, db_session)

def notify_single_user(alert, user_id, fcm_token, message: str, request_info, log_success, log_error, db_session):
    push_msg = messaging.Message(
        notification=messaging.Notification(
            title="Alert",
            body=message
        ),
        data={
            "type": "alert",
            "route": "/alerts/recents",
            "click_action": "FLUTTER_NOTIFICATION_CLICK"
        },
        token=fcm_token,
    )
    try:
        response = messaging.send(push_msg)
        log_success(str(alert.id), request_info, detail=str(response))
        return True
    except messaging.UnregisteredError as e:
        # We clean unregistered FCM tokens (by ids in...) from database
        statement = select(RefreshToken).where(RefreshToken.user_id == user_id)
        rtoken = db_session.execute(statement).first()
        if rtoken:
            rtoken.fcm_token = None
            rtoken.fcm_token_updated_at = None
            db_session.add(rtoken)
            db_session.flush()
        raise(e)
    except Exception as e:
        log_error(str(alert.id), request_info, detail=str(e))
        raise(e)
    