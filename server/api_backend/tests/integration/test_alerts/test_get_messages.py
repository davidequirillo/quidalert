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
    setup_alert_fake_functions
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

def test_get_messages_called_by_admin(client, db_session, test_admin, test_baseuser):
    admin: User = test_admin['user']
    user: User = test_baseuser['user']
    # Test_admin is the caller
    access_token = test_admin['access_token']
    assert admin is not None
    assert access_token is not None
    # Chiefs and admins can get alert messages even if they are not involved for a specific alert.
    # To verify this, we select a local alert created by test_baseuser (the alert sender).
    # Test_admin is not an alerted user for any alert created by test_baseuser
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == user.id
    statement = select(AlertedUser).where(AlertedUser.alert_id==alert.id)
    alerted_users = db_session.exec(statement).all()
    for alerted_user in alerted_users:
        assert alerted_user.user_id != admin.id
    # Now we call the API and we verify it's successful for test_admin
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

def test_get_messages_if_alert_is_general(client, db_session, test_chief, test_baseuser):
    chief: User = test_chief['user']
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert chief is not None, "No chief user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a general alert created by test_chief (the alert sender).
    # Test_chief is the alert sender, but is also the alert manager (because the alert is a non-local alert)
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.general.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.general.value
    assert alert.user_id == chief.id
    # Now we call the API with test_baseuser as caller 
    # and we verify it's successful.
    # Test_baseuser can view all messages for a general alert,
    # even if he is not the alert sender or an alerted user.
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert response.json() is not None
    response_data = response.json()
    messages = response_data["messages"]
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg

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
    messages = response_data["messages"]
    chat_is_readonly = response_data["readonly"]
    # For alert sender the chat is in write mode (readonly is False)
    assert chat_is_readonly is False
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg

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
    messages = response_data["messages"]
    chat_is_readonly = response_data["readonly"]
    # For a base alerted_user (not alerted manager) the chat is in read-only mode
    assert chat_is_readonly == True
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg

def test_get_messages_called_by_alerted_manager(client, db_session, test_chief):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert where test_chief is an alerted user,
    # so he can view all messages related to the alert
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id==Alert.id) # type: ignore
            .where(AlertedUser.user_id == chief.id, Alert.type == AlertType.local.value))
    result = db_session.exec(statement).first()
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alerted_user.alert_id == alert.id
    assert alerted_user.user_id == chief.id
    # We semulate that test_chief is an alerted manager for this alert
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    messages = response_data["messages"]
    chat_is_readonly = response_data["readonly"]
    # The alerted manager (alerted user with "is_manager" field set to True) 
    # can write messages in this chat, so read-only mode is False
    assert chat_is_readonly == False
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg

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
    messages = response_data["messages"]
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
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg

