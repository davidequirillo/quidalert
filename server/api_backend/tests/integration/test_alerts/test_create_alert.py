# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from unittest.mock import ANY
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception
)
from models.general import RefreshToken, User, Alert, AlertType, AlertedUser
from services.security import now_tz_naive
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically used)
    setup_fake_functions, # required (fixture automatically used)
    RADIUS_KM,
)
from scripts.seed_redis_data import (
    DENVER_LAT, 
    DENVER_LON
)
from services.alert_btasks import (
    GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM,
    alert_notification_templates
)

def test_create_alert_not_authorized_missing_token(client):
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post("/api/alert", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_alert_not_authorized_invalid_token(client):
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_create_alert_invalid_alert_data(client, test_baseuser):
    access_token = test_baseuser['access_token']
    # Wrong type
    data = {
        "type": "invalid_type",
        "address": "Test address"
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Now we try with latidude out of range
    data = {
        "address": "Test address",
        "latitude": 100.0, # invalid latitude
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Now we try with longitude out of range
    data = {
        "address": "Test address",
        "latitude": 40.0,
        "longitude": 200.0, # invalid longitude
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # We try with an empty description
    data = {
        "description": "",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # We try a radius of 0, which is invalid (must be positive)
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0,
        "radius": 0.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_create_alert_by_a_user_not_reliable(client, db_session, test_baseuser):
    user = test_baseuser['user']
    access_token = test_baseuser['access_token']
    # We set the user as not reliable
    user.is_reliable = False
    db_session.add(user)
    db_session.commit()
    # The coordinates are valid, but the user is not reliable
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_create_alert_by_a_user_with_zero_reliability_score(client, db_session, test_baseuser):
    user = test_baseuser['user']
    access_token = test_baseuser['access_token']
    # We set the user reliability score to 0
    user.reliability_score = 0
    db_session.add(user)
    db_session.commit()
    # The coordinates are valid, but the user has a low reliability score
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
    # Another example with reliability score negative
    user.reliability_score = -10
    db_session.add(user)
    db_session.commit()
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_create_alert_by_a_blocked_user(client, db_session, test_baseuser):
    user = test_baseuser['user']
    access_token = test_baseuser['access_token']
    # We set the user as blocked
    user.is_blocked = True
    db_session.add(user)
    db_session.commit()
    # The coordinates are valid, but the user is blocked
    data = {
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_create_alert_special_type_called_by_user(client, test_baseuser):
    # This test checks that a user cannot create a special alert (general, empty, managed)
    # Special alerts can be created only by chiefs
    access_token = test_baseuser['access_token']
    # We try to create a "general" alert
    data = {
        "type": AlertType.general.value,
        "description": "Test alert",
        "address": "Test address"
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"].startswith("Only chiefs can create")
    # Now we try with the "empty" type
    data = {
        "type": AlertType.empty.value,
        "description": "Test alert",
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"].startswith("Only chiefs can create")
    # Now we try with the "managed" type
    data = {
        "type": AlertType.managed.value,
        "description": "Test alert",
        "address": "Test address"
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"].startswith("Only chiefs can create")

def test_create_alert_with_large_radius_called_by_user(client, test_baseuser):
    # This test checks that a regular user cannot create an alert with a radius greater than 1 km.
    access_token = test_baseuser['access_token']
    data = {
        "description": "Test alert with large radius",
        "latitude": 40.0,
        "longitude": -105.0,
        "radius": 5.0 # radius greater than 1 km
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"].startswith("Only chiefs can create")

def test_create_alert_type_general_called_by_chief(client, db_session, test_chief):
    # This test checks that a chief can create a general alert
    access_token = test_chief['access_token']
    user = test_chief['user']
    description = "Test general alert by chief"
    data = {
        "type": AlertType.general.value,
        "description": description
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    # The response for general alerts is different, because we don't search for nearby users or chiefs to notify.
    # No background tasks are triggered for this type of alert, because it's a general alert that doesn't have a specific location
    assert response.json() == {"message": f"{AlertType.general.value.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    # We check that the alert is actually created in the database
    alert = db_session.exec(select(Alert).where(Alert.description == description)).first()
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.address is None
    assert alert.description == description
    assert alert.type == AlertType.general.value
    assert alert.latitude == 0.0 # not considered for general alerts
    assert alert.longitude == 0.0 # not considered for general alerts
    assert alert.radius == 1.0 # not considered for general alerts
    # No alerted users are created
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 0

def test_create_alert_type_empty_called_by_chief(client, db_session, test_chief):
    # This test checks that a chief can create an "empty" alert
    access_token = test_chief['access_token']
    user = test_chief['user']
    description = "Test empty alert by chief"
    data = {
        "type": AlertType.empty.value,
        "description": description,
        "latitude": 40.0,
        "longitude": -105.0
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    # The response for empty alerts is different, because we don't search for nearby users or the chiefs to notify.
    # No background tasks are triggered for this type of alert, because it's an empty alert that doesn't alert nearby users, 
    # but we add the current user (chief) to the alerted users list in the database as alert manager. It will be useful.
    assert response.json() == {"message": f"{AlertType.empty.value.capitalize()} alert created, no need to search for nearby users or chiefs to notify"}
    # We check that the alert is actually created in the database
    alert = db_session.exec(select(Alert).where(Alert.description == description)).first()
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.address is None
    assert alert.description == description
    assert alert.type == AlertType.empty.value
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == 1.0 # initially set to the default
    # Nearby users are not inserted (because it's an empty alert)
    # But the alert creator (the sender, the chief) is added as "alert manager". It will be useful.
    # We verify it
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 1
    assert alerted_users[0].is_manager == True
    assert alerted_users[0].user_id == user.id
    assert alerted_users[0].alert_id == alert.id
    assert alerted_users[0].vote == 0
    assert alerted_users[0].closing_vote == 0

def test_create_alert_similar_local_exists(client, db_session, test_baseuser):
    access_token = test_baseuser['access_token']
    user = test_baseuser['user']
    # We create an alert in the database
    existing_alert = Alert(
        latitude=40.0,
        longitude=-105.0,
        user_id=user.id,
        description="Test alert",
        address="Test address",
    )
    # It's a recent alert
    existing_alert.created_at = now_tz_naive() - timedelta(hours=0.5)
    db_session.add(existing_alert)
    db_session.commit()
    # Now we try to create a similar alert with the api call
    # The coordinates are close to the existing alert (less than 1 km away)
    # The description is the same as the existing alert
    # The "created_at" of the existing alert is recent (less than 1 hour ago)
    data = {
        "description": "My test alert", # same description
        "latitude": 40.005, # close to the existing alert (less than 1 km away)
        "longitude": -105.005 # close to the existing alert (less than 1 km away)
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Similar alert already exists in the area"
    assert response.json()["similarity"] >= 50
    # Now we try with a different description, but still similar (similarity >= 50)
    data = {
        "description": "Test alert very similar", # similar description (similarity should be 100)
        "latitude": 40.005, # close to the existing alert (less than 1 km away)
        "longitude": -105.005 # close to the existing alert (less than 1 km away)
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Similar alert already exists in the area"
    assert response.json()["similarity"] >= 50

def test_create_alert_similar_general_exists(client, db_session, test_chief):
    access_token = test_chief['access_token']
    user = test_chief['user']
    # We create a general alert in the database
    existing_alert = Alert(
        user_id=user.id,
        description="Test general alert in Rome",
        type=AlertType.general.value
    )
    # We create a local alert for comparison
    local_alert = Alert(
        user_id=user.id,
        description="Test local alert in Rome",
        type=AlertType.local.value,
        latitude=41.9028,
        longitude=12.4964,
    )
    # Both alerts are recent (created less than 1 hour ago)
    local_alert.created_at = now_tz_naive() - timedelta(hours=0.25)
    existing_alert.created_at = now_tz_naive() - timedelta(hours=0.5)
    db_session.add(local_alert)
    db_session.add(existing_alert)
    db_session.commit()
    # Now we try to create a similar general alert with the api call
    data = {
        "type": AlertType.general.value,
        "description": "Test general alert in Rome city", # same description as the existing alert
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Similar general alert already exists"
    assert response.json()["similarity"] >= 90

def test_create_alert_similar_managed_exists(client, db_session, test_chief):
    access_token = test_chief['access_token']
    user = test_chief['user']
    # We create a managed alert in the database
    existing_alert = Alert(
        user_id=user.id,
        description="Test managed alert in Rome",
        type=AlertType.managed.value,
        latitude=41.9028,
        longitude=12.4964,
    )
    # The alert is recent (created less than 1 hour ago)
    existing_alert.created_at = now_tz_naive() - timedelta(hours=0.5)
    db_session.add(existing_alert)
    db_session.commit()
    # Now we try to create a similar empty alert with the api call
    data = {
        "type": AlertType.empty.value,
        "description": "Test managed alert in Rome city", # same description as the existing alert
        "latitude": 41.90285, # close to the existing alert (less than 1 km away)
        "longitude": 12.49641, # close to the existing alert (less than 1 km away)
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Similar alert already exists in the area"
    assert response.json()["similarity"] >= 50

def test_create_alert_local_no_closest_chiefs_no_nearby_users(client, db_session, test_baseuser, setup_fake_functions):
    access_token = test_baseuser['access_token']
    user: User = test_baseuser['user']
    # We assert that test_baseuser has fcm token not null
    assert user.id is not None
    assert user.is_chief == False
    statement = select(RefreshToken).where(
         RefreshToken.user_id == user.id).where(
             RefreshToken.fcm_token is not None)
    rtoken = db_session.exec(statement).first()
    assert rtoken is not None
    assert rtoken.fcm_token is not None # see conftest.py, where we set a fcm token for the logged user
    # We create an alert in a location where there are no closest chiefs and no nearby users
    description = "Test local alert with no closest chiefs and no nearby users"
    # Nearby users are searched within the alert radius
    # Closest chiefs are searched within a very big radius (GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS)
    # If we want to be sure to not find nearby users or closest chiefs, 
    # we can set the alert coordinates very far from Denver
    radius_for_closest_chiefs_in_degrees = GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM / 111
    data = {
        "description": description,
        "latitude": DENVER_LAT - radius_for_closest_chiefs_in_degrees - 10, # more than GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM km away from Denver
        "longitude": DENVER_LON + radius_for_closest_chiefs_in_degrees + 10 # more than GEOSEARCH_RADIUS_FOR_CLOSEST_CHIEFS_KM km away from Denver 
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.local.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database (1 alert should be present in this test)
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.local.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == 1.0 # set to the default radius
    assert alert.is_closed == False
    # No nearby users or chiefs should be found, so, no alerted users
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 0
    # The sender is notified with a specific message, from alert notification templates
    language = user.language if user.language in alert_notification_templates else "en"
    message = alert_notification_templates[language]["no_chief_available_no_nearby_users"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # No chief is notified, because no chief is found
    setup_fake_functions["mock_notify_chief"].assert_not_called()
    # No nearby user is notified, because no nearby user is found
    setup_fake_functions["mock_notify_nearby_users"].assert_not_called()

def test_create_alert_local_closest_chiefs_but_no_nearby_users(client, db_session, test_baseuser, setup_fake_functions):
    access_token = test_baseuser['access_token']
    user: User = test_baseuser['user']
    # We create an alert in a location where there are closest chiefs but no nearby users
    description = "Test local alert with closest chiefs but no nearby users"
    # Nearby users are searched within the alert radius
    # To simulate the absence of nearby users, we can set the alert coordinates in a location where there are no nearby users registered
    # The test users have been generated with random coordinates around Denver, inside a radius of RADIUS_KM (see tests/fixtures/alerts.py). 
    # So, if we set the alert coordinates far from Denver (more than RADIUS_KM km away), we can be sure to not find nearby users.
    radius_for_nearby_users_in_degrees = RADIUS_KM / 111
    data = {
        "description": description,
        "latitude": DENVER_LAT - (2 * radius_for_nearby_users_in_degrees) - 1, # more than RADIUS_KM km away from Denver, so that no nearby user is found
        "longitude": DENVER_LON + (2 * radius_for_nearby_users_in_degrees) + 1 # more than RADIUS_KM km away from Denver, so that no nearby user is found
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.local.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.local.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == 1.0 # set to the default radius
    assert alert.is_closed == False
    # The first chief should be found (the alert manager), from the list of closest chiefs
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 1
    assert alerted_users[0].is_manager == True
    # The sender is notified with a specific message, from alert notification templates
    language = user.language if user.language in alert_notification_templates else "en"
    message = alert_notification_templates[language]["only_chief_notified"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # The chief is notified, because a chief is found
    setup_fake_functions["mock_notify_chief"].assert_called_once_with(
        ANY, str(alerted_users[0].user_id), ANY, ANY, ANY, ANY)
    # No nearby user is notified, because no nearby user is found
    setup_fake_functions["mock_notify_nearby_users"].assert_not_called()

def test_create_alert_local_no_closest_chiefs_but_nearby_users(client, db_session, test_chief, setup_fake_functions):
    access_token = test_chief['access_token']
    user: User = test_chief['user']
    # We simulate the absence of closest chiefs
    # To obtain this result, we can delete (or demote) all chiefs from the database (except the current user, who can be a chief, or not, it doesn't matter)
    chiefs = db_session.exec(select(User).where(User.is_chief == True)).all()
    for chief in chiefs:
        if chief.id != user.id:
            chief.is_chief = False
            db_session.add(chief)
    db_session.commit()
    description = "Test local alert with no closest chiefs but nearby users"
    # Nearby users are searched within the alert radius
    # The test users have been generated with random coordinates around Denver, inside a radius of RADIUS_KM (see tests/fixtures/alerts.py).
    # To be sure to find nearby users, we set the alert location and radius to the same location and radius used to generate test users (DENVER_LAT, DENVER_LON, RADIUS_KM)
    # The caller is a chief, so there is no problem in setting the radius to RADIUS_KM, which is greater than the default radius of 1 km, because chiefs can create alerts with a radius greater than the default.
    # Note: the alert is normal (local), not managed.
    data = {
        "description": description,
        "latitude": DENVER_LAT, 
        "longitude": DENVER_LON,
        "radius": RADIUS_KM
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.local.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.local.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == data["radius"]
    assert alert.is_closed == False
    # Nearby users should be found, but no chief should be found, so, the nearby users are alerted but no chief is alerted
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) > 0
    for alerted_user in alerted_users:
        # We have no alert manager (no chief)
        assert alerted_user.is_manager == False
    language = user.language if user.language in alert_notification_templates else "en"
    # The sender is notified with a specific message, from alert notification templates
    message = alert_notification_templates[language]["no_chief_available_but_nearby_users"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # No chief is notified, because no chief is found
    setup_fake_functions["mock_notify_chief"].assert_not_called()
    # Nearby users are notified, because nearby users are found
    setup_fake_functions["mock_notify_nearby_users"].assert_called_once()
    args, _ = setup_fake_functions["mock_notify_nearby_users"].call_args
    notified_nearby_user_ids = args[1] # the second argument is the list of notified user ids
    print("Number of notified nearby user ids:", len(notified_nearby_user_ids))
    for alerted_user in alerted_users:
        assert str(alerted_user.user_id) in notified_nearby_user_ids

def test_create_local_closest_chief_and_nearby_users(client, db_session, test_chief, setup_fake_functions):
    access_token = test_chief['access_token']
    user: User = test_chief['user']
    description = "Test local alert with closest chiefs and nearby users"
    # Nearby users are searched within the alert radius
    # The test users have been generated with random coordinates around Denver, inside a radius of RADIUS_KM (see tests/fixtures/alerts.py).
    # To be sure to find nearby users, we set the alert location and radius to the same location and radius used to generate test users (DENVER_LAT, DENVER_LON, RADIUS_KM)
    # The caller is a chief, so there is no problem in setting the radius to RADIUS_KM, which is greater than the default radius of 1 km, because chiefs can create alerts with a radius greater than the default.
    # Note: the alert is normal (local), not managed.
    data = {
        "description": description,
        "latitude": DENVER_LAT, 
        "longitude": DENVER_LON,
        "radius": RADIUS_KM
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.local.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.local.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == data["radius"]
    assert alert.is_closed == False
    # The first chief should be found (the alert manager), from the list of closest chiefs, and nearby users should be found
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) > 0
    # Alerted users contain an alert manager (the first closest chief), and nearby users
    alerted_managers = [u for u in alerted_users if u.is_manager]
    alerted_nearby_users = [u for u in alerted_users if not u.is_manager]
    assert len(alerted_managers) == 1 # it's the first closest chief (alert manager)
    assert len(alerted_nearby_users) == len(alerted_users) - len(alerted_managers)
    language = user.language if user.language in alert_notification_templates else "en"
    # The sender is notified with a specific message, from alert notification templates
    message = alert_notification_templates[language]["chief_and_nearby_users_notified"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # Alert manager (the closest chief) is notified
    setup_fake_functions["mock_notify_chief"].assert_called_once()
    # Nearby users are notified
    setup_fake_functions["mock_notify_nearby_users"].assert_called_once()
    args, _ = setup_fake_functions["mock_notify_nearby_users"].call_args
    notified_nearby_user_ids = args[1] # the second argument is the list of notified user ids
    print("Number of notified nearby user ids:", len(notified_nearby_user_ids))
    for alerted_user in alerted_nearby_users:
        assert str(alerted_user.user_id) in notified_nearby_user_ids
    # ----------
    # Now we do another request to create another alert, with a radius smaller
    # ----------
    description = "Different help request with a smaller radius"
    data = {
        "description": description,
        "latitude": DENVER_LAT, 
        "longitude": DENVER_LON,
        "radius": RADIUS_KM / 2 # smaller radius, so that less nearby users are found
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.local.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database (2 alerts should be present in this test)
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 2
    alert = db_session.exec(select(Alert).where(Alert.description == description)).first()
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.local.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == data["radius"]
    assert alert.is_closed == False
    # The closest chief and nearby users should be found again, but less nearby users than the previous alert
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) > 0
    # Alerted users contain an alert manager (the first closest chief), and nearby users
    alerted_managers = [u for u in alerted_users if u.is_manager]
    new_alerted_nearby_users = [u for u in alerted_users if not u.is_manager]
    assert len(alerted_managers) == 1 # it's the first closest chief (alert manager)
    assert len(new_alerted_nearby_users) == len(alerted_users) - len(alerted_managers)
    assert len(new_alerted_nearby_users) < len(alerted_nearby_users)

def test_create_alert_managed_with_no_nearby_users(client, db_session, test_chief, setup_fake_functions):
    access_token = test_chief['access_token']
    user: User = test_chief['user']
    description = "Test managed alert with no nearby users"
    radius_for_nearby_users_in_degrees = RADIUS_KM / 111
    # We use a location far away Denver coordinates (test users are generated near Denver coordinates)
    # to be sure we will not find nearby users
    data = {
        "type": AlertType.managed.value,
        "description": description,
        "latitude": DENVER_LAT - (2 * radius_for_nearby_users_in_degrees) - 1, # more than RADIUS_KM km away from Denver, so that no nearby user is found
        "longitude": DENVER_LON + (2 * radius_for_nearby_users_in_degrees) + 1 # more than RADIUS_KM km away from Denver, so that no nearby user is found
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.managed.value.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.managed.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == 1.0 # set to the default radius
    assert alert.is_closed == False
    # No nearby users should be found, 
    # so, no alerted users (except the sender, who is added as alert manager)
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 1
    assert alerted_users[0].is_manager == True
    assert alerted_users[0].user_id == user.id
    assert alerted_users[0].alert_id == alert.id
    assert alerted_users[0].vote == 0
    assert alerted_users[0].closing_vote == 0
    # In this case the alert creator (alert sender, a chief) is also the alert manager, 
    # because the alert type is "managed"
    assert alerted_users[0].user_id == alert.user_id
    # Now we check the notifications
    language = user.language if user.language in alert_notification_templates else "en"
    # The sender is notified with a specific message, from alert notification templates
    message = alert_notification_templates[language]["no_nearby_users_available"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # No chief is notified, because it's a managed alert, and the sender (a chief) is the alert manager
    setup_fake_functions["mock_notify_chief"].assert_not_called()
    # No nearby user is notified, because no nearby user is found
    setup_fake_functions["mock_notify_nearby_users"].assert_not_called()

def test_create_alert_managed_with_nearby_users_found(client, db_session, test_chief, setup_fake_functions):
    access_token = test_chief['access_token']
    user: User = test_chief['user']
    description = "Test managed alert with nearby users"
    # Nearby users are searched within the alert radius
    # The test users have been generated with random coordinates around Denver, inside a radius of RADIUS_KM (see tests/fixtures/alerts.py).
    # To be sure to find nearby users, we set the alert location and radius to the same location and radius used to generate test users (DENVER_LAT, DENVER_LON, RADIUS_KM)
    data = {
        "type": AlertType.managed.value,
        "description": description,
        "latitude": DENVER_LAT, 
        "longitude": DENVER_LON,
        "radius": RADIUS_KM
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"].startswith(f"{AlertType.managed.capitalize()} alert created, searching for")
    # We check that the alert is actually created in the database
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    assert len(alerts) == 1
    alert = alerts[0]
    assert alert is not None
    assert alert.id is not None
    assert alert.user_id == user.id
    assert alert.type == AlertType.managed.value
    assert alert.description == description
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.radius == data["radius"]
    assert alert.is_closed == False
    # Nearby users should be found, and the closest chief is the sender (because the alert type is "managed")
    alerted_users = db_session.exec(select(AlertedUser).where(
        AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) > 0
    # Alerted users contain an alert manager (the sender, because it's a managed alert), and nearby users
    alerted_managers = [u for u in alerted_users if u.is_manager]
    alerted_nearby_users = [u for u in alerted_users if not u.is_manager]
    assert len(alerted_managers) == 1 # the sender is the alert manager
    assert alerted_managers[0].user_id == alert.user_id
    assert len(alerted_nearby_users) == len(alerted_users) - len(alerted_managers)
    language = user.language if user.language in alert_notification_templates else "en"
    # The sender is notified with a specific message, from alert notification templates
    message = alert_notification_templates[language]["nearby_users_notified"]
    setup_fake_functions["mock_notify_sender"].assert_called_once_with(
        ANY, str(user.id), ANY, message, ANY, ANY)
    # No chief is notified, because it's a managed alert, and the sender is the alert manager
    setup_fake_functions["mock_notify_chief"].assert_not_called()
    # Nearby users are notified, because nearby users are found
    setup_fake_functions["mock_notify_nearby_users"].assert_called_once()
    args, _ = setup_fake_functions["mock_notify_nearby_users"].call_args
    notified_nearby_user_ids = args[1] # the second argument is the list of notified user ids
    print("Number of notified nearby user ids:", len(notified_nearby_user_ids))
    for alerted_user in alerted_nearby_users:
        assert str(alerted_user.user_id) in notified_nearby_user_ids
