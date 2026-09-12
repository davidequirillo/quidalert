# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime
from fastapi import (
    APIRouter, Depends, 
    HTTPException)
from dependencies import (
    get_redis_session, 
    get_geoposition_token_data,
)
from core.exceptions import (
    invalid_request_exception
)
from core.api_events import (
    log_gps_position_updated
)   
from core.dbmgr import (
    get_redis_chief_locations_key, 
    get_redis_user_locations_key, 
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key,
    get_redis_spec_locations_key,
    get_redis_spec_location_last_updates_key
)
from models.general import (
    UserRole, GpsLocationSchema, GpsBatchLocations, GpsTokenData,
)
from services.security import (
    now_tz_aware,
    from_timestamp_to_datetime_tz_aware,
    ensure_tz_aware,
)

router = APIRouter(
    tags=["Locations"]
)

## Last known GPS position update endpoint

@router.get("/api/locations/last-known-gps-position")
async def last_known_gps_position(
    user_data: GpsTokenData = Depends(get_geoposition_token_data),
    redis_client = Depends(get_redis_session)
):
    user_id_str = user_data.user_id # already a string, no need to convert from UUID
    is_chief = user_data.user_is_chief
    if is_chief:
        location_key = get_redis_chief_locations_key(user_id_str)
    else:
        location_key = get_redis_user_locations_key(user_id_str)
    last_upd_key = get_redis_location_last_updates_key(user_id_str)
    location = await redis_client.geopos(location_key, user_id_str)
    last_update = await redis_client.zscore(last_upd_key, user_id_str)
    if (not location) or (not last_update):
        return None
    last_update_dt = from_timestamp_to_datetime_tz_aware(last_update)
    return {
        "latitude": location[0][1],
        "longitude": location[0][0],
        "last_update": last_update_dt.isoformat()
    }

## GPS position update endpoint

@router.post("/api/locations/update-gps-position")
async def update_gps_position(
    gps_data: GpsBatchLocations,
    user_data: GpsTokenData = Depends(get_geoposition_token_data),
    redis_client = Depends(get_redis_session)
):
    if not gps_data.locations:
        raise invalid_request_exception("No GPS locations provided")
    # We only take the last location from the batch
    gps_location: GpsLocationSchema = gps_data.locations[-1]
    user_id_str = user_data.user_id # already a string, no need to convert from UUID
    is_chief = user_data.user_is_chief
    user_role = user_data.user_role
    if gps_location.timestamp:
        # Get the current timestamp from the location data
        now = ensure_tz_aware(datetime.fromisoformat(gps_location.timestamp))
        now_int_ts = int(now.timestamp())
    else:
        # If no timestamp is provided in the location data, use the current time
        now = now_tz_aware()
        now_int_ts = int(now.timestamp())
    lat, lon = gps_location.latitude, gps_location.longitude
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
            if user_role and (user_role in [r.value for r in UserRole]):
                specloc_key = get_redis_spec_locations_key(user_id_str, user_role)
                spec_last_upd_key = get_redis_spec_location_last_updates_key(user_id_str, user_role)
                pipe.geoadd(specloc_key, (lon, lat, user_id_str))
                pipe.zadd(spec_last_upd_key, {user_id_str: now_int_ts})
            await pipe.execute()
        log_gps_position_updated(
            user_id_str, lat, lon, 
            gps_location.location_id, gps_location.accuracy, 
            gps_location.is_moving, gps_location.speed, gps_location.activity, gps_location.timestamp)
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"Temporarily unable to update position")
    return {"status": "success", "message": "GPS position updated"}
