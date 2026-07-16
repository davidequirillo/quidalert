# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from fastapi import status
from sqlmodel import select
from core.exceptions import (
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

def test_get_alerted_users_missing_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}/alerted-users")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_alerted_users_not_authorized_invalid_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_alerted_users_forbidden(client, db_session, test_baseuser):
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
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alerted_users_forbidden_officer(client, db_session, test_officer):
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
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alerted_users_alert_not_exists(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # Use a non-existing alert_id (assuming 111111 does not exist)
    alert_id = 111111
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    # The response is 200 because the endpoint returns an empty list of alerted users if the alert does not exist
    assert response.status_code == status.HTTP_200_OK
    assert response.json() == []

def test_get_alerted_users_of_local_or_managed_alert(client, db_session, test_chief):
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
    # We get the alerted users from the database
    # We get also users info related to the alerted users, and we build the votes map
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    # There are for sure some alerted users (see setup_alerts_data_and_teardown fixture)
    assert len(alerted_users) > 0
    alerted_user_ids = [au.user_id for au in alerted_users]
    users = db_session.exec(select(User).where(User.id.in_(alerted_user_ids))).all() # type: ignore
    user_firstnames = [user.firstname for user in users]
    user_surnames = [user.surname for user in users]
    user_emails = [user.email for user in users]
    votes_map = {}
    for alerted_user in alerted_users:
        votes_map[str(alerted_user.user_id)] = alerted_user
    # We call the endpoint to get the alerted users
    # and we check that the results are the same as the ones in the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_users = response.json()
    for au in resp_users:
        user_id = str(au["user"]["id"])
        assert "password" not in au["user"], "password should not be present in the alerted user data"
        assert "password_hash" not in au["user"], "password_hash should not be present in the alerted user data"
        assert "activation_code" not in au["user"], "activation_code should not be present in the alerted user data"
        assert au["user"]["firstname"] in user_firstnames, f"Alerted user {user_id} firstname mismatch"
        assert au["user"]["surname"] in user_surnames, f"Alerted user {user_id} surname mismatch"
        assert au["user"]["email"] in user_emails, f"Alerted user {user_id} email mismatch"
        assert au["vote"] == votes_map[user_id].vote, f"Vote for user {user_id} mismatch"
        assert au["closing_vote"] == votes_map[user_id].closing_vote, f"Closing vote for user {user_id} mismatch"
        assert au["is_manager"] == votes_map[user_id].is_manager, f"is_manager for user {user_id} mismatch"
        assert au["distance"] == votes_map[user_id].distance, f"Distance for user {user_id} mismatch"

def test_get_alerted_users_type_general_or_empty_success(client, db_session, test_chief):
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
    # We call the endpoint to get the alerted users 
    # and we check that the results are the same as the ones in the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_users = response.json()
    # The list returned should be empty for general or empty alerts
    assert len(resp_users) == 0

def test_get_alerted_users_success_called_by_admin(client, db_session, test_admin):
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
    # We call the endpoint to get the alerted users
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users", headers={"Authorization": f"Bearer {access_token}"})
    # We check only the successful response, because the logic of the endpoint is already tested in the previous tests
    assert response.status_code == status.HTTP_200_OK
