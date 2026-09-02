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
from models.general import UserRole
from services.alert_btasks import (
    get_zone_users,
)
from tests.fixtures.alerts import (
    create_test_alert, # required (fixture test_alert)
    create_test_request_info # required (fixture test_request_info)
)
from core.settings import settings

# The function "get_zone_users" is used by the alert expansion background task to extract all users who are within a certain radius from the alert location, 
# or if role is specified, all specialists (users with a specific role) within the same area. 
# Note: this function calls "get_nearby_users" (see services.alert_btasks module) with proper arguments to get the nearby users or specialists in the area, in expansion mode.
# The function uses Redis to get the locations of users or specialists, and filters them based on the role and radius.

async def test_get_zone_users_who_have_no_role(redis_session, test_alert, test_request_info):
    # In our test environment, we force Redis to operate in cluster mode with 16 logical shards.
    assert settings.redis_mode == 'cluster'
    assert settings.redis_logical_shards_num in [16]
    # Some checks on test_alert and test_request_info
    assert test_alert.user_id is not None
    assert test_alert.radius == 1 # 1 km radius
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
    # Zone users are only users who reside inside the alert radius
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
    # Now we try to call the same function using a radius not None as input parameter, greater than the alert radius,
    # so the function will use the input radius instead of the alert radius,
    # and we will check that the returned users are more than the previous call
    radius = 500 # 500 km radius
    zone_users_with_larger_radius = await get_zone_users(test_alert, radius, None, test_request_info, redis_engine)
    assert len(zone_users_with_larger_radius) > len(zone_users)
    # 14 users are inside 500 km radius: 
    # user_1 to user_5 are inside the first small radius of 1 km, 
    # and user_6 to user_14 are outside the small alert radius but inside the larger radius (500 km)
    assert len(zone_users_with_larger_radius) == 14

async def test_get_zone_users_with_role(redis_session, test_alert, test_request_info):
    # In our test environment, we force Redis to operate in cluster mode with 16 logical shards.
    assert settings.redis_mode == 'cluster'
    assert settings.redis_logical_shards_num in [16]
    # We add some specialist locations to Redis, near the test alert (inside alert.radius)
    # For example, we add 5 medics
    role = UserRole.medic.value
    for i in range(1, 6):
        user_id = f"specialist_{i}"
        user_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        spec_locations_key = get_redis_spec_locations_key(user_id, UserRole.medic.value)
        spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id, UserRole.medic.value)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(spec_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(spec_last_updates_key, {user_id: now_int_ts})
    # We add 4 alpine rescuers with the same locations more or less
    role = UserRole.alpinerescuer.value
    for i in range(6, 10):
        user_id = f"specialist_{i}"
        user_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        spec_locations_key = get_redis_spec_locations_key(user_id, UserRole.alpinerescuer.value)
        spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id, UserRole.alpinerescuer.value)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(spec_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(spec_last_updates_key, {user_id: now_int_ts})
    # Now we add some medics and alpine rescuers outside the alert radius
    for i in range(10, 20):
        role = UserRole.medic.value if i % 2 == 0 else UserRole.alpinerescuer.value
        user_id = f"specialist_{i}"
        user_location = (test_alert.latitude + 0.1 * i, test_alert.longitude + 0.1 * i)
        spec_locations_key = get_redis_spec_locations_key(user_id, role)
        spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id, role)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(spec_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(spec_last_updates_key, {user_id: now_int_ts})
    # Now we call the function to get the zone users with role "alpinerescuer"
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    zone_specialists = await get_zone_users(test_alert, None, UserRole.alpinerescuer.value, test_request_info, redis_engine)
    # Zone specialists are only alpine rescuers who reside inside the alert radius
    expected_zone_specialist_ids = set([f"specialist_{i}" for i in range(6, 10)])
    for specialist in zone_specialists:
        assert specialist["user_id"] in expected_zone_specialist_ids
        assert specialist["distance_km"] is not None
        assert specialist["distance_km"] <= test_alert.radius
    assert len(zone_specialists) == len(expected_zone_specialist_ids)
    # We also check that the nearby specialists are ordered by distance
    zone_specialists_sorted_by_distance = sorted(zone_specialists, key=lambda x: x["distance_km"])
    assert zone_specialists == zone_specialists_sorted_by_distance
    # Now we try to call the same function using a radius not None as input parameter, greater than the alert radius,
    # so the function will use the input radius instead of the alert radius,
    # and we will check that the returned specialists are more than the previous call
    radius = 500 # 500 km radius
    zone_specialists_with_larger_radius = await get_zone_users(test_alert, radius, UserRole.alpinerescuer.value, 
                                                    test_request_info, redis_engine)
    assert len(zone_specialists_with_larger_radius) > len(zone_specialists)
    # 9 alpine rescuers are inside 500 km radius
    # We added 4 alpine rescuers inside the first small radius of 1 km (specialist_6 to specialist_9) 
    # and 5 alpine rescuers outside the small radius, but inside the larger radius (500 km) 
    # (specialist_11, specialist_13, specialist_15, specialist_17, specialist_19),
    # so inside the larger radius we have 4 + 5 = 9 alpine rescuers
    assert len(zone_specialists_with_larger_radius) == 9
