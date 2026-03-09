# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import uuid
import redis.asyncio as redis
from sqlmodel import Session, select, insert
# todo: from firebase_admin import messaging
from models.general import Alert, RefreshToken, User, UserLanguage, AlertedUser
from core.tasks_events import (
    log_alert_error_searching_closest_chief,
    log_alert_error_searching_nearby_users,
    log_alert_error_saving_chief_and_users,
    log_alert_error_notifying_chief_and_users,
    log_alert_notify_user,
    log_alert_notify_chief_and_users)

alert_notification_templates = {
    "en": {
        "no_chief_available_with_users": "No chief is available, but there are other users nearby who have been notified. Contact emergency services by phone if the situation is serious.",
        "no_chief_available_no_users": "No chief is available and there are no other users nearby to notify. Contact emergency services by phone if the situation is serious.",
        "chief_and_users_notified": "The closest chief and nearby users have been notified about the new alert.",
        "alert_prefix": "Has created a new alert:"
    },
    "it": {
        "no_chief_available_with_users": "Nessun capo è disponibile, ma ci sono altri utenti nelle vicinanze che sono stati notificati. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "no_chief_available_no_users": "Nessun capo è disponibile e non ci sono altri utenti nelle vicinanze da notificare. Contatta telefonicamente i soccorsi se la situazione è grave.",
        "chief_and_users_notified": "Il capo più vicino e gli utenti nelle vicinanze sono stati notificati della nuova allerta.",
        "alert_prefix": "Ha creato una nuova allerta:"
    }
}

def task_alert_search_and_notify( # notify chief and nearby users about the new alert
            alert: Alert, user: User, request_info: dict,
            db_engine, redis_pool):    
    if alert.is_closed:
        return
    msg_for_user = ""
    msg_for_nearby = ""
    chief, users = asyncio.run(
        get_closest_chief_and_nearby_users(alert, request_info, redis_pool))
    if (not chief):
        if users and (len(users) > 1):
            if user.language == UserLanguage.it:
                msg_for_user = alert_notification_templates["it"]["no_chief_available_with_users"]
            else:
                msg_for_user = alert_notification_templates["en"]["no_chief_available_with_users"]
        else:
            if user.language == UserLanguage.it:
                msg_for_user = alert_notification_templates["it"]["no_chief_available_no_users"]
            else:
                msg_for_user = alert_notification_templates["en"]["no_chief_available_no_users"]
    with Session(db_engine) as db_session:
        users_to_fcm_tokens = save_chief_and_users(alert, chief, users, request_info, db_session)
    description = alert.description if len(alert.description) <= 100 else alert.description[:100] + "..."
    msg_for_nearby_prefix = alert_notification_templates[user.language]["alert_prefix"]
    msg_for_nearby= user.firstname + " " + user.surname + " " + msg_for_nearby_prefix.lower() + " " + description
    notify_recipients(alert, users_to_fcm_tokens, msg_for_nearby, request_info) # notify closest chief and nearby users
    msg_for_user = alert_notification_templates[user.language]["chief_and_users_notified"]
    if users_to_fcm_tokens:
        fcm_token = users_to_fcm_tokens[user.id]
        notify_user(alert, user.id, fcm_token, msg_for_user, request_info) # notify the user who created the alert
    else:
        log_alert_error_notifying_chief_and_users(str(alert.id), request_info, message="no user to notify")

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
        log_alert_error_searching_closest_chief(str(alert.id), request_info, message=str(e))
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
        log_alert_error_searching_nearby_users(str(alert.id), request_info, message=str(e))
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
            log_alert_error_saving_chief_and_users(str(alert.id), request_info, message=f"Error converting user_id string to UUID: {e}")
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
            msg = f"Warning: orphan user_ids found (in Redis but not in Postgres): {orphans}"
            log_alert_error_saving_chief_and_users(str(alert.id), request_info, message=msg)
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
        log_alert_error_saving_chief_and_users(str(alert.id), request_info, message=str(e))
        return None
    
def notify_recipients(alert, users_to_tokens, message: str, request_info):
    if not users_to_tokens:
        log_alert_error_notifying_chief_and_users(str(alert.id), request_info, message="no user to notify")
    fcm_tokens = []
    for k, v in users_to_tokens.items():
        if k != alert.user_id:
            fcm_tokens.append(v)
    # todo: implement actual notification sending using FCM API
    # message = messaging.MulticastMessage(
    #    notification=messaging.Notification(
    #        title="Alert",
    #        body=message
    #   ),
    #    data={
    #        "type": "proximity_alert",
    #        "user_id": "multiple", # O i dati che servono al tuo frontend
    #    },
    #    tokens=fcm_tokens,
    #)

def notify_user(alert, user_id, fcm_token, message: str, request_info):
    # todo: Get FCM token from user profile and send push notification using FCM API
    log_alert_notify_user(str(alert.id), request_info, message=message)   