# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
import asyncio
import pytest
from scripts.seed_redis_data import (
    CENTER_LAT, 
    CENTER_LON,
    get_random_coords
)
from sqlmodel import delete, select
from models.general import (
    User, UserRole, RefreshToken, UserLanguage,
    Alert, AlertType, AlertedUser, Message
)
from services.security import now_tz_naive, now_tz_aware
from core.dbmgr import (
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key,
    get_redis_spec_locations_key,
    get_redis_spec_location_last_updates_key
)

GPS_PROBABILITY = 0.90  # 90% of users have GPS enabled
ROLE_PROBABILITY = 0.10  # 10% of users have a role assigned (the rest have role equal to None)
RADIUS_KM = 5  # Radius in kilometers for random location generation around the central point (CENTER_LAT, CENTER_LON) for testing purposes

def print_closest_chiefs_and_nearby_users(alert, user, closest_chiefs, nearby_users):
    # Print alert coordinates, closest chiefs and nearby users for debugging purposes
    print()
    print(f"Test alert ID: {alert.id}")
    print(f"Alert sender: ID {alert.user_id} email {user.email}")
    print(f"Alert coordinates: ({alert.latitude}, {alert.longitude})")
    for chief in closest_chiefs:
        print(f"Closest chief: {chief['user_id']} at distance {chief['distance_km']} km")
    for nearby_user in nearby_users:
        print(f"Nearby user: {nearby_user['user_id']} at distance {nearby_user['distance_km']} km")

def print_zone_users(alert, user, nearby_users):
    # Print alert coordinates and users in the zone (nearby users) for debugging purposes
    print()
    print(f"Test alert ID: {alert.id}")
    print(f"Alert sender: ID {alert.user_id} email {user.email}")
    print(f"Alert coordinates: ({alert.latitude}, {alert.longitude})")
    for nearby_user in nearby_users:
        print(f"Zone users: {nearby_user['user_id']} at distance {nearby_user['distance_km']} km")

def print_zone_specialists(alert, user, zone_specialists):
    # Print alert coordinates and specialists in the zone for debugging purposes
    # Specialists are users with a role assigned (not None)
    print()
    print(f"Test alert ID: {alert.id}")
    print(f"Alert sender: ID {alert.user_id} email {user.email}")
    print(f"Alert coordinates: ({alert.latitude}, {alert.longitude})")
    for specialist in zone_specialists:
        print(f"Specialist in the zone: {specialist['user_id']} at distance {specialist['distance_km']} km")

def create_test_users(db_session):
    roles = [r.value for r in UserRole]
    languages = [l.value for l in UserLanguage]
    # Create a superuser (he is an admin with all permissions)
    superuser = User(
        email="superuser@example.com",
        password_hash="hashed_password",
        firstname="Super",
        surname="User",
        is_active=True,
        is_superuser=True,
        is_admin=True,
        role=None,
        language=UserLanguage.en.value
    )
    db_session.add(superuser)
    db_session.commit()
    # Create 500 normal users with random roles or role equal to None
    for i in range(500):
        user = User(
            email=f"user{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Firstname{i}",
            surname=f"Surname{i}",
            is_active=True,
            role=roles[i % len(roles)] if random.random() < ROLE_PROBABILITY else None,
            language=languages[i % len(languages)],
            authorized_by=superuser.email,
            authorized_at=now_tz_naive()
        )
        db_session.add(user)
    db_session.commit()
    # Create some chiefs
    for i in range(10):
        chief = User(
            email=f"chief{i}@example.com",
            password_hash="hashed_password",
            firstname=f"ChiefFirstname{i}",
            surname=f"ChiefSurname{i}",
            is_active=True,
            is_chief=True,
            role=None,
            language=UserLanguage.en.value,
            authorized_by=superuser.email,
            authorized_at=now_tz_naive()
        )
        db_session.add(chief)
    db_session.commit()
    users = db_session.exec(select(User)).all()
    # For each user, we assign a test FCM token
    for user in users:
        refresh_token = RefreshToken(
            user_id=user.id,
            raw_hash="hashed_token_code",
            fcm_token=f"fcm_token_for_user_{user.id}"
        )
        db_session.add(refresh_token)
    db_session.commit()

