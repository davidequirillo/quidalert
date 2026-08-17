# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from unittest.mock import ANY
from fastapi import status
from sqlmodel import select, delete
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception,
    not_found_exception
)
from models.general import (
    User, Alert, AlertType, AlertedUser,
    ALERT_MAX_MESSAGES_NUM
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

def test_create_message_success_for_general_alert(client, db_session, test_chief, setup_fake_functions):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No chief found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_chief and the alert is general
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.general.value)
    alert = db_session.exec(statement).first()
    assert alert is not None, "No suitable alert found in the database for testing"
    # The caller is the alert sender, because the alert is general
    assert alert.user_id == chief.id
    messages_count_before_api = alert.messages_num
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are not sent because the alert is general
    setup_fake_functions["mock_notify_on_new_message"].assert_not_called()

def test_create_message_success_for_empty_alert(client, db_session, test_chief, setup_fake_functions):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No chief found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_chief and the alert is empty
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.empty.value)
    alert = db_session.exec(statement).first()
    # The caller is the alert sender, because the alert is empty
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == chief.id
    messages_count_before_api = alert.messages_num
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are not sent because the alert is empty
    setup_fake_functions["mock_notify_on_new_message"].assert_not_called()

def test_create_message_success_for_managed_alert(client, db_session, test_chief, setup_fake_functions):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No chief found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_chief and the alert is managed
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.managed.value)
    alert = db_session.exec(statement).first()
    # The caller is the alert sender, because the alert is managed
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == chief.id
    messages_count_before_api = alert.messages_num
    # We verify that there are some alerted users for this alert
    # See setup_alerts_data_and_teardown fixture, which creates some alerted users for the managed alert
    statement_alerted_users = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement_alerted_users).all()
    assert len(alerted_users) > 0, "No alerted users found for the managed alert in the database for testing"
    alerted_users_ids = [str(alerted_user.user_id) for alerted_user in alerted_users]
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are sent because the alert is managed
    # and there are some alerted users for this alert, 
    # so the mock_notify_on_new_message function should be called once
    setup_fake_functions["mock_notify_on_new_message"].assert_called_once()
    msg_name = f"{chief.firstname} {chief.surname}"
    msg_content = data["content"]
    if len(msg_content) > 30:
        msg_content = msg_content[:30] + "..."
    setup_fake_functions["mock_notify_on_new_message"].assert_called_with(
        alerted_users_ids, ANY, chief.language,
        ANY, msg_name, msg_content,
        ANY, ANY
    )

def test_create_message_success_by_alert_sender(client, db_session, test_baseuser, setup_fake_functions):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_baseuser and the alert is local
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # The caller is the alert sender in this case 
    # (the alert sender calls the API to create a message for the alert)
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == user.id
    messages_count_before_api = alert.messages_num
    # We select all alerted users for this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    # We verify that there are some alerted users for this alert.
    # See setup_alerts_data_and_teardown fixture, which creates some alerted users for the local alert
    assert len(alerted_users) > 0, "No alerted users found for the local alert in the database for testing"
    alerted_users_ids = [str(alerted_user.user_id) for alerted_user in alerted_users]
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are sent because the alert is local
    # and there are some alerted users for this alert.
    # So the notify_on_new_message function should be called once
    setup_fake_functions["mock_notify_on_new_message"].assert_called_once()
    msg_name = f"{user.firstname} {user.surname}"
    msg_content = data["content"]
    if len(msg_content) > 30:
        msg_content = msg_content[:30] + "..."
    setup_fake_functions["mock_notify_on_new_message"].assert_called_with(
        alerted_users_ids, ANY, user.language,
        ANY, msg_name, msg_content,
        ANY, ANY
    )

def test_create_message_success_by_alert_manager(client, db_session, test_chief, setup_fake_functions):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No chief found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert where test_chief is an alerted user
    statement = (select(Alert, AlertedUser).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == chief.id))
    result = db_session.exec(statement).first()
    assert result is not None
    alert = result[0]
    alerted_user = result[1]
    assert alert is not None
    assert alerted_user is not None
    assert alerted_user.user_id == chief.id
    assert alerted_user.alert_id == alert.id
    # We simulate that the alerted user (test_chief) is the alert manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We also select all alerted user for this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    alerted_users_ids = [str(alerted_user.user_id) for alerted_user in alerted_users]
    messages_count_before_api = alert.messages_num
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are sent because the alert is local
    # and there are some alerted users for this alert.
    # So the notify_on_new_message function should be called once
    setup_fake_functions["mock_notify_on_new_message"].assert_called_once()
    msg_name = f"{chief.firstname} {chief.surname}"
    msg_content = data["content"]
    if len(msg_content) > 30:
        msg_content = msg_content[:30] + "..."
    # In this case we notify all alerted users 
    # (except the alert manager, who is the caller),
    # and we also notify the alert sender
    alerted_users_ids.remove(str(chief.id))  # Remove the alert manager from the list of alerted users to notify
    # Note: the order of the list is relevant, because the notify_on_new_message function (see alert_btasks.py) 
    # is called with the list of user IDs in a specific order (first the alert sender, then the alerted users), 
    # so we need to maintain that order in the test.
    users_to_notify_ids = [str(alert.user_id)] + alerted_users_ids
    setup_fake_functions["mock_notify_on_new_message"].assert_called_with(
        users_to_notify_ids, ANY, chief.language,
        ANY, msg_name, msg_content,
        ANY, ANY
    )

def test_create_message_with_no_other_alerted_users(client, db_session, test_baseuser, setup_fake_functions):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select an alert from database where the alert sender is test_baseuser and the alert is local
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    # The caller is the alert sender in this case 
    # (the alert sender calls the API to create a message for the alert)
    assert alert is not None, "No suitable alert found in the database for testing"
    assert alert.user_id == user.id
    messages_count_before_api = alert.messages_num
    # We remove all alerted users for this alert, 
    # to simulate the case where there are no alerted users
    statement = delete(AlertedUser).where(AlertedUser.alert_id == alert.id)
    db_session.exec(statement)
    db_session.commit()
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    assert len(alerted_users) == 0, "There are still alerted users for the local alert in the database for testing"
    # Call the API endpoint to create a message for the alert
    data = {
        "content": "This is a test message",
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/messages", json=data, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["message"] == "Message created successfully"
    assert response_data["message_id"] is not None
    # Verify that the messages_num field in the alert has been incremented
    db_session.refresh(alert)
    assert alert.messages_num == messages_count_before_api + 1
    # Notifications are not sent because there are no alerted users for this alert,
    # so the notify_on_new_message function should not be called
    setup_fake_functions["mock_notify_on_new_message"].assert_not_called()
