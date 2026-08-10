# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from haversine import haversine, Unit
from models.general import (
    User,
    AlertType
)
from services.security import (
    now_tz_aware
)
from core.dbmgr import (
    get_redis_chief_locations_key,
    get_redis_location_last_updates_key,
    get_redis_user_locations_key
)
from services.alert_btasks import (
    get_closest_chiefs_and_nearby_users
)
from tests.fixtures.alerts import (
    create_test_alert, # required (fixture test_alert)
    create_test_request_info # required (fixture test_request_info)
)

# The function "get_closest_chiefs_and_nearby_users" is used by the alert creation background task to extract the closest chiefs 
# and all nearby users who are within a certain radius from the alert location.
# Note: this function calls "get_closest_chiefs" and "get_nearby_users" (see services.alert_btasks module) 
# with proper arguments to get separately the closest chiefs and nearby users in the area, in creation mode.
# These two functions use Redis to get the locations of chiefs and users, and filter them based on the distance from the alert location.

async def test_get_closest_chiefs_and_nearby_users(redis_session, test_alert, test_request_info):
    # Some checks on test_alert and test_request_info
    assert test_alert.user_id is not None
    assert test_alert.radius == 1 # 1 km radius
    assert test_request_info["request_id"] == "request_id_123"
    # We add some chief locations to Redis, near the test alert
    # We create 7 chief ids and locations around the alert (some within the alert radius, some outside), 
    # and 13 user ids and locations around the alert (some within the alert radius, some outside)
    # We start with 4 chiefs inside the alert radius
    for i in range(4):
        chief_id = f"chief_{i}"
        chief_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        chief_locations_key = get_redis_chief_locations_key(chief_id)
        last_updates_key = get_redis_location_last_updates_key(chief_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(chief_locations_key, (chief_location[1], chief_location[0], chief_id))
        await redis_session.zadd(last_updates_key, {chief_id: now_int_ts})
        # we assert that the distance from the alert coordinates to the chief locations is less than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, chief_location, unit=Unit.KILOMETERS)
        assert distance <= test_alert.radius
    # Now we add 3 chiefs outside the alert radius
    for i in range(4, 7):
        chief_id = f"chief_{i}"
        chief_location = (test_alert.latitude + 0.1 * i, test_alert.longitude + 0.1 * i)
        chief_locations_key = get_redis_chief_locations_key(chief_id)
        last_updates_key = get_redis_location_last_updates_key(chief_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(chief_locations_key, (chief_location[1], chief_location[0], chief_id))
        await redis_session.zadd(last_updates_key, {chief_id: now_int_ts})
        # we assert that the distance from the alert coordinates to the chief locations is greater than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, chief_location, unit=Unit.KILOMETERS)
        assert distance > test_alert.radius
    # We also add some user locations to Redis, near the test alert (inside the radius)
    for i in range(7, 12):
        user_id = f"user_{i}"
        user_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        user_locations_key = get_redis_user_locations_key(user_id)
        last_updates_key = get_redis_location_last_updates_key(user_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
        # we assert that the distance from the alert coordinates to the user locations is less than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
        assert distance <= test_alert.radius
    # Now we add some user ids outside the alert radius
    for i in range(12, 20):
        user_id = f"user_{i}"
        user_location = (test_alert.latitude + 0.1 * i, test_alert.longitude + 0.1 * i)
        user_locations_key = get_redis_user_locations_key(user_id)
        last_updates_key = get_redis_location_last_updates_key(user_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
        # we assert that the distance from the alert coordinates to the user locations is greater than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
        assert distance > test_alert.radius
    # Now we call the function to get the closest chiefs and nearby users
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    # We assert that the closest chiefs are all chiefs
    # We remember that the closest chiefs are all chiefs (at maximum the first 100, in our example 7 chiefs), 
    # ordered by distance, even those outside the alert radius
    expected_closest_chief_ids = set([f"chief_{i}" for i in range(4)] + [f"chief_{i}" for i in range(4, 7)])
    for chief in closest_chiefs:
        assert chief["user_id"] in expected_closest_chief_ids
        assert chief["distance_km"] is not None
        location = chief["location"]
        assert location["latitude"] < test_alert.latitude + 1.0
        assert location["latitude"] > test_alert.latitude - 1.0
        assert location["longitude"] < test_alert.longitude + 1.0
        assert location["longitude"] > test_alert.longitude - 1.0
    assert len(closest_chiefs) == len(expected_closest_chief_ids)
    # Nearby users are only users inside the alert radius
    expected_nearby_user_ids = set([f"user_{i}" for i in range(7, 12)])
    for user in nearby_users:
        assert user["user_id"] in expected_nearby_user_ids
        assert user["distance_km"] is not None
        assert user["distance_km"] <= test_alert.radius
        location = user["location"]
        assert location["latitude"] < test_alert.latitude + 0.0015
        assert location["latitude"] > test_alert.latitude - 0.0015
        assert location["longitude"] < test_alert.longitude + 0.0015
        assert location["longitude"] > test_alert.longitude - 0.0015
    assert len(nearby_users) == len(expected_nearby_user_ids)
    # We also check that the closest chiefs are ordered by distance
    closest_chiefs_sorted_by_distance = sorted(closest_chiefs, key=lambda x: x["distance_km"])
    assert closest_chiefs == closest_chiefs_sorted_by_distance
    # We also check that the nearby users are ordered by distance
    nearby_users_sorted_by_distance = sorted(nearby_users, key=lambda x: x["distance_km"])
    assert nearby_users == nearby_users_sorted_by_distance
    # Now we check that the function returns an empty list of nearby users if the alert radius is very small
    test_alert.radius = 0.00001  # very small radius
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    # Nearby users empty for a very small alert radius, obviously
    assert len(nearby_users) == 0
    # But closest chiefs are still returned, because they are not related to the alert radius
    assert len(closest_chiefs) == len(expected_closest_chief_ids)
    # Now, we check that the function returns an empty list of closest chiefs
    # if the alert type is "managed" (created only by a chief, so the closest chief will be the alert creator)
    test_alert.type = AlertType.managed.value
    test_alert.radius = 1.0  # we set a normal radius, to check that nearby users are still returned
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    assert len(closest_chiefs) == 0
    # Nearby users are still returned, because they are not related to the alert type
    expected_nearby_user_ids = set([f"user_{i}" for i in range(7, 12)])
    for user in nearby_users:
        assert user["user_id"] in expected_nearby_user_ids
        assert user["distance_km"] <= test_alert.radius
    assert len(nearby_users) == len(expected_nearby_user_ids)

async def test_get_closest_chiefs_and_nearby_users_exclude_alert_user_id(db_session, redis_session, test_alert, test_request_info):
    # We insert some closest chiefs and nearby users in Redis
    for i in range(3):
        chief_id = f"chief_{i}"
        chief_location = (test_alert.latitude + 0.0001 * i, test_alert.longitude + 0.0001 * i)
        chief_locations_key = get_redis_chief_locations_key(chief_id)
        last_updates_key = get_redis_location_last_updates_key(chief_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(chief_locations_key, (chief_location[1], chief_location[0], chief_id))
        await redis_session.zadd(last_updates_key, {chief_id: now_int_ts})
        # We assert that the distance from the alert coordinates to the chief locations is less than alert radius
        alert_coords = (test_alert.latitude, test_alert.longitude)
        distance = haversine(alert_coords, chief_location, unit=Unit.KILOMETERS)
        assert distance <= test_alert.radius
    for i in range(3, 7):
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
    # Now we insert the alert user id in the closest chiefs and in the nearby users, in Redis
    test_alert_creator = User(
        firstname="Alert",
        surname="Creator",
        email="alert.creator@example.com",
        password_hash="fakepwdhash",
        activation_code="fakeactivationcode",
        activation_expires_at=None,
        is_active=True,
        is_superuser=False,
        is_admin=False,
        is_chief=True
    )
    db_session.add(test_alert_creator)
    db_session.commit()
    db_session.refresh(test_alert_creator)
    test_alert.user_id = test_alert_creator.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    user_id = str(test_alert_creator.id)
    chief_id = user_id
    chief_locations_key = get_redis_chief_locations_key(chief_id)
    user_locations_key = get_redis_user_locations_key(user_id)
    last_updates_key = get_redis_location_last_updates_key(user_id)
    now_int_ts = int(now_tz_aware().timestamp())
    # The alert creator is located near the alert, inside the alert radius
    user_location = (test_alert.latitude + 0.00001, test_alert.longitude + 0.00001)
    await redis_session.geoadd(chief_locations_key, (user_location[1], user_location[0], chief_id))
    await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
    await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
    assert user_location is not None
    alert_coords = (test_alert.latitude, test_alert.longitude)
    distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
    assert distance <= test_alert.radius
    # Now we call the function to get the closest chiefs and nearby users
    # We check that the function excludes the alert user id from the closest chiefs and from the nearby users, even if it is within the alert radius
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    for user in nearby_users:
        assert user["user_id"] != str(test_alert.user_id)
        assert user["distance_km"] <= test_alert.radius
        location = user["location"]
        assert location["latitude"] < test_alert.latitude + 0.001
        assert location["latitude"] > test_alert.latitude - 0.001
        assert location["longitude"] < test_alert.longitude + 0.001
        assert location["longitude"] > test_alert.longitude - 0.001
    assert len(nearby_users) == 4  # only the other 4 nearby users
    for chief in closest_chiefs:
        assert chief["user_id"] != str(test_alert.user_id)
        assert chief["distance_km"] <= test_alert.radius
        location = chief["location"]
        assert location["latitude"] < test_alert.latitude + 0.0005
        assert location["latitude"] > test_alert.latitude - 0.0005
        assert location["longitude"] < test_alert.longitude + 0.0005
        assert location["longitude"] > test_alert.longitude - 0.0005
    assert len(closest_chiefs) == 3  # only the other 3 chiefs

async def test_get_closest_chiefs_and_nearby_users_no_redis_data(redis_session, test_alert, test_request_info):
    # We check that the function returns empty lists if there is no data in Redis
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    assert len(closest_chiefs) == 0
    assert len(nearby_users) == 0

async def test_get_closest_chiefs_and_nearby_users_many_records(redis_session, test_alert, test_request_info):
    # We insert many chief locations and user locations in Redis, around the alert
    # For convenience, we set the same nearby location for all chiefs and users, within the alert radius
    user_location = (test_alert.latitude + 0.0001, test_alert.longitude + 0.0001)
    chief_location = user_location
    for i in range(200):
        chief_id = f"chief_{i}"
        # For convenience, we set the same nearby location for all chiefs, within the alert radius
        chief_locations_key = get_redis_chief_locations_key(chief_id)
        last_updates_key = get_redis_location_last_updates_key(chief_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(chief_locations_key, (chief_location[1], chief_location[0], chief_id))
        await redis_session.zadd(last_updates_key, {chief_id: now_int_ts})
    for i in range(200, 3000):
        user_id = f"user_{i}"
        # For convenience, we set the same nearby location for all users
        user_locations_key = get_redis_user_locations_key(user_id)
        last_updates_key = get_redis_location_last_updates_key(user_id)
        now_int_ts = int(now_tz_aware().timestamp())
        await redis_session.geoadd(user_locations_key, (user_location[1], user_location[0], user_id))
        await redis_session.zadd(last_updates_key, {user_id: now_int_ts})
    # We assert that the distance between the nearby location and the alert location is less than the radius
    alert_coords = (test_alert.latitude, test_alert.longitude)
    distance = haversine(alert_coords, user_location, unit=Unit.KILOMETERS)
    assert distance <= test_alert.radius
    # Now we call the function to get the closest chiefs and nearby users
    redis_engine = redis_session # Redis session is a fake Redis engine in test mode
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    # We check that the function returns only the chiefs and users within the alert radius, even if there are many records in Redis
    for chief in closest_chiefs:
        assert chief["distance_km"] <= test_alert.radius
        location = chief["location"]
        assert round(location["latitude"], 4) == round(chief_location[0], 4)
        assert round(location["longitude"], 4) == round(chief_location[1], 4)
    # We check that the function returns at most 100 closest chiefs (the maximum allowed), even if there are more than 100 chiefs in Redis
    assert len(closest_chiefs) == 100 
    for user in nearby_users:
        assert user["distance_km"] <= test_alert.radius
        location = user["location"]
        assert round(location["latitude"], 4) == round(user_location[0], 4)
        assert round(location["longitude"], 4) == round(user_location[1], 4)
    # We check that the function returns 1000 nearby users (the maximum allowed), even if there are more than 1000 nearby users in Redis
    assert len(nearby_users) == 1000
    # We also check that the closest chiefs are ordered by distance
    closest_chiefs_sorted_by_distance = sorted(closest_chiefs, key=lambda x: x["distance_km"])
    assert closest_chiefs == closest_chiefs_sorted_by_distance
    # We also check that the nearby users are ordered by distance
    nearby_users_sorted_by_distance = sorted(nearby_users, key=lambda x: x["distance_km"])
    assert nearby_users == nearby_users_sorted_by_distance
