# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
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
    response_data = response.json()
    assert response_data["alerted_users"] == []
    assert response_data["next_cursor"] is None

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
    resp_data = response.json()
    for au in resp_data["alerted_users"]:
        user_id = str(au["user"]["id"])
        assert au["alert_id"] == alert_id
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
    # Next cursor should be None, because we are returning all alerted users for the alert, in a single page 
    # (the default limit is 100, and we have less than 100 alerted users for the alert)
    assert resp_data["next_cursor"] is None

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
    resp_data = response.json()
    # The list returned should be empty for general or empty alerts
    assert resp_data["alerted_users"] == []
    assert resp_data["next_cursor"] is None

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

def test_get_alerted_users_success_paginated(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.local.value)
    # We take a random local alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0
    alert = random.choice(alerts)
    assert alert is not None
    # We call the endpoint to get the alerted users with pagination
    alert_id = alert.id
    # The default limit is 100, but we can set a lower allowed limit to test pagination
    limit = 10
    offset = 0
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users?limit={limit}&offset={offset}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    # The list returned is the first page, and it should have at most 'limit' number of alerted users
    assert len(resp_data["alerted_users"]) <= limit
    if len(resp_data["alerted_users"]) == limit:
        assert resp_data["next_cursor"] == offset + limit
        # If we recall the endpoint with offset+limit, we should get the next page of alerted users (the second page)
        response = client.get(
            f"/api/alerts/{alert_id}/alerted-users?limit={limit}&offset={offset+limit}", headers={"Authorization": f"Bearer {access_token}"})
        assert response.status_code == status.HTTP_200_OK
        resp_data = response.json()
        # The list returned should have at most 'limit' number of alerted users
        # and the next_cursor should be None because there are no more alerted users beyond the second page
        # (see setup_alerts_data_and_teardown fixture, which creates 15 alerted users for each local alert, 
        # plus sometimes an additional alerted user, so maximum two pages if the page limit is 10)
        assert len(resp_data["alerted_users"]) <= limit
        assert resp_data["next_cursor"] is None
    else:
        assert resp_data["next_cursor"] is None

def test_get_alerted_users_success_paginated_offset_too_far(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.local.value)
    # We take a random local alert from the test database
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    assert alerts_num > 0
    alert = random.choice(alerts)
    assert alert is not None
    # We call the endpoint to get the alerted users with pagination, but with an offset that is too far
    # (see setup_alerts_data_and_teardown fixture, which creates 15 or 16 alerted users for each local alert)
    alert_id = alert.id
    limit = 10
    offset = 1000
    response = client.get(
        f"/api/alerts/{alert_id}/alerted-users?limit={limit}&offset={offset}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    # The list returned should be empty because the offset is beyond the number of alerted users for the alert
    assert len(resp_data["alerted_users"]) == 0
    assert resp_data["next_cursor"] is None
