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
    User, RefreshToken, 
    Alert, AlertType, AlertedUser,
    ALERT_MAX_MESSAGES_NUM,
    Message
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required fixture (manually called as argument named "test_alert" in test functions when needed)
    setup_fake_functions
)

def test_create_message_not_authorized_missing_token(client, test_alert):
    data = {
        "content": "This is a test message",
    }
    alert_id = test_alert.id
    response = client.post(f"/api/alerts/{alert_id}/messages", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_create_message_not_authorized_invalid_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    data = {
        "content": "This is a test message",
    }
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_create_message_content_too_long(client, test_alert, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    assert test_alert is not None, "No alert found in the database for testing"
    data = {
        "content": "A" * 513,
    }
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_create_message_alert_not_found(client, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    data = {
        "content": "This is a test message",
    }
    alert_id = 9999  # Non-existing alert ID
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "not found" in response.json()["detail"].lower()

def test_create_message_alert_is_closed(client, db_session, test_alert, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    assert test_alert is not None, "No alert found in the database for testing"
    # Close the alert first, to simulate the case where the alert is closed
    test_alert.is_closed = True
    db_session.add(test_alert)
    db_session.commit()
    # Call the API endpoint to create a message for the alert
    data = {
            "content": "This is a test message",
        }
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "alert is closed" in response.json()["detail"].lower()

def test_create_message_not_sender_not_alert_manager(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is not test_baseuser,
    # and test_baseuser is an alerted user but not an alert manager.
    statement = (select(Alert, AlertedUser).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(Alert.user_id != user.id, Alert.is_closed == False)
        .where(AlertedUser.user_id == user.id, AlertedUser.is_manager == False))
    result = db_session.exec(statement).first()
    assert result is not None, "No suitable alert found in the database for testing"
    test_alert = result[0]
    test_alerted_user = result[1]
    assert test_alerted_user is not None
    assert test_alert is not None
    assert test_alert.user_id != user.id
    assert test_alerted_user.user_id == user.id
    assert test_alerted_user.is_manager == False
    # Call the API endpoint to create a message for the alert
    data = {
            "content": "This is a test message",
        }
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Only the alert sender or the chief alert manager can create messages for this alert" in response.json()["detail"]

def test_create_message_alert_is_local_and_caller_not_reliable(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_baseuser, 
    # and test_baseuser is not reliable. We will set the user as unreliable before calling the API.
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == user.id
    # Set the caller as unreliable, to simulate the case where the caller is not reliable
    user.reliability_score = 0
    db_session.add(user)
    db_session.commit()
    # Call the API endpoint to create a message for the alert
    data = {
            "content": "This is a test message",
        }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    # When the alert is local and the caller (if he is the alert sender) is not reliable, 
    # the API should return a forbidden exception with a message indicating that the user is not reliable.
    assert response.status_code == forbidden_exception().status_code
    assert "You are not a reliable user" in response.json()["detail"]

def test_create_message_alert_is_local_and_banned(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_baseuser, 
    # and test_baseuser is reliable, so the user appears eligible to create a message, 
    # but the alert is banned. 
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == user.id
    # Set the alert as banned, to simulate the case where the alert is banned
    alert.is_banned = True
    db_session.add(alert)
    db_session.commit()
    # Call the API endpoint to create a message for the alert
    data = {
            "content": "This is a test message",
        }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    # When the alert is local and the alert is banned,
    # the caller (if he is the alert sender) cannot create a message.
    assert response.status_code == forbidden_exception().status_code
    assert "alert has been banned" in response.json()["detail"].lower()

def test_create_message_limit_reached(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_baseuser, 
    # and test_baseuser is reliable and the alert is not banned.
    # But we will set the alert as having reached the message limit, 
    # to simulate the case where the alert has reached the message limit. 
    statement = select(Alert).where(Alert.user_id == user.id)
    alert = db_session.exec(statement).first()
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == user.id
    # Set the alert as having reached the message limit, 
    # to simulate the case where the alert has reached the message limit
    alert.messages_num = ALERT_MAX_MESSAGES_NUM
    db_session.add(alert)
    db_session.commit()
    # Call the API endpoint to create a message for the alert
    data = {
            "content": "This is a test message",
        }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    # When the alert has reached the message limit,
    # the caller cannot create a message.
    assert response.status_code == forbidden_exception().status_code
    assert "alert has reached the maximum number of messages" in response.json()["detail"].lower()
