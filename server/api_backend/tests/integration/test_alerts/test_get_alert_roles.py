# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception
)
from models.general import (
    User, UserRole, Alert, AlertType, AlertedUser
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
)

def test_get_alert_roles_missing_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}/roles")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_alert_roles_not_authorized_invalid_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_alert_roles_forbidden(client, db_session, test_baseuser):
    baseuser: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    statement = select(Alert).where(Alert.user_id == baseuser.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # There is at least one local alert created by test_baseuser (see setup_alerts_data_and_teardown fixture)
    # Theorically he can view alert created by himself, but in this case not,
    # because this endpoint is useful to see additional info (number of alerted specialists, for each role),
    # and this is only allowed to chiefs (and admins), not to base users
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_alert_roles_alert_not_exists(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # Use a non-existing alert_id (assuming 111111 does not exist)
    alert_id = 111111
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    # The response is 200 and the alert_roles list contains all zero counts, because the alert does not exist 
    # (so no users alerted for a non-existing alert)
    assert response.status_code == status.HTTP_200_OK
    assert "alert_roles" in response.json()
    for role in response.json()["alert_roles"]:
        assert role["role"] in [r.value for r in UserRole]
        assert role["specialists_count"] == 0

def test_get_alert_roles_for_a_general_alert(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.general.value)
    alert = db_session.exec(statement).first()
    # There is at least one general alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No general alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The response should contain a list of roles and their counts,
    # but since this is a general alert, all roles should have a count of 0 (no users alerted for a general alert)
    assert "alert_roles" in response_data
    for role in response_data["alert_roles"]:
        assert role["role"] in [r.value for r in UserRole]
        assert role["specialists_count"] == 0

def test_get_alert_roles_for_an_empty_alert(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.empty.value)
    alert = db_session.exec(statement).first()
    # There is at least one empty alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No empty alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The response should contain a list of roles and their counts,
    # and since this is an empty alert, there are no users alerted, so all roles should have a count of 0
    assert "alert_roles" in response_data
    for role in response_data["alert_roles"]:
        assert role["role"] in [r.value for r in UserRole]
        assert role["specialists_count"] == 0

def test_get_alert_roles_for_a_managed_alert(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.managed.value)
    alert = db_session.exec(statement).first()
    # There is at least one managed alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No managed alert found in the database for testing"
    # Now we try to find all alerted users with their roles for this alert
    statement = (select(AlertedUser, User)
            .join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id)
    )
    role_counts = {}
    for role in UserRole:
        role_counts[role.value] = 0
    results = db_session.exec(statement).all()
    # There are for sure some alerted users 
    # for this managed alert (see setup_alerts_data_and_teardown fixture)
    assert len(results) > 0, "No alerted users found for the managed alert"
    for _, user in results:
        assert (user.role is None) or (user.role in [r.value for r in UserRole])
        if user.role:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
    # Now we call the API endpoint to get the alert roles and their counts
    # and we check that the counts match what we manually counted from the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The response should contain a list of roles and their counts,
    # and since this is a managed alert, there should be some users alerted for each role
    assert "alert_roles" in response_data
    for role in response_data["alert_roles"]:
        assert role["role"] in [r.value for r in UserRole]
        assert role["specialists_count"] >= 0
        assert role["specialists_count"] == role_counts[role["role"]]

def test_get_alert_roles_for_a_local_alert(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    statement = select(Alert).where(Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # There is at least one local alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No local alert found in the database for testing"
    # Now we try to find all alerted users with their roles for this alert
    statement = (select(AlertedUser, User)
            .join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id)
    )
    role_counts = {}
    for role in UserRole:
        role_counts[role.value] = 0
    results = db_session.exec(statement).all()
    # There are for sure some alerted users 
    # for this local alert (see setup_alerts_data_and_teardown fixture)
    assert len(results) > 0, "No alerted users found for the local alert"
    for _, user in results:
        assert (user.role is None) or (user.role in [r.value for r in UserRole])
        if user.role:
            role_counts[user.role] = role_counts.get(user.role, 0) + 1
    # Now we call the API endpoint to get the alert roles and their counts
    # and we check that the counts match what we manually counted from the database
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/roles", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The response should contain a list of roles and their counts,
    # and since this is a local alert, there should be some users alerted for each role
    assert "alert_roles" in response_data
    for role in response_data["alert_roles"]:
        assert role["role"] in [r.value for r in UserRole]
        assert role["specialists_count"] >= 0
        assert role["specialists_count"] == role_counts[role["role"]]
