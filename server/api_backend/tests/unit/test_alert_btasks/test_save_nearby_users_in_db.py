# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select, delete
from models.general import (
    string_as_uuid,
    User, RefreshToken, AlertedUser
)
from services.alert_btasks import (
    get_closest_chiefs_and_nearby_users,
    save_nearby_users_in_db_and_get_fcm_tokens
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown,
    create_test_alert,
    create_test_request_info,
    print_alert_coordinates_and_nearby_users
)

async def test_save_nearby_users_in_db_success(db_session, redis_session, test_alert, test_request_info):
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
    db_engine = db_session.get_bind()
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_alert_coordinates_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    nearby_users_num = len(nearby_users)
    fcm_tokens_map = save_nearby_users_in_db_and_get_fcm_tokens(test_alert, nearby_users, test_request_info, db_engine)
    if nearby_users_num == 0:
        print("No nearby users in Redis for this test. Please retry it") 
        assert len(fcm_tokens_map) == 0
        return
    else:
        assert len(fcm_tokens_map) > 0
        assert len(fcm_tokens_map) == nearby_users_num
        # The user_id of the alerted users should be the same as the user_id of the nearby users in Redis
        # ...because all nearby_users have an FCM token for sure, and they exist in the database (see tests/fixtures/alerts.py)
        # Here we should have exactly n alerted_users (n=nearby_users_num) in the database
        # Note: in this test we are saving only the nearby users as alerted users in the database, and not the closest chief (the alert manager)
        statement = (select(AlertedUser, RefreshToken.fcm_token)
            .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
            .where(AlertedUser.alert_id == test_alert.id)
        )
        results = db_session.exec(statement).all()
        assert len(results) == nearby_users_num
        for alerted_user, fcm_token in results:
            assert str(alerted_user.user_id) in fcm_tokens_map
            assert alerted_user.alert_id == test_alert.id
            assert alerted_user.vote == 0  # default value
            assert alerted_user.closing_vote == 0  # default value
            assert alerted_user.is_manager == False  # default value for nearby users
            assert fcm_token == fcm_tokens_map[str(alerted_user.user_id)]

