# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select
from models.general import (
    User, RefreshToken, AlertedUser
)
from services.alert_btasks import (
    get_zone_users,
    save_zone_users_in_db
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically used)
    create_test_alert, # required (fixture test_alert)
    create_test_request_info, # required (fixture test_request_info)
    print_zone_users
)

# The function "save_zone_users_in_db" is used by the alert expansion background task to add in the database (as "alerted users") all nearby users or specialists found in Redis.
# This function calls "save_nearby_users_in_db" (see services.alert_btasks module) with proper arguments to add nearby users or specialists in the database in expansion mode.

async def test_save_zone_users_in_db_success(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user105@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis engine is equal to redis session in testing mode (in testing mode we use FakeRedis)
    redis_engine = redis_session
    # We get zone users from Redis, with radius None, so the function will use the alert radius, 
    # and role None, so the function will get all nearby users, not specialists.
    zone_users = await get_zone_users(test_alert, None, None, test_request_info, redis_engine)
    print_zone_users(test_alert, user, zone_users)
    zone_users_num = len(zone_users)
    # We call the save_zone_users_in_db function with None role to save the zone users in the database as alerted users
    fcm_tokens_map = save_zone_users_in_db(test_alert, zone_users, None, test_request_info, db_session)
    if zone_users_num == 0:
        print("No nearby users in Redis for this test. Please retry it") 
        assert len(fcm_tokens_map) == 0
        return
    else:
        assert len(fcm_tokens_map) > 0
        assert len(fcm_tokens_map) == zone_users_num
        # The user_id of the alerted users should be the same as the user_id of the zone users in Redis
        # ...because all zone_users have an FCM token for sure, and they exist in the database (see tests/fixtures/alerts.py)
        # Here we should have exactly n alerted_users (n=zone_users_num) in the database
        statement = (select(AlertedUser, RefreshToken.fcm_token)
            .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
            .where(AlertedUser.alert_id == test_alert.id)
        )
        results = db_session.exec(statement).all()
        assert len(results) == zone_users_num
        for alerted_user, fcm_token in results:
            assert str(alerted_user.user_id) in fcm_tokens_map
            assert alerted_user.alert_id == test_alert.id
            assert alerted_user.vote == 0  # default value
            assert alerted_user.distance is not None
            assert alerted_user.distance >= 0.0
            assert alerted_user.closing_vote == 0  # default value
            assert alerted_user.is_manager == False  # default value for nearby users
            assert fcm_token == fcm_tokens_map[str(alerted_user.user_id)]
    # Now we try to increase the radius of get_zone_users function
    # and we assert that the save_zone_users_in_db function add to database only non-existing alerted users
    radius = 100 # 100 km
    zone_users = await get_zone_users(test_alert, radius, None, test_request_info, redis_engine)
    zone_users_num = len(zone_users)
    # We call the save_zone_users_in_db function with None role to save the zone users in the database as alerted users
    # Zone users list contains all users within 100 km radius, 
    # but Fcm tokens map contains only the new alerted users added to the database, not the existing one.
    fcm_tokens_map = save_zone_users_in_db(test_alert, zone_users, None, test_request_info, db_session)
    if zone_users_num == 0:
        print("No new zone users in Redis to add as alerted users for this test") 
        assert len(fcm_tokens_map) == 0
        return
    else:
        assert len(fcm_tokens_map) > 0
        # The number of new alerted users added to the database should be less than the total number of zone users, 
        # because some of them were already added in the previous call to save_zone_users_in_db
        assert len(fcm_tokens_map) < zone_users_num