async def assign_redis_data_to_users(db_session, redis_session):
    users = db_session.exec(select(User)).all()
    now_int_ts = int(now_tz_aware().timestamp())
    at_least_one_chief_has_gps = False
    for user in users:
        if (random.random() < GPS_PROBABILITY) or (
            user.is_chief and (at_least_one_chief_has_gps == False)
        ):
            lat, lon = get_random_coords(CENTER_LAT, CENTER_LON, RADIUS_KM)
            user_id_str = str(user.id)
            chief_locations_key = get_redis_chief_locations_key(user_id_str)
            user_locations_key = get_redis_user_locations_key(user_id_str)
            last_updates_key = get_redis_location_last_updates_key(user_id_str)
            async with redis_session.pipeline(transaction=True) as pipe:
                if user.is_chief:
                    pipe.geoadd(chief_locations_key, (lon, lat, user_id_str))
                    at_least_one_chief_has_gps = True
                else:
                    pipe.geoadd(user_locations_key, (lon, lat, user_id_str)) 
                pipe.zadd(last_updates_key, {user_id_str: now_int_ts})      
                if user.role and (user.role in [r.value for r in UserRole]):
                    roleloc_key = get_redis_spec_locations_key(user_id_str, user.role)
                    role_last_upd_key = get_redis_spec_location_last_updates_key(user_id_str, user.role)
                    pipe.geoadd(roleloc_key, (lon, lat, user_id_str))
                    pipe.zadd(role_last_upd_key, {user_id_str: now_int_ts})
                await pipe.execute()

@pytest.fixture(autouse=True)
def setup_fake_functions(mocker):
    def fake_notify_nearby_users(user_ids, fcm_tokens, 
            language: str, alert: Alert, content: str, 
            request_info, db_session):
        return len(user_ids)
    def fake_notify_about_closure(user_ids, fcm_tokens, 
            language: str, alert: Alert, closing_type: str, 
            request_info, db_session):
        return len(user_ids)
    def fake_notify_nearby_users_about_expansion(user_ids, fcm_tokens,
            language: str, alert: Alert, 
            request_info, db_session):
        return len(user_ids)
    def fake_notify_on_new_message(user_ids, fcm_tokens, 
            language: str, alert: Alert, name: str, message_id: int, content: str,
            request_info, db_session):
        return len(user_ids)  
    notify_sender_mocked = mocker.patch("services.alert_btasks.notify_sender", return_value=True)
    notify_chief_manager_mocked = mocker.patch("services.alert_btasks.notify_chief_manager", return_value=True)
    notify_chief_manager_via_email_mocked = mocker.patch("services.alert_btasks.send_mail_to_chief_manager", return_value=True)
    notify_nearby_users_mocked = mocker.patch("services.alert_btasks.notify_nearby_users", side_effect=fake_notify_nearby_users)
    notify_about_closure_mocked = mocker.patch("services.alert_btasks.notify_about_closure", side_effect=fake_notify_about_closure)
    notify_sender_exp_mocked = mocker.patch("services.alert_btasks.notify_sender_about_expansion", return_value=True)
    notify_chief_manager_exp_mocked = mocker.patch("services.alert_btasks.notify_chief_manager_about_expansion", return_value=True)
    notify_nearby_users_exp_mocked = mocker.patch("services.alert_btasks.notify_nearby_users_about_expansion", side_effect=fake_notify_nearby_users_about_expansion)
    notify_on_new_message_mocked = mocker.patch("services.alert_btasks.notify_on_new_message", side_effect=fake_notify_on_new_message)

    yield {
        "mock_notify_sender": notify_sender_mocked,
        "mock_notify_chief_manager": notify_chief_manager_mocked,
        "mock_notify_chief_manager_via_email": notify_chief_manager_via_email_mocked,
        "mock_notify_nearby_users": notify_nearby_users_mocked,
        "mock_notify_about_closure": notify_about_closure_mocked,
        "mock_notify_sender_about_expansion": notify_sender_exp_mocked,
        "mock_notify_chief_manager_about_expansion": notify_chief_manager_exp_mocked,
        "mock_notify_nearby_users_about_expansion": notify_nearby_users_exp_mocked,
        "mock_notify_on_new_message": notify_on_new_message_mocked
    }