async def test_save_nearby_users_in_db_some_having_wrong_id(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user106@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    db_engine = db_session.get_bind()
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_alert_coordinates_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    # We intentionally add 2 nearby users with wrong user_id (not existing in the database) to test that the function handles them correctly
    nearby_users.append({"user_id": "wrong_id_1", "distance_km": 1.0})
    nearby_users.append({"user_id": "wrong_id_2", "distance_km": 2.0})
    nearby_users_num = len(nearby_users)
    fcm_tokens_map = save_nearby_users_in_db_and_get_fcm_tokens(test_alert, nearby_users, test_request_info, db_engine)
    if nearby_users_num == 2:
        print("No nearby users in Redis for this test (only the 2 with wrong ids). Please retry it") 
        assert len(fcm_tokens_map) == 0
        return
    else:
        assert len(fcm_tokens_map) > 0
        assert len(fcm_tokens_map) == (nearby_users_num - 2)  # we should have 2 less FCM tokens than nearby users, because of the 2 with wrong ids
        # The user_id of the alerted users should be the same as the user_id of the nearby users in Redis (except for the 2 with wrong ids, which should be ignored)
        # ...because all nearby_users with correct ids have an FCM token for sure, and they exist in the database (see tests/fixtures/alerts.py)
        # Here we should have exactly n-2 alerted_users (n=nearby_users_num) in the database, because the 2 with wrong ids should be ignored
        statement = (select(AlertedUser, RefreshToken.fcm_token)
            .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
            .where(AlertedUser.alert_id == test_alert.id)
        )
        results = db_session.exec(statement).all()
        assert len(results) == (nearby_users_num - 2)
        for alerted_user, fcm_token in results:
            assert str(alerted_user.user_id) in fcm_tokens_map
            assert alerted_user.alert_id == test_alert.id
            assert alerted_user.vote == 0  # default value
            assert alerted_user.closing_vote == 0  # default value
            assert alerted_user.is_manager == False  # default value for nearby users
            assert fcm_token == fcm_tokens_map[str(alerted_user.user_id)]

async def test_save_nearby_users_some_orphans_with_null_fcm_tokens(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user107@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    db_engine = db_session.get_bind()
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    nearby_users_num = len(nearby_users)
    print_alert_coordinates_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if nearby_users_num < 2:
        print("Not enough nearby users in Redis for this test. Please retry it") 
        return
    # We delete intentionally some FCM tokens from the nearby users in database, to create some "orphan" nearby users with null FCM tokens, to test that the function handles them correctly
    user1_without_fcm_token = nearby_users[0]
    user2_without_fcm_token = nearby_users[1]
    user1_id = string_as_uuid(user1_without_fcm_token["user_id"])
    user2_id = string_as_uuid(user2_without_fcm_token["user_id"])
    statement = select(User).where((User.id == user1_id) | (User.id == user2_id))
    nearby_users_in_db_with_null_fcm = db_session.exec(statement).all()
    for nearby_user in nearby_users_in_db_with_null_fcm:
        statement = select(RefreshToken).where(RefreshToken.user_id == nearby_user.id)
        refresh_token = db_session.exec(statement).first()
        if refresh_token is not None:
            refresh_token.fcm_token = None
            db_session.add(refresh_token)
    db_session.commit()
    # We check that the function save as alerted users only nearby users with valid FCM tokens in the database, and ignores the ones with null FCM tokens (the "orphans")
    fcm_tokens_map = save_nearby_users_in_db_and_get_fcm_tokens(test_alert, nearby_users, test_request_info, db_engine)
    assert len(fcm_tokens_map) == (nearby_users_num - 2)
    # Here we should have exactly n-2 alerted_users (n=nearby_users_num) in the database, because the 2 with null FCM tokens should be ignored
    statement = (select(AlertedUser, RefreshToken.fcm_token)
        .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
        .where(AlertedUser.alert_id == test_alert.id)
    )
    results = db_session.exec(statement).all()
    assert len(results) == (nearby_users_num - 2)
    for alerted_user, fcm_token in results:
        assert str(alerted_user.user_id) in fcm_tokens_map
        assert alerted_user.alert_id == test_alert.id
        assert alerted_user.vote == 0  # default value
        assert alerted_user.closing_vote == 0  # default value
        assert alerted_user.is_manager == False  # default value for nearby users
        assert fcm_token == fcm_tokens_map[str(alerted_user.user_id)]

async def test_save_nearby_users_some_orphans_deleted_in_db(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user108@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    db_engine = db_session.get_bind()
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    nearby_users_num = len(nearby_users)
    print_alert_coordinates_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if nearby_users_num < 3:
        print("Not enough nearby users in Redis for this test. Please retry it") 
        return
    # We delete intentionally some nearby users in database, to create some "orphan" nearby users, to test that the function handles them correctly
    user1_orphan = nearby_users[0]
    user2_orphan = nearby_users[1]
    user3_orphan = nearby_users[2]
    user1_id = string_as_uuid(user1_orphan["user_id"])
    user2_id = string_as_uuid(user2_orphan["user_id"])
    user3_id = string_as_uuid(user3_orphan["user_id"])
    # We delete refreshtokens of the 3 nearby users from the database
    statement = delete(RefreshToken).where((RefreshToken.user_id == user1_id) | (RefreshToken.user_id == user2_id) | (RefreshToken.user_id == user3_id)) # type:ignore
    db_session.exec(statement)
    # We delete the 3 nearby users from the database
    statement = delete(User).where((User.id == user1_id) | (User.id == user2_id) | (User.id == user3_id)) # type:ignore
    db_session.exec(statement)
    db_session.commit()
    # We check that the function save as alerted users only nearby users existing in the database, and ignores the "orphans"
    fcm_tokens_map = save_nearby_users_in_db_and_get_fcm_tokens(test_alert, nearby_users, test_request_info, db_engine)
    assert len(fcm_tokens_map) == (nearby_users_num - 3)
    # Here we should have exactly n-3 alerted_users (n=nearby_users_num) in the database, because the 3 "orphans" should be ignored
    statement = (select(AlertedUser, RefreshToken.fcm_token)    
        .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
        .where(AlertedUser.alert_id == test_alert.id)
    )
    results = db_session.exec(statement).all()
    assert len(results) == (nearby_users_num - 3)
    for alerted_user, fcm_token in results:
        assert str(alerted_user.user_id) in fcm_tokens_map
        assert alerted_user.alert_id == test_alert.id
        assert alerted_user.vote == 0  # default value
        assert alerted_user.closing_vote == 0  # default value
        assert alerted_user.is_manager == False  # default value for nearby users
        assert fcm_token == fcm_tokens_map[str(alerted_user.user_id)]

def test_save_nearby_users_in_db_no_nearby_users(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user109@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    db_engine = db_session.get_bind()
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We simulate the case with no nearby users in Redis
    nearby_users = []
    nearby_users_num = len(nearby_users)
    assert nearby_users_num == 0
    fcm_tokens_map = save_nearby_users_in_db_and_get_fcm_tokens(test_alert, nearby_users, test_request_info, db_engine)
    assert len(fcm_tokens_map) == 0
    # Here we should have 0 alerted_users in the database, because there are no nearby users
    statement = (select(AlertedUser, RefreshToken.fcm_token)
        .join(RefreshToken, AlertedUser.user_id == RefreshToken.user_id) # type:ignore
        .where(AlertedUser.alert_id == test_alert.id)
    )
    results = db_session.exec(statement).all()
    assert len(results) == 0
