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
    User, Alert, AlertType, AlertedUser
)
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
    response = client.get(f"/api/alerts/{alert_id}/users")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_alert_not_authorized_invalid_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/users", headers={"Authorization": "Bearer invalidtoken"})
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
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
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
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alert_with_users_not_found(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # Use a non-existing alert_id (assuming 111111 does not exist)
    alert_id = 111111
    response = client.get(
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
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
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception("Alert not found").status_code
    assert "not found" in response.json()["detail"]

def test_get_alert_with_users_type_local_or_managed_success(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where((Alert.type == AlertType.local.value) | (Alert.type == AlertType.managed.value))
    # We take a random local or managed alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0
    alert = random.choice(alerts)
    assert alert is not None
    # We get the alerted users and the alert sender from the database
    # We get also users info related to the alerted users, and we build the votes map
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    # There are for sure some alerted users (see setup_alerts_data_and_teardown fixture)
    assert len(alerted_users) > 0
    alert_sender = db_session.exec(select(User).where(User.id == alert.user_id)).first()
    alerted_user_ids = [au.user_id for au in alerted_users]
    users = db_session.exec(select(User).where(User.id.in_(alerted_user_ids))).all() # type: ignore
    user_firstnames = [user.firstname for user in users]
    user_surnames = [user.surname for user in users]
    user_emails = [user.email for user in users]
    votes_map = {}
    for alerted_user in alerted_users:
        votes_map[str(alerted_user.user_id)] = alerted_user
    # We call the endpoint to get the alert with users 
    # and we check that the results are the same as the ones in the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # We check alert data against the database values, and we check that sensitive data is not present in the response
    assert data["alert"]["id"] == alert.id
    assert "user_id" not in data["alert"], "user_id should not be present in the alert data"
    assert data["alert"]["type"] == alert.type
    assert data["alert"]["description"] == alert.description
    assert data["alert"]["created_at"] == alert.created_at.isoformat()
    # We check sender data against the database values, and we check that sensitive data is not present in the response
    assert data["sender"]["id"] == str(alert_sender.id)
    assert data["sender"]["firstname"] == alert_sender.firstname
    assert data["sender"]["surname"] == alert_sender.surname
    assert data["sender"]["email"] == alert_sender.email
    assert data["sender"]["role"] == alert_sender.role
    assert data["sender"]["reliability_score"] == alert_sender.reliability_score
    assert "password" not in data["sender"], "password should not be present in the sender data"
    assert "password_hash" not in data["sender"], "password_hash should not be present in the sender data"
    assert "activation_code" not in data["sender"], "activation_code should not be present in the sender data"
    # We check users (related to alerted users) data against the database values, and we check that sensitive data is not present in the response
    for au in data["users"]:
        user_id = str(au["id"])
        assert "password" not in au, "password should not be present in the alerted user data"
        assert "password_hash" not in au, "password_hash should not be present in the alerted user data"
        assert "activation_code" not in au, "activation_code should not be present in the alerted user data"
        assert user_id in votes_map, f"Alerted user {user_id} not found in database"
        assert au["firstname"] in user_firstnames, f"Alerted user {user_id} firstname mismatch"
        assert au["surname"] in user_surnames, f"Alerted user {user_id} surname mismatch"
        assert au["email"] in user_emails, f"Alerted user {user_id} email mismatch"
    # We check votes data against the database values
    for k, v in data["votes_map"].items():
        assert k in votes_map, f"Vote for user {k} not found in database"
        assert v["vote"] == votes_map[k].vote, f"Vote for user {k} mismatch"
        assert v["closing_vote"] == votes_map[k].closing_vote, f"Closing vote for user {k} mismatch"
        assert v["is_manager"] == votes_map[k].is_manager, f"is_manager for user {k} mismatch"

def test_get_alert_with_users_type_general_or_empty_success(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where((Alert.type == AlertType.general.value) | (Alert.type == AlertType.empty.value))
    # We take a random empty or general alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0
    alert = random.choice(alerts)
    assert alert is not None
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    # There are no alerted users for general or empty alerts (see setup_alerts_data_and_teardown fixture)
    assert len(alerted_users) == 0
    alert_sender = db_session.exec(select(User).where(User.id == alert.user_id)).first()
    # We call the endpoint to get the alert with users 
    # and we check that the results are the same as the ones in the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    # We check alert data against the database values, and we check that sensitive data is not present in the response
    assert data["alert"]["id"] == alert.id
    assert "user_id" not in data["alert"], "user_id should not be present in the alert data"
    assert data["alert"]["type"] == alert.type
    assert data["alert"]["description"] == alert.description
    assert data["alert"]["created_at"] == alert.created_at.isoformat()
    # We check sender data against the database values, and we check that sensitive data is not present in the response
    assert data["sender"]["id"] == str(alert_sender.id)
    assert data["sender"]["firstname"] == alert_sender.firstname
    assert data["sender"]["surname"] == alert_sender.surname
    assert data["sender"]["email"] == alert_sender.email
    assert data["sender"]["role"] == alert_sender.role
    assert data["sender"]["reliability_score"] == alert_sender.reliability_score
    assert "password" not in data["sender"], "password should not be present in the sender data"
    assert "password_hash" not in data["sender"], "password_hash should not be present in the sender data"
    assert "activation_code" not in data["sender"], "activation_code should not be present in the sender data"
    # Alerted users and votes map should be empty for general or empty alerts
    assert len(data["users"]) == 0
    assert len(data["votes_map"]) == 0

def test_get_alert_with_users_success_called_by_admin(client, db_session, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    statement = select(Alert).where(Alert.type == AlertType.local.value)
    # We take a random alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0
    alert = random.choice(alerts)
    assert alert is not None
    # We call the endpoint to get the alert with users 
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/users", headers={"Authorization": f"Bearer {access_token}"})
    # We check only the successful response, because the logic of the endpoint is already tested in the previous tests
    assert response.status_code == status.HTTP_200_OK