@pytest.fixture(autouse=True, name="test_alert_users_data")
def setup_users_data_and_teardown(db_session, redis_session):
    create_test_users(db_session)
    # Assign GPS location data to users in Redis
    asyncio.run(assign_redis_data_to_users(db_session, redis_session))
    yield {"users_created": True}
    # Teardown: flush Redis and delete users from the database
    asyncio.run(redis_session.flushall())
    db_session.exec(delete(RefreshToken))
    db_session.exec(delete(User))
    db_session.commit()

@pytest.fixture(name="test_alert")
def create_test_alert(db_session, test_baseuser):
    user: User = test_baseuser["user"]
    alert = Alert(
        type=AlertType.local.value,
        description="Test alert description",
        user_id=user.id,
        latitude=CENTER_LAT,
        longitude=CENTER_LON,
        radius=1
    )
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    return alert

@pytest.fixture(name="test_request_info")
def create_test_request_info():
    return {
        "client_ip": "0.0.0.0",
        "request_id": "request_id_123",
        "user_agent": "test_user_agent",
        "user_id": "test_user_id"
    }

@pytest.fixture(autouse=True)
def setup_alerts_data_and_teardown(db_session, test_alert_users_data, test_baseuser, test_chief, test_officer):
    # See setup_users_data_and_teardown fixture in this module for user creation, because we need users to create alerts
    assert test_alert_users_data.get("users_created") == True, "Users data fixture did not create users as expected"
    user: User = test_baseuser["user"]
    chief: User = test_chief["user"]
    officer: User = test_officer["user"]
    # Create 10 local alerts for a "strange" user (not the test baseuser, not the test chief)
    # We can use the test officer as a "strange" user, 
    # but anyone else could be used, for example another standart user created by the setup_users_data_and_teardown fixture
    strange_user = officer
    for i in range(0, 10):
        alert = Alert(
            type=AlertType.local.value,
            description=f"Strange user alert {i}",
            user_id=strange_user.id,  # Use the ID of the strange user
            latitude=CENTER_LAT,
            longitude=CENTER_LON,
            radius=1, 
            is_pending=False
        )
        db_session.add(alert)
    # Create some local alert for the base user
    for i in range(10, 13):
        alert = Alert(
            type=AlertType.local.value,
            description=f"Test alert {i}",
            user_id=user.id,
            latitude=CENTER_LAT,
            longitude=CENTER_LON,
            radius=1,
            is_pending=False,
        )
        db_session.add(alert)
    # Create some local alert for the chief user
    for i in range(13, 16):
        alert = Alert(
            type=AlertType.local.value,
            description=f"Chief alert {i}",
            user_id=chief.id,
            latitude=CENTER_LAT,
            longitude=CENTER_LON,
            radius=1,
            is_pending=False
        )
        db_session.add(alert)
    # Now we create some general alerts
    for i in range(16, 19):
        alert = Alert(
            type=AlertType.general.value,
            description=f"General alert {i}",
            user_id=chief.id,
            latitude=0.0,
            longitude=0.0,
            radius=1,
            is_pending=False # general alerts are not pending, because we don't have to perform background tasks for this type of alert
        )
        db_session.add(alert)
    # Now we create some empty alerts
    for i in range(19, 22):
        alert = Alert(
            type=AlertType.empty.value,
            description=f"Empty alert {i}",
            user_id=chief.id,
            latitude=CENTER_LAT,
            longitude=CENTER_LON,
            radius=1,
            is_pending=False # empty alerts are not pending, because we don't have to perform background tasks for this type of alert
        )
        db_session.add(alert)
    # Now we create some managed alerts
    for i in range(22, 25):
        alert = Alert(
            type=AlertType.managed.value,
            description=f"Managed alert {i}",
            user_id=chief.id,
            latitude=CENTER_LAT,
            longitude=CENTER_LON,
            radius=random.uniform(2,5),
            is_pending=False
        )
        db_session.add(alert)
    # We keep base users as candidates to be "alerted users" (not including test_baseuser, test_chief, or test_strange_user)
    user_candidates_stmt = select(User).where(
        User.is_chief == False, User.is_admin == False, User.is_officer == False, 
        User.id != user.id, User.id != chief.id, User.id != strange_user.id)
    user_candidates = db_session.exec(user_candidates_stmt).all()
    if len(user_candidates) == 0:
        raise Exception("No user candidates found to create alerted users for the test alerts, please check the setup_users_data_and_teardown fixture and ensure that it is imported in the test file")
    # Now we create some alerted users for the alerts created, fetching them from user candidates
    for alert in db_session.exec(select(Alert)).all():
        if (alert.type == AlertType.general.value):
            continue # generale alerts have no alerted users
        if (alert.type == AlertType.empty.value):
            continue # empty alerts have no alerted users
        for i in range(0, 15):
            user_candidate = user_candidates[i % len(user_candidates)]
            alerted_user = AlertedUser(
                alert_id=alert.id,
                user_id=user_candidate.id
            )
            db_session.add(alerted_user)
    # Now we create some alerted users for the alerts created, using the test baseuser and test chief as alerted users for some alerts
    # We will add the test baseuser as an alerted user for the first 3 alerts, and the test chief as an alerted user for the next 3 alerts
    # Note: the alerts are not created by the test baseuser or test chief (are created by the "strange" user, "test_officer"),
    # so test_baseuser and test_chief can be alerted users for these alerts
    statement = select(Alert).where(Alert.user_id != user.id, Alert.user_id != chief.id, Alert.type == AlertType.local.value)
    for i, alert in enumerate(db_session.exec(statement).all()):
        if i < 3:
            alerted_user = AlertedUser(
                alert_id=alert.id,
                user_id=user.id
            )
            db_session.add(alerted_user)
        elif i < 6:
            alerted_user = AlertedUser(
                alert_id=alert.id,
                user_id=chief.id
            )
            db_session.add(alerted_user)
    # Now we create some messages for the alerts
    statement = select(Alert)
    alerts = db_session.exec(statement).all()
    for i, alert in enumerate(alerts):
        if (alert.type == AlertType.general.value):
            continue # generale alerts have no messages
        if (alert.type == AlertType.empty.value):
            continue # empty alerts have no messages
        alerted_users_stmt = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
        alerted_users = db_session.exec(alerted_users_stmt).all()
        if len(alerted_users) == 0:
            continue # no alerted users for this alert, so we skip message creation
        for alerted_user in alerted_users:
            message_sender_id = alerted_user.user_id
            for j in range(0, 3):
                message = Message(
                    alert_id=alert.id,
                    user_id=message_sender_id,
                    content=f"Test message {j} by user {message_sender_id} for alert {alert.id}"
                )
                db_session.add(message)
                alert.messages_num += 1 # see "messages_num" field in the Alert model for details about database denormalization.
                db_session.add(alert)
    db_session.commit()
    yield {"alerts_created": True}
    db_session.exec(delete(Message))
    db_session.exec(delete(AlertedUser))
    db_session.exec(delete(Alert))
    db_session.commit()