def test_get_messages_check_messages_details_case_1(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert created by test_baseuser (the alert sender).
    # Test_baseuser is the sender so he can view all messages related to this alert
    statement = select(Alert).where(Alert.user_id == user.id, Alert.type == AlertType.local.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    # It's a local alert
    assert alert.type == AlertType.local.value
    assert alert.user_id == user.id
    # We simulate that the first alerted user is the alerted manager.
    statement = select(AlertedUser).where(AlertedUser.alert_id==alert.id)
    alerted_user = db_session.exec(statement).first()
    # There is for sure at least one alerted user for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert alerted_user is not None
    # We simulate that the first alerted user is the alerted manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We select all messages for this alert, joined with user's info
    statement = (select(Message, AlertedUser, User)
            .join(AlertedUser, AlertedUser.user_id==Message.user_id) # type: ignore
            .join(User, AlertedUser.user_id==User.id) # type: ignore
            .where(Message.alert_id==alert.id, AlertedUser.alert_id==alert.id))
    results = db_session.exec(statement).all()
    print(f"Found {len(results)} messages from alerted users for alert id={alert.id}")
    # Now we construct a special messages map, where the key is the message id, 
    # and each element is a dict with the related user's info
    # It's useful to check the messages details later.
    # Note: we must add the sender's messages too, 
    # because the join done above will return only the messages from the alerted users
    special_messages_map = {}
    for r in results:
        m = r[0] # the message in result
        assert m.id is not None
        assert m.alert_id == alert.id
        au = r[1] # the alerted_user in result
        u = r[2] # the user in result
        if au.is_manager == True:
            print(f"Alerted user {u.firstname} {u.surname} (email={u.email}) is the alerted manager for alert_id={alert.id}, message_id={m.id}")
        special_messages_map[str(m.id)] = {
            "firstname": u.firstname,
            "surname": u.surname,
            "user_role": u.role,
            "is_alert_sender": (u.id == alert.user_id),
            "is_alert_manager": au.is_manager, # for local alerts, the alert manager is the alerted user with is_manager=True, not the alert sender
            "is_caller": (u.id == test_baseuser['user'].id)
        }
    sender_messages_stmt = (select(Message, User)
                .join(User, User.id==Message.user_id) # type: ignore
                .where(Message.alert_id==alert.id, Message.user_id==alert.user_id))
    results = db_session.exec(sender_messages_stmt).all()
    print(f"Found {len(results)} messages from alert sender for alert id={alert.id}")
    for m, u in results:
        special_messages_map[str(m.id)] = {
            "firstname": u.firstname,
            "surname": u.surname,
            "user_role": u.role,
            "is_alert_sender": (u.id == alert.user_id),
            "is_alert_manager": False, # for local alerts, the alert manager is the alerted user with is_manager=True, not the alert sender
            "is_caller": (u.id == test_baseuser['user'].id)
        }
    special_messages_length = len(special_messages_map)
    print(f"Total messages in special messages map for alert id={alert.id}: {special_messages_length}")
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    messages = response_data["messages"]
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    assert len(messages) == special_messages_length
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["id"] is not None
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg
        # Now we check that the message details match the the info contained in special_messages_map
        special_msg = special_messages_map.get(str(msg["id"]))
        assert special_msg is not None
        # Now we check that the message details match the alerted user info
        assert msg["user_role"] == special_msg["user_role"]
        assert msg["is_alert_sender"] == special_msg["is_alert_sender"]
        assert msg["is_alert_manager"] == special_msg["is_alert_manager"]
        assert msg["is_caller"] == special_msg["is_caller"]

def test_get_messages_check_messages_details_case_2(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    access_token = test_baseuser['access_token']
    assert user is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a local alert where test_baseuser is an alerted user
    statement = (select(AlertedUser, Alert)
            .join(Alert, AlertedUser.alert_id==Alert.id) # type: ignore
            .where(AlertedUser.user_id == user.id)
            .where(Alert.type == AlertType.local.value))
    result = db_session.exec(statement).first()
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alerted_user.alert_id == alert.id
    assert alerted_user.user_id == user.id
    # It's a local alert
    assert alert.type == AlertType.local.value
    # We simulate that the first alerted user is the alerted manager.
    statement = select(AlertedUser).where(AlertedUser.alert_id==alert.id)
    alerted_user = db_session.exec(statement).first()
    # There is for sure at least one alerted user for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert alerted_user is not None
    # We simulate that the first alerted user is the alerted manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We select all messages (by alerted users) for this alert, joined with user's info
    statement = (select(Message, AlertedUser, User)
            .join(AlertedUser, AlertedUser.user_id==Message.user_id) # type: ignore
            .join(User, AlertedUser.user_id==User.id) # type: ignore
            .where(Message.alert_id==alert.id, AlertedUser.alert_id==alert.id))
    results = db_session.exec(statement).all()
    print(f"Found {len(results)} messages from alerted users for alert id={alert.id}")
    # Now we construct a special messages map, where the key is the message id, 
    # and each element is a dict with the related user's info
    # It's useful to check the messages details later.
    # Note: we must add the sender's messages too, 
    # because the join done above will return only the messages from the alerted users
    special_messages_map = {}
    for r in results:
        m = r[0] # the message in result
        assert m.id is not None
        assert m.alert_id == alert.id
        au = r[1] # the alerted_user in result
        u = r[2] # the user in result
        if au.is_manager == True:
            print(f"Alerted user {u.firstname} {u.surname} (email={u.email}) is the alerted manager for alert_id={alert.id}, message_id={m.id}")
        special_messages_map[str(m.id)] = {
            "firstname": u.firstname,
            "surname": u.surname,
            "user_role": u.role,
            "is_alert_sender": (u.id == alert.user_id),
            "is_alert_manager": au.is_manager, # for local alerts, the alert manager is the alerted user with is_manager=True, not the alert sender
            "is_caller": (u.id == test_baseuser['user'].id)
        }
    sender_messages_stmt = (select(Message, User)
                .join(User, User.id==Message.user_id) # type: ignore
                .where(Message.alert_id==alert.id, Message.user_id==alert.user_id))
    results = db_session.exec(sender_messages_stmt).all()
    print(f"Found {len(results)} messages from alert sender for alert id={alert.id}")
    for m, u in results:
        special_messages_map[str(m.id)] = {
            "firstname": u.firstname,
            "surname": u.surname,
            "user_role": u.role,
            "is_alert_sender": (u.id == alert.user_id),
            "is_alert_manager": False, # for local alerts, the alert manager is the alerted user with is_manager=True, not the alert sender
            "is_caller": (u.id == test_baseuser['user'].id)
        }
    special_messages_length = len(special_messages_map)
    print(f"Total messages in special messages map for alert id={alert.id}: {special_messages_length}")
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    messages = response_data["messages"]
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    assert len(messages) == special_messages_length
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["id"] is not None
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg
        # Now we check that the message details match the info contained in special_messages_map
        special_msg = special_messages_map.get(str(msg["id"]))
        assert special_msg is not None
        # Now we check that the message details match the alerted user info
        assert msg["user_role"] == special_msg["user_role"]
        assert msg["is_alert_sender"] == special_msg["is_alert_sender"]
        assert msg["is_alert_manager"] == special_msg["is_alert_manager"]
        assert msg["is_caller"] == special_msg["is_caller"]

def test_get_messages_check_messages_details_case_3(client, db_session, test_chief):
    chief: User = test_chief['user']
    access_token = test_chief['access_token']
    assert chief is not None, "No user found in the database for testing"
    assert access_token is not None, "No access token found in the database for testing"
    # We select a managed alert where test_chief is the alert sender (and alert manager)
    # Note: in non-local alerts, the alert manager is the alert sender
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.managed.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    # It's a managed alert
    assert alert.type == AlertType.managed.value
    assert alert.user_id == chief.id
    # In non-local alerts, all messages are sent only by the alert sender (the manager)
    messages = db_session.exec(select(Message).where(Message.alert_id==alert.id)).all()
    assert len(messages) > 0
    # Now we call the API and we verify it's successful
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}/messages", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    messages = response_data["messages"]
    # There are for sure some messages for this alert
    # (see the fixture setup_alerts_data_and_teardown in fixtures/alerts.py)
    assert len(messages) > 0
    for msg in messages:
        # Each message is originated from MessageOut model, not Message model, 
        # so user_id is not present. Content and created_at are not null.
        assert "user_id" not in msg
        assert msg["id"] is not None
        assert msg["content"] is not None
        assert msg["created_at"] is not None
        assert msg["firstname"] is not None
        assert msg["surname"] is not None
        assert "user_role" in msg
        assert "is_alert_sender" in msg
        assert "is_alert_manager" in msg
        assert "is_caller" in msg
        assert msg["user_role"] == chief.role
        assert msg["firstname"] == chief.firstname
        assert msg["surname"] == chief.surname
        assert msg["is_alert_sender"] == True
        assert msg["is_alert_manager"] == True
        # The caller here is the alert sender (test_chief), 
        # so is_caller is True for this test case
        assert msg["is_caller"] == True
