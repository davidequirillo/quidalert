# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import APIRouter, Depends, HTTPException, Request, BackgroundTasks
from dependencies import (get_current_user, 
            get_db_session, get_redis_session, 
            get_geoposition_token_data,
        )
from sqlmodel import Session, select
from haversine import haversine, Unit
from rapidfuzz import fuzz
from core.exceptions import forbidden_exception
from core.security_events import get_request_info
from core.dbmgr import (
    get_redis_chief_locations_key, 
    get_redis_user_locations_key, 
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key)
from models.general import Alert, AlertIn, GpsCoordinatesSchema, GpsTokenData, User
from services.security import now_tz_naive, ensure_tz_aware
from services.btasks import (
    task_alert_search_and_notify, task_alert_cleanup)

router = APIRouter(
    tags=["Alerts"]
)
    
@router.post("/api/alert")
def create_alert(alert_in: AlertIn,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_reliable) or \
        (current_user.reliability_score <= 0) or \
            (current_user.is_blocked):
        raise forbidden_exception()
    now = now_tz_naive()
    lat_range = 0.2 # 22 km
    long_range = 0.2 # 22 km (approx, at the equator), less at higher latitudes    
    lat_min, lat_max = alert_in.latitude - lat_range, alert_in.latitude + lat_range
    long_min, long_max = alert_in.longitude - long_range, alert_in.longitude + long_range
    recent_alerts = db_session.exec(
        select(Alert).where(
            Alert.created_at > (now - timedelta(hours=1)),
            Alert.latitude > lat_min,
            Alert.latitude < lat_max,
            Alert.longitude > long_min,
            Alert.longitude < long_max
        )
    ).all()
    for rec_alert in recent_alerts:
        dist = haversine((alert_in.latitude, alert_in.longitude), (rec_alert.latitude, rec_alert.longitude), unit=Unit.KILOMETERS)
        if dist < rec_alert.radius:
            d1 = alert_in.description.lower().strip()
            d2 = rec_alert.description.lower().strip()
            similarity = fuzz.token_set_ratio(d1, d2)
            if similarity >= 50: # similarity threshold (50 means 50%)
                return {"message": "Similar alert already exists in the area", "similarity": similarity}
    alert = Alert(
        latitude=alert_in.latitude,
        longitude=alert_in.longitude,
        user_id = current_user.id,
        description = alert_in.description,
        address = alert_in.address
    )
    rel_score = current_user.reliability_score 
    alert.radius = rel_score / 100 * alert.radius
    alert.severity = int(rel_score / 100 * alert.severity)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    alert_copy = alert.model_copy()
    curr_user = current_user.model_copy()
    req_info = get_request_info(str(current_user.id))
    background_tasks.add_task(
        task_alert_search_and_notify, 
        alert_copy, 
        curr_user, 
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_pool=request.app.state.redis_pool
        )
    return {"message": "Alert created"}

@router.post("/api/update-gps-position")
async def update_gps_position(
    gps_data: GpsCoordinatesSchema,
    user_data: GpsTokenData = Depends(get_geoposition_token_data),
    redis_client = Depends(get_redis_session)
):
    user_id = user_data.user_id
    user_id_str = str(user_id)
    is_chief = user_data.user_is_chief
    now = ensure_tz_aware(now_tz_naive())
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

@router.post("/api/alert-close")
def close_alert(alert_id: int,
            request: Request,
            background_tasks: BackgroundTasks,
            current_user: User = Depends(get_current_user), 
            db_session: Session = Depends(get_db_session)):
    if (not current_user.is_admin) and (not current_user.is_chief):
        raise forbidden_exception()
    alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
    if alert is None:
        return {"message": "Alert not found"}
    alert.is_closed = True
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    alert_copy = alert.model_copy()
    curr_user = current_user.model_copy()
    req_info = get_request_info(str(current_user.id))
    background_tasks.add_task(
        task_alert_cleanup, 
        alert_copy, 
        curr_user, 
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_pool=request.app.state.redis_pool
        )
    return {"message": "Alert created"}