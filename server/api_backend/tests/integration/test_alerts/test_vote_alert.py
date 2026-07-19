# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception,
    not_found_exception
)
from models.general import (
    User, Alert, AlertType, AlertedUser
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required fixture (manually called as argument in test functions when needed)
)

def test_vote_alert_not_authorized_missing_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    alert_id = test_alert.id
    response = client.post(f"/api/alerts/{alert_id}/vote", json={"vote": 1})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_vote_alert_not_authorized_invalid_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": 1}, headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_vote_alert_vote_not_valid(client, test_alert, test_baseuser):
    caller: User = test_baseuser["user"]
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser["access_token"]
    assert test_alert is not None, "No alert found in the database for testing"
    assert test_alert.type == AlertType.local.value, "Test alert is not a local alert"
    alert_id = test_alert.id
    # We call the API endpoint to vote the alert with an invalid vote value (not -1 or +1)
    # Valid vote values are -1 (downvote) and +1 (upvote). Any other value is invalid.
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": -5}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Another example with 0 as invalid vote value
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": 0}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_vote_alert_current_user_not_reliable(client, db_session, test_alert, test_baseuser):
    caller: User = test_baseuser["user"]
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser["access_token"]
    assert test_alert is not None, "No alert found in the database for testing"
    assert test_alert.type == AlertType.local.value, "Test alert is not a local alert"
    alert_id = test_alert.id
    # We simulate that the caller (test_baseuser) is not a reliable user by setting is_reliable to False
    caller.is_reliable = False
    db_session.add(caller)
    db_session.commit()
    db_session.refresh(caller)
    # We call the API endpoint to vote the alert with a reliable user (test_baseuser) that has reliability_score <= 0
    # We expect a forbidden response because the user is not reliable
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": -1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "you are not a reliable user" in response.json()["detail"].lower()
    # Another example with reliability_score <= 0
    caller.is_reliable = True
    caller.reliability_score = 0
    db_session.add(caller)
    db_session.commit()
    db_session.refresh(caller)
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": +1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "you are not a reliable user" in response.json()["detail"].lower()
    # Another example with reliability_score < 0
    caller.reliability_score = -5
    db_session.add(caller)
    db_session.commit()
    db_session.refresh(caller)
    response = client.post(
        f"/api/alerts/{alert_id}/vote", json={"vote": +1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "you are not a reliable user" in response.json()["detail"].lower()

def test_vote_alert_not_found(client, test_baseuser):
    caller: User = test_baseuser["user"]
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser["access_token"]
    # We call the API endpoint to vote an alert that does not exist (alert_id = 999999)
    response = client.post(
        f"/api/alerts/999999/vote", json={"vote": 1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "alert not found" in response.json()["detail"].lower()

def test_vote_alert_not_local(client, db_session, test_baseuser):
    caller: User = test_baseuser["user"]
    access_token = test_baseuser["access_token"]
    # We select an alert from the database, where the API caller (test_baseuser) is an alerted user
    statement = (select(Alert).join(AlertedUser, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(AlertedUser.user_id == caller.id)
            .where(Alert.type == AlertType.local.value))
    alerts = db_session.exec(statement).all()
    # There are for sure some alerts in the database where the API caller (test_baseuser) is an alerted user,
    # because of the fixture setup_alerts_data_and_teardown
    assert len(alerts) > 0, "No alerts found in the database for testing"
    # We pick one of these alerts randomly
    test_alert = random.choice(alerts)
    # We simulate that this alert is not a local alert by setting its type to "managed"
    test_alert.type = AlertType.managed.value
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    # We call the API endpoint to vote this non-local alert    
    response = client.post(
        f"/api/alerts/{test_alert.id}/vote", json={"vote": 1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "you can only vote for local alerts" in response.json()["detail"].lower()

def test_vote_alert_closed(client, db_session, test_baseuser):
    caller: User = test_baseuser["user"]
    access_token = test_baseuser["access_token"]
    # We select an alert from the database, where the API caller (test_baseuser) is an alerted user
    statement = (select(Alert).join(AlertedUser, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(AlertedUser.user_id == caller.id)
            .where(Alert.type==AlertType.local.value))
    alerts = db_session.exec(statement).all()
    # There are for sure some alerts in the database where the API caller (test_baseuser) is an alerted user, 
    # because of the fixture setup_alerts_data_and_teardown
    assert len(alerts) > 0
    for alert in alerts:
        assert alert.is_closed == False
    # Now we pick one of these alerts and we simulate that it is closed by setting is_closed to True
    alert = random.choice(alerts)
    alert.is_closed = True
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    # We call the API endpoint to vote for this closed alert    
    response = client.post(
        f"/api/alerts/{alert.id}/vote", json={"vote": 1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "alert is closed" in response.json()["detail"].lower()

def test_vote_alert_alerted_user_not_found(client, db_session, test_baseuser, test_chief):
    # We select an alert from the database, where the API caller (test_baseuser) is not an alerted user
    # In the fixture setup_alerts_data_and_teardown, there are 3 alert created by test_chiefs. 
    # For each of these alerts, test_baseuser is not an alerted user.
    caller: User = test_baseuser["user"]
    access_token = test_baseuser["access_token"]
    statement = (select(Alert).where(Alert.user_id == test_chief["user"].id)
                 .where(Alert.type == AlertType.local.value))
    alerts = db_session.exec(statement).all()
    assert len(alerts) > 0, "No alerts found in the database for testing"
    # For each alert, the API caller (test_baseuser) is not an alerted user
    for alert in alerts:
        alerted_user = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id, AlertedUser.user_id == caller.id)).first()
        assert alerted_user is None
    test_alert = random.choice(alerts)
    # We call the API endpoint to vote the alert, and we expect a not found response
    # because the API caller (test_baseuser) is not an alerted user for the test alert
    response = client.post(
        f"/api/alerts/{test_alert.id}/vote", json={"vote": 1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "you are not an alerted user" in response.json()["detail"].lower()

def test_vote_alert_alerted_user_already_voted(client, db_session, test_baseuser):
    caller: User = test_baseuser["user"]
    access_token = test_baseuser["access_token"]
    # We select an alert from the database, where the API caller (test_baseuser) is an alerted user
    statement = (select(Alert).join(AlertedUser, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(AlertedUser.user_id == caller.id)
            .where(Alert.type == AlertType.local.value))
    alerts = db_session.exec(statement).all()
    # There are for sure some alerts in the database where the API caller (test_baseuser) is an alerted user,
    # because of the fixture setup_alerts_data_and_teardown
    assert len(alerts) > 0, "No alerts found in the database for testing"
    # We pick one of these alerts randomly
    test_alert = random.choice(alerts)
    # We simulate that the API caller (test_baseuser) has already voted for this alert by setting the vote to +1
    alerted_user = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == test_alert.id, AlertedUser.user_id == caller.id)).first()
    assert alerted_user is not None, "No alerted user found in the database for testing"
    alerted_user.vote = 1
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We call the API endpoint to vote the alert, and we expect a forbidden response
    # because the API caller (test_baseuser) has already voted for this alert
    response = client.post(
        f"/api/alerts/{test_alert.id}/vote", json={"vote": +1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "already voted" in response.json()["detail"].lower()

def test_vote_alert_success(client, db_session, test_baseuser):
    caller: User = test_baseuser["user"]
    access_token = test_baseuser["access_token"]
    # We select an alert from the database, where the API caller (test_baseuser) is an alerted user
    statement = (select(Alert).join(AlertedUser, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(AlertedUser.user_id == caller.id)
            .where(Alert.type == AlertType.local.value))
    alerts = db_session.exec(statement).all()
    # There are for sure some alerts in the database where the API caller (test_baseuser) is an alerted user,
    # because of the fixture setup_alerts_data_and_teardown
    assert len(alerts) > 0, "No alerts found in the database for testing"
    # We pick one of these alerts randomly
    test_alert = random.choice(alerts)
    # We assert that the API caller (test_baseuser) has not voted for this alert
    # checking that the current vote is 0 (not voted yet)
    statement = select(AlertedUser).where(AlertedUser.alert_id == test_alert.id, AlertedUser.user_id == caller.id)
    alerted_user = db_session.exec(statement).first()
    assert alerted_user is not None
    assert alerted_user.vote == 0
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We call the API endpoint to vote the alert with a valid vote value (+1 or -1)
    response = client.post(
        f"/api/alerts/{test_alert.id}/vote", json={"vote": +1}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json()["message"] == "Vote registered successfully"
    assert response.json()["vote"] == +1
