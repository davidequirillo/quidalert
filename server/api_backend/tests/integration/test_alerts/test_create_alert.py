# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timedelta
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception
)
from models.general import User, Alert, AlertType, AlertedUser
from services.security import now_tz_naive
from tests.fixtures.alerts import setup_data_and_teardown, setup_fake_functions

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
    # We try a radius of 0, which is invalid
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
    assert response.json() == {"message": "Alert created, no need to search for nearby users or chiefs to notify"}
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
    assert response.json() == {"message": "Alert created, no need to search for nearby users or chiefs to notify"}
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
    # But the alert user (the sender, the chief) is added as "manager"
    # We verity it
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
        "description": "My test alert very similar", # similar description (similarity should be 100)
        "latitude": 40.005, # close to the existing alert (less than 1 km away)
        "longitude": -105.005 # close to the existing alert (less than 1 km away)
    }
    response = client.post(
        "/api/alert", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    
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
    assert response.json()["message"] == "Similar alert already exists"
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
