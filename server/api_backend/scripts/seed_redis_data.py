# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timedelta
import math
import argparse
import asyncio
import random
from sqlmodel import Session, select
from core.dbmgr import (
    get_engine, get_redis_handle,
    cluster, redis, RedisHandleTypeError,
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key,
    get_redis_chief_demotions_key,
    get_redis_spec_locations_key,
    get_redis_spec_location_last_updates_key
)
from models.general import User, UserRole
from services.security import now_tz_aware
from services.periodics import CHIEF_DEMOTIONS_TTL_MINUTES, LOCATIONS_TTL_HOURS
from services.network import FAKE_EMAIL_DOMAIN

# --- CONFIGURATION ---
CENTER_LAT = 39.7392 # Denver, Colorado, USA (default central point if no arguments are provided to the script)
CENTER_LON = -104.9903 # Denver, Colorado, USA (default central point if no arguments are provided to the script)
RADIUS_KM = 5.0 # default if no arguments are provided to the script
GPS_PROBABILITY = 0.90  # 90% of users have GPS enabled
GPS_LOCATION_EXPIRATION_PROBABILITY = 0.05  # 5% of GPS locations are expired (for testing purposes)
DEMOTION_PROBABILITY = 0.02  # 2% chance that a user was a chief and has been demoted to regular user (for testing purposes)
DEMOTION_EXPIRATION_PROBABILITY = 0.50  # 50% of demotions are expired (for testing purposes)

db_engine = None
redis_handle = None

def initialize_db_and_redis():
    global db_engine, redis_handle
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

def get_fake_users_from_db(db_session):
    print("Fetching fake users from the database...")
    users = db_session.exec(select(User).where(User.email.endswith(f"@{FAKE_EMAIL_DOMAIN}"))).all()
    print(f"Found {len(users)} fake users.")
    return users

async def flush_redis(redis_session):
    print("Flushing all Redis data...")
    await redis_session.flushdb()
    print("Redis flushed.")
    # We check that Redis is empty after flushing
    keys = await redis_session.keys("*")
    if len(keys) == 0:
        print("Redis is empty after flushing.")

