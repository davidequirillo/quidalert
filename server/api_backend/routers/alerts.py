# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import APIRouter, Depends, Request, BackgroundTasks
from dependencies import get_db_session
from sqlmodel import Session, select
from haversine import haversine, Unit
from rapidfuzz import fuzz
from core.exceptions import forbidden_exception
from core.security_events import get_request_info
from models.general import Alert, AlertIn, User
from dependencies import get_current_user
from services.security import now_tz_naive
from services.tasks import notify_nearby_users

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
        notify_nearby_users, 
        alert_copy, 
        curr_user, 
        request_info=req_info,
        db_engine=request.app.state.db_engine,
        redis_pool=request.app.state.redis_pool
        )
    return {"message": "Alert created"}