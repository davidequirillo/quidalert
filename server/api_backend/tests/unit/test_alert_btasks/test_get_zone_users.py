# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from haversine import haversine, Unit
from services.security import (
    now_tz_aware
)
from core.dbmgr import (
    get_redis_location_last_updates_key,
    get_redis_user_locations_key,
    get_redis_spec_location_last_updates_key,
    get_redis_spec_locations_key,
)
from services.alert_btasks import (
    get_zone_users,
)
from tests.fixtures.alerts import (
    create_test_alert, # required (fixture test_alert)
    create_test_request_info # required (fixture test_request_info)
)

# The function "get_zone_users" is used by the alert expansion task to extract all users who are within a certain radius, 
# or if role is specified, all specialists (users with a specific role) within a certain radius, from the alert location. 
# The function uses Redis to get the locations of users or specialists, and filters them based on the role and alert radius.

async def test_get_zone_users(redis_session, test_alert, test_request_info):
    # Some checks on test_alert and test_request_info
    assert test_alert.user_id is not None
    assert test_request_info["request_id"] == "request_id_123"
    # We add some user locations to Redis, near the test alert (inside alert.radius)
    for i in range(1, 6):
        user_id = f"user_{i}"
        user_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        user_locations_key = get_redis_user_locations_key(user_id)
        last_updates_key = get_redis_location_last_updates_key(user_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
        # We assert that the distance from the alert coordinates to the user locations is less than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
        assert distance <= test_alert.radius
    # Now we add some user ids outside the alert radius
    for i in range(6, 15):
        user_id = f"user_{i}"
        user_location = (test_alert.latitude + 0.1 * i, test_alert.longitude + 0.1 * i)
        user_locations_key = get_redis_user_locations_key(user_id)
        last_updates_key = get_redis_location_last_updates_key(user_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
        # We assert that the distance from the alert coordinates to the user locations is greater than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
        assert distance > test_alert.radius
    # Now we call the function to get the zone users
    # Note: we pass None for radius and None for role, 
    # so the function will use the alert radius and will not filter by role 
    # (meaning it will return all users inside the area)
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    zone_users = await get_zone_users(test_alert, None, None, test_request_info, redis_engine)
    # Zone users are only users inside the alert radius
    expected_zone_user_ids = set([f"user_{i}" for i in range(1, 6)])
    for user in zone_users:
        assert user["user_id"] in expected_zone_user_ids
        assert user["distance_km"] is not None
        assert user["distance_km"] <= test_alert.radius
        location = user["location"]
        assert location["latitude"] < test_alert.latitude + 0.0015
        assert location["latitude"] > test_alert.latitude - 0.0015
        assert location["longitude"] < test_alert.longitude + 0.0015
        assert location["longitude"] > test_alert.longitude - 0.0015
    assert len(zone_users) == len(expected_zone_user_ids)
    # We also check that the nearby users are ordered by distance
    zone_users_sorted_by_distance = sorted(zone_users, key=lambda x: x["distance_km"])
    assert zone_users == zone_users_sorted_by_distance
