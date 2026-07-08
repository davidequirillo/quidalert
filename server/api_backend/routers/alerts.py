# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import (
    APIRouter, Depends, 
    HTTPException, 
    Request, BackgroundTasks)
from fastapi import status as http_status
from dependencies import (get_current_user, 
            get_db_session, get_redis_session, 
            get_geoposition_token_data,
        )
from sqlmodel import Session, desc, select, union_all
from haversine import haversine, Unit
from rapidfuzz import fuzz
from core.exceptions import (
    forbidden_exception,
    not_found_exception
)
from core.logging import get_request_info
from core.dbmgr import (
    get_redis_chief_locations_key, 
    get_redis_user_locations_key, 
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key)
from models.general import (string_as_uuid,
    Alert, AlertType, AlertIn, 
    AlertOut, AlertOutWithInfo, AlertOutWithUsers,
    AlertedUser,
    GpsCoordinatesSchema, GpsTokenData, 
    RefreshToken, User
    )
from services.security import (
    now_tz_naive, now_tz_aware)
from services.alert_btasks import (
    task_alert_search_and_notify
)

router = APIRouter(
    tags=["Alerts"]
)
    
@router.post("/api/alert")
def create_alert(alert_in: AlertIn,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    # Only chiefs can create special type of alerts (managed, general, empty)
    if (alert_in.type != AlertType.local.value):
        if not current_user.is_chief:
            raise forbidden_exception("Only chiefs can create special alerts")
    else:
        if (not current_user.is_reliable) or (current_user.reliability_score <= 0):
            raise forbidden_exception()
    if (alert_in.radius > 1):
        if not current_user.is_chief:
            raise forbidden_exception("Only chiefs can create alerts with radius greater than 1")
    now = now_tz_naive()
    lat_range = 0.2 # 22 km
    long_range = 0.2 # 22 km (approx, at the equator), less at higher latitudes    
    lat_min, lat_max = alert_in.latitude - lat_range, alert_in.latitude + lat_range
    long_min, long_max = alert_in.longitude - long_range, alert_in.longitude + long_range
    recent_alerts = db_session.exec(
        select(Alert).where(
            Alert.created_at > (now - timedelta(hours=1)),
            Alert.latitude > lat_min, # type:ignore
            Alert.latitude < lat_max, # type:ignore
            Alert.longitude > long_min, # type:ignore
            Alert.longitude < long_max # type:ignore
        )
    ).all()
    for rec_alert in recent_alerts:
        if (alert_in.type == AlertType.general.value) and (rec_alert.type == AlertType.general.value):
            d1 = alert_in.description.lower().strip()
            d2 = rec_alert.description.lower().strip()
            similarity = fuzz.token_set_ratio(d1, d2)
            if similarity >= 90: # similarity threshold (90 means 90%)
                return {"message": "Similar general alert already exists", "similarity": similarity}
        if (alert_in.type != AlertType.general.value) and (rec_alert.type != AlertType.general.value):
            dist = haversine((alert_in.latitude, alert_in.longitude), (rec_alert.latitude, rec_alert.longitude), unit=Unit.KILOMETERS)
            if dist < rec_alert.radius:
                d1 = alert_in.description.lower().strip()
                d2 = rec_alert.description.lower().strip()
                similarity = fuzz.token_set_ratio(d1, d2)
                if similarity >= 50: # similarity threshold (50 means 50%)
                    return {"message": "Similar alert already exists in the area", "similarity": similarity}
    alert = Alert(
        type=alert_in.type,
        description = alert_in.description,
        latitude=alert_in.latitude,
        longitude=alert_in.longitude,
        address = alert_in.address,
        radius = alert_in.radius,
        user_id = current_user.id,
        is_pending = True if (alert_in.type != AlertType.general.value) and (alert_in.type != AlertType.empty.value) else False # general and empty alerts are not pending, because we don't have to perform background tasks for this type of alert
    )
    if (alert.type == AlertType.local.value):
        rel_score = current_user.reliability_score 
        alert.radius = min(max(rel_score, 0), 100) / 100 * alert.radius
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    if alert.id is None:
        raise HTTPException(status_code=500, detail="Unknown error creating alert")
    if (alert.type == AlertType.general.value):
        # No need to search for chiefs or users to notify for this type of alert
        return {"message": f"{alert.type.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    if (alert.type == AlertType.empty.value):
        # No need to search for chiefs or users to notify for this type of alert
        return {"message": f"{alert.type.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    # For managed alerts, we need to search for nearby users and notify them
    # For local alerts, we need to search for nearby chiefs and users and notify them
    # so... we must go on with the search and notification process, but we do it in background to avoid making the current user wait for it
    alert_copy = Alert.model_validate(alert)
    curr_user_copy = User.model_validate(current_user)
    req_info = get_request_info(str(current_user.id))
    background_tasks.add_task(
        task_alert_search_and_notify, 
        alert_copy, 
        curr_user_copy, 
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_handle=request.app.state.redis_handle
        )
    if alert.type == AlertType.managed.value:
        return {"message": f"{alert.type.capitalize()} alert created, searching for nearby users to notify"}
    else:
        return {"message": f"{alert.type.capitalize()} alert created, searching for nearby users and chiefs to notify"}

@router.get("/api/alerts/recent", response_model=list[AlertOut])
def get_recent_alerts(current_user: User = Depends(get_current_user),
        db_session: Session = Depends(get_db_session)):
    now = now_tz_naive()
    alerts_by_me_stmt = (select(Alert)
        .where(Alert.user_id == current_user.id, Alert.type != AlertType.general.value)
        .where(Alert.created_at > (now - timedelta(days=365))))
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == current_user.id)
        .where(Alert.created_at > (now - timedelta(days=365))))
    alerts_general_stmt = (select(Alert)
        .where(Alert.type == AlertType.general.value)
        .where(Alert.created_at > (now - timedelta(days=365))))
    statement = union_all(alerts_by_me_stmt, alerts_to_me_stmt, alerts_general_stmt)
    statement = statement.order_by(desc(Alert.created_at))
    alerts = db_session.exec(statement).all() # type: ignore
    for alert in alerts:
        if alert.is_banned:
            alert.description = "[BANNED ALERT]"
    return alerts

# API endpoint used by all users to view general details of a specific alert, 
# for example: description, gps location, sender name and reliability score, number of alerted users
@router.get("/api/alert/{alert_id}", response_model=AlertOutWithInfo)
def get_alert(alert_id: int,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    statement = (select(Alert, User)
        .join(User, Alert.user_id == User.id) # type: ignore
        .where(Alert.id == alert_id))   
    result = db_session.exec(statement).first()
    if result:
        alert = result[0]
        sender = result[1]
    else:
        alert = None
        sender = None
    if (not alert) or (not sender):
        raise not_found_exception("Alert not found")
    if alert.is_banned:
        alert.description = "[BANNED ALERT]"
    current_user_is_the_sender = False
    current_user_is_alerted = False
    chief_is_alerted = False
    chief_closing_vote = 0
    alerted_users_num = 0
    votes_up_num = 0
    votes_down_num = 0
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    if current_user.id == alert.user_id:
        current_user_is_the_sender = True
    for au in alerted_users:
        if au.user_id == current_user.id:
            current_user_is_alerted = True
        if au.is_manager:
            chief_is_alerted = True
            chief_closing_vote = au.closing_vote
        if au.vote > 0:
            votes_up_num += 1
        elif au.vote < 0:
            votes_down_num += 1
        alerted_users_num += 1
    if alert.type != AlertType.general.value:
        # A note about non-general alerts: 
        # base users can only see alerts they created or alerts they were alerted about;
        # officers can see alerts they created, alerts they were alerted about, and alerts created by users authorized by them;
        if ((not current_user_is_the_sender) and 
                (not current_user.is_admin) and 
                    (not current_user.is_chief)):
            if current_user.is_officer:
                if (not current_user_is_alerted):
                    if sender.authorized_by != current_user.email:
                        raise forbidden_exception()
            else:
                if (not current_user_is_alerted):
                    raise forbidden_exception()
    alert_with_info = {
        "alert": alert, 
        "sender_firstname": sender.firstname,
        "sender_surname": sender.surname,
        "sender_reliability_score": sender.reliability_score,
        "alerted_users_num": alerted_users_num,
        "positive_votes_num": votes_up_num,
        "negative_votes_num": votes_down_num,
        "chief_is_alerted": chief_is_alerted,
        "chief_closing_vote": chief_closing_vote
    }
    return alert_with_info

# API endpoint used by the chief to list all users involved in the specific alert (sender and alerted users),
# so he can see their personal info and their votes about the alert
@router.get("/api/alert/{alert_id}/users", response_model=AlertOutWithUsers)
def get_alert_with_users(alert_id: int,
                current_user: User = Depends(get_current_user), 
                db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_chief):
        raise forbidden_exception()
    statement = (select(Alert, User)
        .join(User, Alert.user_id == User.id) # type: ignore
        .where(Alert.id == alert_id))
    result = db_session.exec(statement).first()
    if result:
        alert = result[0]
        sender = result[1]
    else:
        alert = None
        sender = None
    if (not alert) or (not sender):
        raise not_found_exception("Alert not found")
    statement = (select(User, AlertedUser)
        .join(AlertedUser, User.id == AlertedUser.user_id) # type: ignore
        .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    users = []
    votes_map = {}
    for r in results:
        user = r[0]
        alerted_user = r[1]
        users.append(user)
        votes_map[user.id] = alerted_user
    alert_with_users = { 
        "alert": alert, 
        "sender": sender, 
        "users": users, 
        "votes_map": votes_map 
    }
    return alert_with_users

@router.post("/api/alert-close")
def close_alert(alert_id: int,
            request: Request,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_chief):
        raise forbidden_exception()
    alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
    if alert is None:
        raise not_found_exception("Alert not found")
    alert.is_closed = True
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return {"message": "Alert closed"}

@router.post("/api/update-gps-position")
async def update_gps_position(
    gps_data: GpsCoordinatesSchema,
    user_data: GpsTokenData = Depends(get_geoposition_token_data),
    redis_client = Depends(get_redis_session)
):
    user_id_str = user_data.user_id # already a string, no need to convert from UUID
    is_chief = user_data.user_is_chief
    now = now_tz_aware()
    now_int_ts = int(now.timestamp())
    lat, lon = gps_data.latitude, gps_data.longitude
    userloc_key = get_redis_user_locations_key(user_id_str)
    chiefloc_key = get_redis_chief_locations_key(user_id_str)
    last_upd_key = get_redis_location_last_updates_key(user_id_str)
    chief_dem_key = get_redis_chief_demotions_key(user_id_str)
    chief_demoted_at = await redis_client.zscore(chief_dem_key, user_id_str)
    # Potential race condition here if a chief is demoted while updating position,
    # but it's not a big issue because the inconsistency will be temporary (until the next position update)
    # and in the case of an alert, chiefs returned by redis are always checked against the postgres database for safety
    try:
        async with redis_client.pipeline(transaction=True) as pipe:
            if is_chief and (not chief_demoted_at):
                pipe.zrem(userloc_key, user_id_str)
                pipe.geoadd(chiefloc_key, (lon, lat, user_id_str))
            else:
                pipe.zrem(chiefloc_key, user_id_str)
                pipe.geoadd(userloc_key, (lon, lat, user_id_str))
            pipe.zadd(last_upd_key, {user_id_str: now_int_ts})      
            await pipe.execute()
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temporarily unable to update position")
    return {"status": "success", "message": "GPS position updated"}
