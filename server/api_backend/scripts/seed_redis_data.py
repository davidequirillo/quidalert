# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timedelta
import asyncio
import math
import random
from sqlmodel import Session, select
from core.dbmgr import (
    get_engine, get_redis_handle,
    cluster, redis, RedisHandleTypeError,
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key,
)
from models.general import User
from services.security import now_tz_aware
from services.periodics import CHIEF_DEMOTIONS_TTL_MINUTES, LOCATIONS_TTL_HOURS

# --- CONFIGURATION ---
DENVER_LAT = 39.7392
DENVER_LON = -104.9903
RADIUS_KM = 8
GPS_PROBABILITY = 0.90  # 90% of users have GPS enabled
GPS_LOCATION_EXPIRATION_PROBABILITY = 0.05  # 5% of GPS locations are expired (for testing purposes)
DEMOTION_PROBABILITY = 0.02  # 2% chance that a user was a chief and has been demoted to regular user (for testing purposes)
DEMOTION_EXPIRATION_PROBABILITY = 0.50  # 50% of demotions are expired (for testing purposes)

db_engine = get_engine()
redis_handle = get_redis_handle()

def get_random_coords(lat, lon, max_km):
    # We convert the maximum distance from kilometers to degrees (for latitude it's approximately 111.32 km per degree)
    max_radius_degrees = max_km / 111.32
    # We generate a random angle and a random radius (with a distribution that ensures uniformity in the area)
    angle = random.uniform(0, 2 * math.pi)
    # The square root ensures uniform distribution over the area
    radius = math.sqrt(random.uniform(0, 1)) * max_radius_degrees
    # Calculate the deltas in degrees
    delta_lat = radius * math.cos(angle)
    # For longitude, we need to divide by the cosine of the latitude
    # (meridians converge as we approach the poles)
    lat_in_radians = math.radians(lat)
    delta_lon = (radius * math.sin(angle)) / math.cos(lat_in_radians)
    return lat + delta_lat, lon + delta_lon

def get_users_from_db(db_session):
    print("Fetching users from the database...")
    users = db_session.exec(select(User)).all()
    print(f"Found {len(users)} users.")
    return users

async def flush_redis(redis_session):
    print("Flushing Redis data...")
    await redis_session.flushdb()
    print("Redis flushed.")
    # We check that Redis is empty after flushing
    keys = await redis_session.keys("*")
    if len(keys) == 0:
        print("Redis is empty after flushing.")

