# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception,
    not_found_exception
)
from models.general import (
    User, Alert, AlertType, AlertedUser,
    ALERT_MAX_MESSAGES_NUM, Message
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required fixture (manually called as argument named "test_alert" in test functions when needed)
    setup_fake_functions
)

def test_get_messages_not_authorized_missing_token(client, test_alert):
    alert_id = test_alert.id
    response = client.get(f"/api/alerts/{alert_id}/messages")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_messages_not_authorized_invalid_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    alert_id = test_alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_messages_alert_not_found(client, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    alert_id = 9999  # Non-existing alert ID
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "not found" in response.json()["detail"].lower()

def test_get_messages_called_by_chief(client, db_session, test_chief, test_baseuser):
    chief: User = test_chief['user']
    user: User = test_baseuser['user']
    # Test_chief is the caller
    access_token = test_chief['access_token']
    assert chief is not None
    assert access_token is not None
    # Chiefs and admins can get alert messages even if they are not involved for a specific alert.
    # To verify this, we select a local alert created by test_baseuser (the alert sender).
    # Test_chief is not an alerted user for any alert created by test_baseuser
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == user.id
    statement = select(AlertedUser).where(AlertedUser.alert_id==alert.id)
    alerted_users = db_session.exec(statement).all()
    for alerted_user in alerted_users:
        assert alerted_user.user_id != chief.id
    # Now we call the API and we verify it's successful for test_chief
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK

def test_get_messages_called_by_user_not_involved(client, db_session, test_baseuser, test_chief):
    user: User = test_baseuser['user']
    chief: User = test_chief['user']
    # Test_baseuser is the caller
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert created by test_chief (the alert sender).
    # Test_baseuser is not an alerted user for any alert created by test_chief
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == chief.id
    statement = select(AlertedUser).where(AlertedUser.alert_id==alert.id)
    alerted_users = db_session.exec(statement).all()
    for alerted_user in alerted_users:
        assert alerted_user.user_id != user.id
    # Now we call the API and we verify it's forbidden for test_baseuser
    # because he is not involved in the alert (he is not the alert sender and he is not an alerted user)
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "not authorized" in response.json()["detail"].lower()

def test_get_messages_called_by_alert_sender(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert created by test_baseuser (the alert sender).
    # Test_baseuser is the sender so he can view all messages related to this alert
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == user.id
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # response_data is a json object, but in this case is not a dict (map)
    # It's a list (see the api implementation)
    messages = response_data
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None

def test_get_messages_called_by_alerted_user(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert where test_baseuser is an alerted user,
    # so he can view all messages related to the alert
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id==Alert.id) # type: ignore
            .where(AlertedUser.user_id == user.id, Alert.type == AlertType.local.value))
    result = db_session.exec(statement).first()
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alerted_user.alert_id == alert.id
    assert alerted_user.user_id == user.id
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # response_data is a json object, but in this case is not a dict (map)
    # It's a list (see the api implementation)
    messages = response_data
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None

def test_get_messages_with_all_messages_banned(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert created by test_baseuser (the alert sender).
    # Test_baseuser is the sender so he can view all messages related to this alert.
    # But we simulate a banned alert with all messages banned.
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == user.id
    alert.is_banned = True
    db_session.add(alert)
    statement = select(Message).where(Message.alert_id==alert.id)
    messages = db_session.exec(statement).all()
    for msg in messages:
        msg.is_banned = True
        db_session.add(msg)
    db_session.commit()
    # Now we call the API and we verify it's successful
    # but all returned messages contain a "banned text"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # response_data is a json object, but in this case is not a dict (map)
    # It's a list (see the api implementation)
    messages = response_data
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        # Content is banned!
        assert "user_id" not in msg
        assert msg["content"] == "[BANNED MESSAGE]"
        assert msg["created_at"] is not None