async def seed_redis_gps_and_demotions(fake_users, redis_session):
    print(f"Assigning positions to fake users (GPS Probability: {GPS_PROBABILITY*100}%)...")
    print(f"Central point: ({CENTER_LAT}, {CENTER_LON}), Radius: {RADIUS_KM} km")
    print(f"GPS Location Expiration Probability: {GPS_LOCATION_EXPIRATION_PROBABILITY*100}%")
    print(f"Demotion Probability: {DEMOTION_PROBABILITY*100}%") 
    print(f"Demotion Expiration Probability: {DEMOTION_EXPIRATION_PROBABILITY*100}%")
    placed_count = 0
    not_placed_count = 0
    now = now_tz_aware()
    now_int_ts = int(now.timestamp())
    expired_demotions_int_ts_for_update = int((now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 10)).timestamp())
    expired_locations_int_ts_for_update = int((now - timedelta(hours=LOCATIONS_TTL_HOURS + 1)).timestamp())
    at_least_one_chief_has_gps = False
    at_least_one_chief_has_not_expired_gps = False
    locations_count = 0
    locations_expired_count = 0
    spec_locations_count = 0
    spec_locations_expired_count = 0
    demoted_chiefs_count = 0
    demoted_chiefs_expired_count = 0
    for user in fake_users:
        random_gps_num = random.random()
        random_gps_expiration_num = random.random()
        random_demotion_num = random.random()
        random_demotion_expiration_num = random.random()
        # Decide if this user has GPS enabled
        if (random_gps_num < GPS_PROBABILITY) or (
            user.is_chief and (at_least_one_chief_has_gps == False)
            ):
            lat, lon = get_random_coords(CENTER_LAT, CENTER_LON, RADIUS_KM)
            is_chief = user.is_chief
            is_demoted = False
            user_id_str = str(user.id)
            chief_locations_key = get_redis_chief_locations_key(user_id_str)
            user_locations_key = get_redis_user_locations_key(user_id_str)
            chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
            last_updates_key = get_redis_location_last_updates_key(user_id_str)
            if (not is_chief) and (random_demotion_num < DEMOTION_PROBABILITY):
                # Simulate a user that was a chief but has been demoted to regular user (so it's not a chief anymore)
                is_demoted = True
            async with redis_session.pipeline(transaction=True) as pipe:
                if is_demoted:
                    # Mark the user as demoted in Redis (for testing purposes)
                    demoted_chiefs_count += 1
                    print(f"User {user.id} is marked as demoted (was a chief but now is a regular user).")
                    if random_demotion_expiration_num < DEMOTION_EXPIRATION_PROBABILITY:
                        demoted_at = expired_demotions_int_ts_for_update  # Expired demotion
                        print(f"User {user.id} demotion is expired (demoted at: {datetime.fromtimestamp(demoted_at)})")    
                        demoted_chiefs_expired_count += 1
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
                locations_count += 1
                if (random_gps_expiration_num < GPS_LOCATION_EXPIRATION_PROBABILITY) and (
                    (not is_chief) or (at_least_one_chief_has_not_expired_gps == True)
                    ):
                    pipe.zadd(last_updates_key, {user_id_str: expired_locations_int_ts_for_update})  # Expired location
                    print(f"User {user.id} has an expired GPS location (last update: {datetime.fromtimestamp(expired_locations_int_ts_for_update)})")
                    locations_expired_count += 1
                else:
                    pipe.zadd(last_updates_key, {user_id_str: now_int_ts})
                    if is_chief and (not is_demoted):
                        at_least_one_chief_has_not_expired_gps = True
                if user.role and (user.role in [r.value for r in UserRole]):
                    specloc_key = get_redis_spec_locations_key(user_id_str, user.role)
                    spec_last_upd_key = get_redis_spec_location_last_updates_key(user_id_str, user.role)
                    pipe.geoadd(specloc_key, (lon, lat, user_id_str))
                    spec_locations_count += 1
                    if (random_gps_expiration_num < GPS_LOCATION_EXPIRATION_PROBABILITY):
                        pipe.zadd(spec_last_upd_key, {user_id_str: expired_locations_int_ts_for_update})  # Expired location
                        print(f"User {user.id} with role {user.role} has an expired GPS specialist location (last update: {datetime.fromtimestamp(expired_locations_int_ts_for_update)})")
                        spec_locations_expired_count += 1
                    else:
                        pipe.zadd(spec_last_upd_key, {user_id_str: now_int_ts})
                await pipe.execute()
                placed_count += 1
        else:
            not_placed_count += 1
    print(f"Total fake users in SQL database: {len(fake_users)}")
    print(f"Users with a GPS location placed: {placed_count}")
    print(f"Users without a GPS location placed: {not_placed_count}")
    print(f"Users with a GPS location (total): {locations_count}")
    print(f"Users with expired GPS locations: {locations_expired_count}")
    print(f"Users with a specialist location (total): {spec_locations_count}")
    print(f"Users with expired specialist locations: {spec_locations_expired_count}")
    print(f"Demoted chiefs (total): {demoted_chiefs_count}")
    print(f"Demoted chiefs with expired timestamp: {demoted_chiefs_expired_count}")

async def main():
    fake_users = []
    with Session(db_engine) as db_session:
        fake_users = get_fake_users_from_db(db_session)
    if isinstance(redis_handle, cluster.RedisCluster):
        await flush_redis(redis_handle)
        await seed_redis_gps_and_demotions(fake_users, redis_handle)
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            await flush_redis(redis_session)
            await seed_redis_gps_and_demotions(fake_users, redis_session)
    else:
        raise RedisHandleTypeError(redis_handle)

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Seed Redis database with random GPS locations around a central point and other test Redis data for fake users (emails ending with @{FAKE_EMAIL_DOMAIN}).")
    # Add central point coordinates and radius as optional arguments
    parser.add_argument("--central-lat", type=float, default=CENTER_LAT, help="Central latitude for generating random GPS locations")
    parser.add_argument("--central-lon", type=float, default=CENTER_LON, help="Central longitude for generating random GPS locations")
    parser.add_argument("--radius", type=float, default=RADIUS_KM, help="Radius in kilometers for generating random GPS locations")
    args = parser.parse_args()
    # Update global variables based on command-line arguments
    CENTER_LAT = args.central_lat
    CENTER_LON = args.central_lon
    RADIUS_KM = args.radius
    print(f"Seeding Redis with random GPS locations around central point ({CENTER_LAT}, {CENTER_LON}) with radius {RADIUS_KM} km...")
    initialize_db_and_redis()
    asyncio.run(main())
