# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select, delete
from models.general import (
    string_as_uuid,
    User, RefreshToken, AlertedUser
)
from services.alert_btasks import (
    get_closest_chiefs_and_nearby_users,
    save_first_chief_in_db
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically used)
    create_test_alert, # required (fixture test_alert)
    create_test_request_info, # required (fixture test_request_info)
    print_closest_chiefs_and_nearby_users
)

async def test_save_first_chief_in_db_success(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user14@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    closest_chiefs_num = len(closest_chiefs)
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    if closest_chiefs_num > 0:
        assert first_chief_fcm_token is not None
        assert first_chief is not None
        # The chief_id of the alerted user should be the same as the id of the first closest chief
        # ...because the first closest chief has an FCM token for sure and exists in the database (see tests/fixtures/alerts.py)
        assert first_chief["user_id"] == closest_chiefs[0]["user_id"]
        # Here we should have exactly one alerted user in the database, and it should be the closest chief
        # Note: in this test we are saving only the first chief and not all nearby users
        statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
        alerted_users = db_session.exec(statement).all()
        assert len(alerted_users) == 1
        assert alerted_users[0].user_id == string_as_uuid(closest_chiefs[0]["user_id"])
        assert alerted_users[0].alert_id == test_alert.id
        assert alerted_users[0].distance is not None
        assert round(alerted_users[0].distance, 1) == 0.0
        assert alerted_users[0].vote == 0  # default value
        assert alerted_users[0].closing_vote == 0  # default value
        assert alerted_users[0].is_manager == True # The first chief is the alert manager
        refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == alerted_users[0].user_id)).first()
        assert refresh_token is not None
        assert refresh_token.fcm_token == first_chief_fcm_token
    else:
        print("No closest chiefs in Redis for this test. Please retry it")
        assert first_chief_fcm_token is None
        assert first_chief is None
        return
    
async def test_save_first_chief_in_db_but_first_chief_has_wrong_uuid_in_redis(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user18@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id 
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if not closest_chiefs:
       print("No closest chiefs in Redis for this test. Please retry it")
       return
    # We simulate the wrong id of the first chief in Redis
    closest_chiefs[0]["user_id"] = "wrong_id"
    closest_chiefs_num = len(closest_chiefs)
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    if closest_chiefs_num > 1:
        assert first_chief_fcm_token is not None
        assert first_chief is not None
        # The chief_id of the alerted user should be the same as the id of the second closest chief 
        # ...because the first closest chief has a wrong id, 
        # so the function should skip it and save the second closest chief as "first chief with FCM token"
        assert first_chief["user_id"] == closest_chiefs[1]["user_id"]
        # Here we should have exactly one alerted user in the database, and it should be the closest chief
        # Note: in this test we are saving only the first chief and not all nearby users
        statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
        alerted_users = db_session.exec(statement).all()
        assert len(alerted_users) == 1
        assert alerted_users[0].user_id == string_as_uuid(closest_chiefs[1]["user_id"])
        assert alerted_users[0].alert_id == test_alert.id
        assert round(alerted_users[0].distance, 1) == 0.0
        assert alerted_users[0].vote == 0  # default value
        assert alerted_users[0].closing_vote == 0  # default value
        assert alerted_users[0].is_manager == True # The first chief is the alert manager
        refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == alerted_users[0].user_id)).first()
        assert refresh_token is not None
        assert refresh_token.fcm_token == first_chief_fcm_token
    else:
        print("Not enough closest chiefs in Redis for this test. Please retry it")
        assert first_chief_fcm_token is None
        assert first_chief is None
        return
    
