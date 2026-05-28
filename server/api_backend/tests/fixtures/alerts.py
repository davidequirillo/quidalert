# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
import asyncio
import pytest
from scripts.seed_redis_data import (
    DENVER_LAT, 
    DENVER_LON,
    GPS_PROBABILITY,
    get_random_coords
)
from sqlmodel import delete, select
from models.general import (
    User, UserRole, UserLanguage,
    Alert, AlertType
)
from services.security import now_tz_naive, now_tz_aware
from core.dbmgr import (
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key,
)

RADIUS = 5  # Radius in kilometers for random location generation around Denver

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
        role=UserRole.citizen.value,
        language=UserLanguage.en.value
    )
    db_session.add(superuser)
    db_session.commit()
    # Create 100 normal users with random roles
    for i in range(100):
        user = User(
            email=f"user{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Firstname{i}",
            surname=f"Surname{i}",
            is_active=True,
            role=roles[i % len(roles)],
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
            role=UserRole.citizen.value,
            language=UserLanguage.en.value,
            authorized_by=superuser.email,
            authorized_at=now_tz_naive()
        )
        db_session.add(chief)
    db_session.commit()

async def assign_redis_data_to_users(db_session, redis_session):
    users = db_session.exec(select(User)).all()
    now_int_ts = int(now_tz_aware().timestamp())
    at_least_one_chief_has_gps = False
    for user in users:
        if (random.random() < GPS_PROBABILITY) or (
            user.is_chief and (at_least_one_chief_has_gps == False)
        ):
            lat, lon = get_random_coords(DENVER_LAT, DENVER_LON, RADIUS)
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
                await pipe.execute()

@pytest.fixture(autouse=True)
def setup_fake_functions(mocker):
    def fake_notify_nearby_users(alert, user_ids, fcm_tokens, message: str, request_info, db_engine):
        return len(user_ids)
    notify_sender_mocked = mocker.patch("services.alert_btasks.notify_sender", return_value=True)
    notify_chief_mocked = mocker.patch("services.alert_btasks.notify_chief", return_value=True)
    notify_nearby_users_mocked = mocker.patch("services.alert_btasks.notify_nearby_users", side_effect=fake_notify_nearby_users)
    yield {
        "mock_notify_sender": notify_sender_mocked,
        "mock_notify_chief": notify_chief_mocked,
        "mock_notify_nearby_users": notify_nearby_users_mocked
    }

@pytest.fixture(autouse=True)
def setup_users_data_and_teardown(db_session, redis_session):
    create_test_users(db_session)
    # Assign GPS location data to users in Redis
    asyncio.run(assign_redis_data_to_users(db_session, redis_session))
    yield
    # Teardown: flush Redis and delete users from the database
    asyncio.run(redis_session.flushall())
    db_session.exec(delete(User))
    db_session.commit()

@pytest.fixture(name="test_alert")
def create_test_alert(db_session, test_baseuser):
    user: User = test_baseuser["user"]
    alert = Alert(
        type=AlertType.local.value,
        description="Test alert description",
        user_id=user.id,
        latitude=DENVER_LAT,
        longitude=DENVER_LON,
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