async def seed_redis_gps_and_demotions(users, redis_session):
    print(f"Assigning positions to users (GPS Probability: {GPS_PROBABILITY*100}%)...")
    placed_count = 0
    not_placed_count = 0
    now = now_tz_aware()
    now_int_ts = int(now.timestamp())
    expired_demotions_int_ts_for_update = int((now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 10)).timestamp())
    expired_locations_int_ts_for_update = int((now - timedelta(hours=LOCATIONS_TTL_HOURS + 1)).timestamp())
    expired_demotions_int_ts = int((now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES)).timestamp())
    expired_locations_int_ts = int((now - timedelta(hours=LOCATIONS_TTL_HOURS)).timestamp())
    at_least_one_chief_has_gps = False
    at_least_one_chief_has_not_expired_gps = False
    for user in users:
        # Decide if this user has GPS enabled
        if (random.random() < GPS_PROBABILITY) or (
            user.is_chief and (at_least_one_chief_has_gps == False)
            ):
            lat, lon = get_random_coords(DENVER_LAT, DENVER_LON, RADIUS_KM)
            is_chief = user.is_chief
            is_demoted = False
            user_id_str = str(user.id)
            chief_locations_key = get_redis_chief_locations_key(user_id_str)
            user_locations_key = get_redis_user_locations_key(user_id_str)
            chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
            last_updates_key = get_redis_location_last_updates_key(user_id_str)
            if (not is_chief) and (random.random() < DEMOTION_PROBABILITY):
                # Simulate a user that was a chief but has been demoted to regular user (so it's not a chief anymore)
                is_demoted = True
            async with redis_session.pipeline(transaction=True) as pipe:
                if is_demoted:
                    # Mark the user as demoted in Redis (for testing purposes)
                    if random.random() < DEMOTION_EXPIRATION_PROBABILITY:
                        demoted_at = expired_demotions_int_ts_for_update  # Expired demotion
                    else:   
                        demoted_at = now_int_ts # active demotion (not expired)
                    pipe.zadd(chief_demotions_key, {user_id_str: demoted_at})
                if is_chief and (not is_demoted):
                    pipe.zrem(user_locations_key, user_id_str)  # Remove from user locations if previously added
                    pipe.geoadd(chief_locations_key, (lon, lat, user_id_str))
                    at_least_one_chief_has_gps = True
                else:
                    pipe.zrem(chief_locations_key, user_id_str)  # Remove from chief locations if previously added
                    pipe.geoadd(user_locations_key, (lon, lat, user_id_str)) 
                if (random.random() < GPS_LOCATION_EXPIRATION_PROBABILITY) and (
                    (not is_chief) or (at_least_one_chief_has_not_expired_gps == True)
                    ):
                    pipe.zadd(last_updates_key, {user_id_str: expired_locations_int_ts_for_update})  # Expired location
                else:
                    pipe.zadd(last_updates_key, {user_id_str: now_int_ts})
                    if is_chief and (not is_demoted):
                        at_least_one_chief_has_not_expired_gps = True      
                await pipe.execute()
                placed_count += 1
        else:
            not_placed_count += 1
    print(f"Total users in SQL: {len(users)}")
    print(f"Users with a GPS location placed: {placed_count}")
    print(f"Users without a GPS location placed: {not_placed_count}")
    # We calculate the number of users with a GPS location in Redis and how many of those locations are expired (for testing purposes)
    locations_count = 0
    locations_expired_count = 0
    for user in users:
        last_updates_key = get_redis_location_last_updates_key(str(user.id))
        last_update_timestamp = await redis_session.zscore(last_updates_key, str(user.id))
        if (last_update_timestamp is not None):
            locations_count += 1
            if (last_update_timestamp <= expired_locations_int_ts):
                locations_expired_count += 1
                print(f"User {user.id} has an expired GPS location (last update: {datetime.fromtimestamp(last_update_timestamp)})")
    print(f"Users with a GPS location (total): {locations_count}")
    print(f"Users with expired GPS locations: {locations_expired_count}")
    # We calculate the number of demoted chiefs in Redis
    demoted_chiefs_count = 0
    demoted_chiefs_expired_count = 0
    for user in users:
        chief_demotions_key = get_redis_chief_demotions_key(str(user.id))
        demotion_timestamp = await redis_session.zscore(chief_demotions_key, str(user.id))
        if demotion_timestamp is not None:
            demoted_chiefs_count += 1
            if demotion_timestamp <= expired_demotions_int_ts:
                demoted_chiefs_expired_count += 1
                print(f"User {user.id} is marked as demoted with an expired timestamp ({datetime.fromtimestamp(demotion_timestamp)})")
            else:
                print(f"User {user.id} is marked as demoted with an active timestamp ({datetime.fromtimestamp(demotion_timestamp)})")
    print(f"Demoted chiefs (total): {demoted_chiefs_count}")
    print(f"Demoted chiefs with expired timestamp: {demoted_chiefs_expired_count}")

async def main():
    users = []
    with Session(db_engine) as db_session:
        users = get_users_from_db(db_session)
    if isinstance(redis_handle, cluster.RedisCluster):
        await flush_redis(redis_handle)
        await seed_redis_gps_and_demotions(users, redis_handle)
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            await flush_redis(redis_session)
            await seed_redis_gps_and_demotions(users, redis_session)
    else:
        raise RedisHandleTypeError(redis_handle)

if __name__ == "__main__":
    asyncio.run(main())