async def test_save_first_chief_in_db_orphan_is_no_longer_a_chief_in_db(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user15@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if not closest_chiefs:
        print("No closest chiefs in Redis for this test. Please retry it")
        return
    first_chief_is_not_a_chief = closest_chiefs[0]
    # We change "is_chief" flag to simulate the case where the first closest chief is no longer a chief in the database
    # The first closest chief, in other words is an orphan chief in Redis, 
    # because in the database counterpart he is no longer a chief, so the function should skip it and save the second closest chief as "first chief with FCM token"
    first_chief_is_not_a_chief_user_id = string_as_uuid(first_chief_is_not_a_chief["user_id"])
    statement = select(User).where(User.id == first_chief_is_not_a_chief_user_id)
    chief_user = db_session.exec(statement).first()
    assert chief_user is not None
    assert chief_user.is_chief == True # Before the change it was a chief in database
    chief_user.is_chief = False # But now, is no longer a chief in database
    db_session.add(chief_user)
    db_session.commit()
    closest_chiefs_num = len(closest_chiefs)
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    if closest_chiefs_num > 1: # We need at least 2 closest chiefs in Redis for this test, because the first closest chief is no longer a chief in the database and cannot be taken as "first chief with FCM token"
        assert first_chief_fcm_token is not None
        assert first_chief is not None
        # The chief_id of the alerted user should be the same as the id of the second closest chief 
        # ...because the first closest chief is no longer a chief in database), 
        # so the function should skip it and save the second closest chief as the first chief with FCM token
        assert first_chief["user_id"] == closest_chiefs[1]["user_id"]
        # Here we should have exactly one alerted user in the database, and it should be the closest chief
        # Note: in this test we are saving only the first chief and not all nearby users
        statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
        alerted_users = db_session.exec(statement).all()
        assert len(alerted_users) == 1
        assert alerted_users[0].user_id == string_as_uuid(closest_chiefs[1]["user_id"])
        assert round(alerted_users[0].distance, 1) == 0.0
        assert alerted_users[0].alert_id == test_alert.id
        assert alerted_users[0].vote == 0  # default value
        assert alerted_users[0].closing_vote == 0  # default value
        assert alerted_users[0].is_manager == True # The first chief is the alert manager
        refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == alerted_users[0].user_id)).first()
        assert refresh_token is not None
        assert refresh_token.fcm_token == first_chief_fcm_token
    else:
        print("Not enough closest chiefs in Redis for this test. Please retry it")
        assert first_chief_fcm_token is None
        assert first_chief is None
        return

async def test_save_first_chief_in_db_found_orphan_with_no_fcm_token(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user15@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if not closest_chiefs:
        print("No closest chiefs in Redis for this test. Please retry it")
        return
    first_chief_without_fcm_token = closest_chiefs[0]
    # We delete the FCM token of this chief to simulate the case where the first closest chief has no FCM token in the database
    # The first closest chief, in other words is an orphan chief in Redis, 
    # because in the database counterpart he has no FCM token, so the function should skip it and save the second closest chief as "first chief with FCM token"
    first_chief_without_fcm_token_user_id = string_as_uuid(first_chief_without_fcm_token["user_id"])
    refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == first_chief_without_fcm_token_user_id)).first()
    refresh_token.fcm_token = None
    db_session.add(refresh_token)
    db_session.commit()
    closest_chiefs_num = len(closest_chiefs)
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    if closest_chiefs_num > 1: # We need at least 2 closest chiefs in Redis for this test, because the first closest chief has no FCM token in the database and cannot be taken as "first chief"
        assert first_chief_fcm_token is not None
        assert first_chief is not None
        # The chief_id of the alerted user should be the same as the id of the second closest chief 
        # ...because the first closest chief has not FCM token in database), 
        # so the function should skip it and save the second closest chief as the first chief with FCM token
        assert first_chief["user_id"] == closest_chiefs[1]["user_id"]
        # Here we should have exactly one alerted user in the database, and it should be the closest chief
        # Note: in this test we are saving only the first chief and not all nearby users
        statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
        alerted_users = db_session.exec(statement).all()
        assert len(alerted_users) == 1
        assert alerted_users[0].user_id == string_as_uuid(closest_chiefs[1]["user_id"])
        assert alerted_users[0].alert_id == test_alert.id
        assert round(alerted_users[0].distance, 1) == 0.0
        assert alerted_users[0].vote == 0  # default value
        assert alerted_users[0].closing_vote == 0  # default value
        assert alerted_users[0].is_manager == True # The first chief is the alert manager
        refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == alerted_users[0].user_id)).first()
        assert refresh_token is not None
        assert refresh_token.fcm_token == first_chief_fcm_token
    else:
        print("Not enough closest chiefs in Redis for this test. Please retry it")
        assert first_chief_fcm_token is None
        assert first_chief is None
        return

