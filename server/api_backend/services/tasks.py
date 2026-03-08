# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import redis.asyncio as redis
from sqlmodel import Session, select, insert
from models.general import Alert, User
from core.tasks_events import (
    log_alert_notify_nearby_users,
    log_alert_error_saving_nearby_chief_and_users,
    log_alert_error_searching_nearby_users,
    log_alert_error_searching_nearest_chief)

def notify_nearby_users(
        alert: Alert, user: User, request_info: dict,
        db_engine, redis_pool):
    if alert.is_closed:
        return
    nearest_chief = None
    nearby_users = []
    async def get_nearby_chief_and_users():
        async with redis.Redis(connection_pool=redis_pool, decode_responses=True) as redis_client:
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
                nearest_chief = {
                    "user_id": user_id.decode("utf-8"),
                    "distance_km": round(distance, 3),
                    "location": {
                        "latitude": coords[1],
                        "longitude": coords[0]
                    }
                }
            except Exception as e:
                log_alert_error_searching_nearest_chief(str(alert.id),request_info)
                print(f"Error searching the nearest chief: {e}")
            try:
                results = await redis_client.geosearch(
                    name="user_locations",
                    longitude=alert.longitude,
                    latitude=alert.latitude,
                    radius=alert.radius,
                    unit="km",
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
            except Exception as e:
                log_alert_error_searching_nearby_users(str(alert.id),request_info)
                print(f"Error searching nearby users: {e}")
        # redis connection end
    asyncio.run(get_nearby_chief_and_users())  
    with Session(db_engine) as session:
        try:
            pass
            # bulk insert chief and nearby users into alerted_users table 
        except Exception as e:
            log_alert_error_saving_nearby_chief_and_users(str(alert.id),request_info)
            print(f"Error saving chief and nearby users to database: {e}")
    # todo: send push notification to nearby chief and users
    log_alert_notify_nearby_users(str(alert.id), request_info)
    