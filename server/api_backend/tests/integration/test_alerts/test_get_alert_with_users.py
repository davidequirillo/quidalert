# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from fastapi import status
from sqlmodel import select, delete
from core.exceptions import (
    not_found_exception,
    token_not_valid_exception,
    forbidden_exception
)
from models.general import (
    string_as_uuid,
    User, Alert, AlertType, AlertedUser
)
from services.security import now_tz_naive
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
)

def test_get_alert_with_users_missing_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(f"/api/alert/users/{alert_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_alert_not_authorized_invalid_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_alert_with_users_forbidden(client, db_session, test_baseuser):
    baseuser: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    statement = select(Alert).where(Alert.user_id == baseuser.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # There is at least one local alert created by test_baseuser (see setup_alerts_data_and_teardown fixture)
    # Theorically he can view alert created by himself, but in this case not,
    # because this endpoint is useful to see additional info (like alerted users personal info and their votes),
    # and this is only allowed to chiefs (and admins), not to base users
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alert_with_users_forbidden_officer(client, db_session, test_officer):
    officer: User = test_officer['user']
    access_token = test_officer['access_token']
    statement = select(Alert).where(Alert.user_id == officer.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # There is at least one local alert created by test_officer (see setup_alerts_data_and_teardown fixture)
    # Theorically he can view alert created by himself, but in this case not,
    # because this endpoint is useful to see additional info (like alerted users personal info and their votes),
    # and this is only allowed to chiefs (and admins), not to officers
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alert_with_users_not_found(client, db_session, test_chief):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    # Use a non-existing alert_id (assuming 111111 does not exist)
    alert_id = 111111
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception("Alert not found").status_code
    assert "not found" in response.json()["detail"]
    # The same result should be obtained if the alert is present
    # but the relative user is not found.
    # We simulate this by deleting the user_id of an existing alert
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    # Delete the user associated with this alert
    statement = delete(User).where(User.id == alert.user_id)
    db_session.exec(statement)
    db_session.commit()
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception("Alert not found").status_code
    assert "not found" in response.json()["detail"]

def test_get_alert_with_users_success(client, db_session, test_chief):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    statement = select(Alert)
    # We take a random alert local alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0, "No alerts found in the database for testing"
    alert = random.choice(alerts)
    assert alert is not None
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    alert_sender = db_session.exec(select(User).where(User.id == alert.user_id)).first()
    votes_map = {}
    for alerted_user in alerted_users:
        votes_map[str(alerted_user.user_id)] = alerted_user
    # We call the endpoint to get the alert with users 
    # and we check that the results are the same as the ones in the database
    alert_id = alert.id
    response = client.get(
        f"/api/alert/users/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["alert"]["id"] == alert.id
    assert "user_id" not in data["alert"], "user_id should not be present in the alert data"
    assert data["alert"]["type"] == alert.type
    assert data["alert"]["description"] == alert.description
    assert data["alert"]["created_at"] == alert.created_at.isoformat()
    assert data["sender"]["id"] == str(alert_sender.id)
    assert data["sender"]["firstname"] == alert_sender.firstname
    assert data["sender"]["surname"] == alert_sender.surname
    assert data["sender"]["email"] == alert_sender.email
    assert data["sender"]["role"] == alert_sender.role
    assert data["sender"]["reliability_score"] == alert_sender.reliability_score
    assert "password" not in data["sender"], "password should not be present in the sender data"
    assert "password_hash" not in data["sender"], "password_hash should not be present in the sender data"
    assert "activation_code" not in data["sender"], "activation_code should not be present in the sender data"
    for au in data["users"]:
        user_id = str(au["id"])
        assert "password_hash" not in au, "password_hash should not be present in the alerted user data"
        assert "activation_code" not in au, "activation_code should not be present in the alerted user data"
        assert user_id in votes_map, f"Alerted user {user_id} not found in database"
        