async def test_save_first_chief_in_db_3_orphan_chiefs_deleted_from_db(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user16@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if (not closest_chiefs) or (len(closest_chiefs) < 4):
        print("Not enough closest chiefs in Redis for this test. Please retry it")
        return
    # Now we delete the first 3 closest chiefs in the database, 
    # but we keep them in Redis (so they become "orphan chiefs" in Redis, because they exist in Redis, but they don't exist in the database).
    # For this reason, the function should skip these 3 chiefs and save the 4th closest chief as "first chief with FCM token"
    for i in range(3):
        chief_deleted = closest_chiefs[i]
        chief_deleted_user_id = string_as_uuid(chief_deleted["user_id"])
        # We delete the refresh token of the user and the user itself
        statement = delete(RefreshToken).where(RefreshToken.user_id==chief_deleted_user_id) # type:ignore
        db_session.exec(statement)
        statement = delete(User).where(User.id==chief_deleted_user_id) # type:ignore
        db_session.exec(statement)
    db_session.commit()
    closest_chiefs_num = len(closest_chiefs)
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    if closest_chiefs_num > 3: # We need at least 4 closest chiefs in Redis for this test, because the first 3 are "orphan chiefs" in Redis (they don't exist in database), so the function should skip them and save the 4th closest chief as "first chief with FCM token"
        assert first_chief_fcm_token is not None
        assert first_chief is not None
        # The chief_id of the alerted user should be the same as the id of the fourth closest chief 
        # ...because the first three closest chiefs have been deleted from the database (they are "orphan chiefs" in Redis), 
        # so the function should skip them and save the fourth closest chief as "first chief with FCM token"
        assert first_chief["user_id"] == closest_chiefs[3]["user_id"]
        # Here we should have exactly one alerted user in the database, and it should be the closest chief
        # Note: in this test we are saving only the first chief and not all nearby users
        statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
        alerted_users = db_session.exec(statement).all()
        assert len(alerted_users) == 1
        assert alerted_users[0].user_id == string_as_uuid(closest_chiefs[3]["user_id"])
        assert alerted_users[0].alert_id == test_alert.id
        assert alerted_users[0].vote == 0  # default value
        assert alerted_users[0].closing_vote == 0  # default value
        assert alerted_users[0].is_manager == True # The first chief is the alert manager
        refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == alerted_users[0].user_id)).first()
        assert refresh_token is not None
        assert refresh_token.fcm_token == first_chief_fcm_token
    else:
        print("Not enough closest chiefs in Redis for this test. Please retry it")
        assert first_chief_fcm_token is None
        assert first_chief is None
        return

async def test_save_first_chief_in_db_all_orphan_chiefs_deleted_from_db(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user17@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # Redis session is a fake Redis engine for testing mode
    redis_engine = redis_session
    # We get closest chiefs and nearby users from Redis
    closest_chiefs, nearby_users = await get_closest_chiefs_and_nearby_users(test_alert, test_request_info, redis_engine)
    print_closest_chiefs_and_nearby_users(test_alert, user, closest_chiefs, nearby_users)
    if not closest_chiefs:
        print("No closest chiefs in Redis for this test. Please retry it")
        return
    # Now we delete all closest chiefs in the database, but in Redis we keep them (so they become "orphan chiefs" in Redis, because they exist in Redis, but they don't exist in the database).
    # For this reason, the function should skip all chiefs and return None for the first chief and its FCM token, because there are no chiefs with FCM token in the database
    for chief in closest_chiefs:
        chief_user_id = string_as_uuid(chief['user_id'])
        # We delete the refresh token of the user and the user itself
        statement = delete(RefreshToken).where(RefreshToken.user_id==chief_user_id) # type:ignore
        db_session.exec(statement)
        statement = delete(User).where(User.id==chief_user_id) # type:ignore
        db_session.exec(statement)
    db_session.commit()
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    assert first_chief_fcm_token is None
    assert first_chief is None
    # In the database, there will be no alerted manager (no first chief) for this alert, because the function should not save any chief in the database
    statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)
    alerted_users = db_session.exec(statement).all()
    # Note: here we have no alerted chief in the database, because the function should skip all chiefs in Redis (because they are all "orphan chiefs", so they don't exist in the database)
    # Note: there are not nearby alerted users, because we are not saving nearby users in the database in this test
    assert len(alerted_users) == 0

def test_save_first_chief_in_db_no_closest_chief_in_redis(db_session, redis_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # Now we select a user from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "user18@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id 
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # We set closest chiefs as an empty list, to simulate the case where there are no closest chiefs in Redis for this alert
    closest_chiefs = []
    assert len(closest_chiefs) == 0
    # The function has no effect when there are no closest chiefs in Redis
    first_chief, first_chief_fcm_token = save_first_chief_in_db(test_alert, closest_chiefs, test_request_info, db_session)
    assert first_chief_fcm_token is None
    assert first_chief is None
