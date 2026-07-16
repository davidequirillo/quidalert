# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select, delete
from core.exceptions import (
    not_found_exception,
    token_not_valid_exception,
    forbidden_exception
)
from models.general import (
    User, Alert, AlertType, 
    AlertedUser, Message
)
from services.security import now_tz_naive
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
)

def test_get_alert_not_authorized_missing_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_alert_not_authorized_invalid_token(client, db_session):
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    response = client.get(
        f"/api/alerts/{alert_id}", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_alert_not_found(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser['access_token']
    statement = select(Alert)
    alert = db_session.exec(statement).first()
    # There is at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    # We delete the alert to simulate a not found scenario
    db_session.exec(delete(Alert).where(Alert.id == alert_id))
    db_session.commit()
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception("Alert not found").status_code
    assert "Alert not found" in response.json()["detail"]

def test_get_alert_user_not_found(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser['access_token']
    statement = select(Alert, User).join(User, Alert.user_id == User.id) # type: ignore
    result = db_session.exec(statement).first()
    # There is at least one alert with related user (see setup_alerts_data_and_teardown fixture)
    assert result is not None, "No alert and user found in the database for testing"
    alert, sender = result
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    assert sender is not None, "No user found in the database for testing"
    sender_id = sender.id
    # We delete the user (the sender) to simulate a not found scenario
    db_session.exec(delete(User).where(User.id == sender_id))
    db_session.commit()
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception("Alert not found").status_code
    assert "Alert not found" in response.json()["detail"]

def test_get_alert_success_but_is_banned(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser['access_token']
    statement = select(Alert, User).join(User, Alert.user_id == User.id) # type: ignore
    result = db_session.exec(statement).first()
    # There is at least one alert with related user (see setup_alerts_data_and_teardown fixture)
    assert result is not None, "No alert and user found in the database for testing"
    alert, sender = result
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    assert sender is not None, "No user found in the database for testing"
    # We set "is_banned" field of the alert, to simulate a banned alert scenario
    alert.is_banned = True
    db_session.add(alert)
    db_session.commit()
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_obj = response.json()
    assert resp_obj["alert"]["description"] == "[BANNED ALERT]"

def test_get_alert_success_general_alert(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None, "No user found in the database for testing"
    access_token = test_baseuser['access_token']
    statement = select(Alert, User).join(User, Alert.user_id == User.id).where(Alert.type == AlertType.general.value) # type: ignore
    result = db_session.exec(statement).first()
    # There is at least one alert with related user (see setup_alerts_data_and_teardown fixture)
    assert result is not None, "No alert and user found in the database for testing"
    alert, sender = result
    assert alert is not None, "No alert found in the database for testing"
    alert_id = alert.id
    assert sender is not None, "No user found in the database for testing"
    # A general alert cannot have alerted users, 
    # but it can have messages (coming from the alert sender, which is a chief)
    messages = db_session.exec(select(Message).where(Message.alert_id == alert.id)).all()
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_obj = response.json()
    assert resp_obj["alert"]["id"] == alert.id
    assert resp_obj["alert"]["description"] == alert.description
    assert resp_obj["alert"]["type"] == alert.type
    assert resp_obj["alert"]["latitude"] <= alert.latitude + 0.0001 
    assert resp_obj["alert"]["latitude"] >= alert.latitude - 0.0001
    assert resp_obj["alert"]["longitude"] <= alert.longitude + 0.0001
    assert resp_obj["alert"]["longitude"] >= alert.longitude - 0.0001
    assert resp_obj["alert"]["created_at"] == alert.created_at.isoformat()
    # Test_baseuser (the caller) has not high privileges, so he cannot read "sender" object completely.
    # He can only read sender's firstname, surname and reliability_score, 
    # but not the other data (for example email, phone, address, etc.)
    assert resp_obj["sender"] is None
    assert resp_obj["sender_firstname"] == sender.firstname
    assert resp_obj["sender_surname"] == sender.surname
    assert resp_obj["sender_reliability_score"] == sender.reliability_score
    # For non-local alerts the chief is the sender
    assert resp_obj["chief_firstname"] == sender.firstname
    assert resp_obj["chief_surname"] == sender.surname
    # It's a general alert (no alerted users)
    assert resp_obj["alerted_users_num"] == 0
    assert resp_obj["positive_votes_num"] == 0
    assert resp_obj["negative_votes_num"] == 0
    assert resp_obj["messages_num"] == len(messages)
    # It's a general alert (there are not any alerted users or voters)
    assert resp_obj["user_is_alerted"] is False
    assert resp_obj["user_is_manager"] is False
    assert resp_obj["user_vote"] == 0
    # The API caller (test_baseuser) is not the alert sender in this test
    assert resp_obj["user_is_sender"] is False

def test_get_alert_local_created_by_me(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None
    access_token = test_baseuser['access_token']
    statement = select(Alert).where(Alert.user_id == caller.id, Alert.type == AlertType.local.value) # type: ignore
    alert = db_session.exec(statement).first()
    # There is at least one local alert created by the caller (see setup_alerts_data_and_teardown fixture)
    assert alert is not None
    assert alert.user_id == caller.id
    assert alert.type == AlertType.local.value
    # And this alert has some alerted users (see setup_alerts_data_and_teardown fixture)
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_obj = response.json()
    assert resp_obj["alert"]["id"] == alert.id
    assert resp_obj["alert"]["description"] == alert.description
    assert resp_obj["alert"]["type"] == alert.type
    assert resp_obj["alert"]["latitude"] <= alert.latitude + 0.0001 
    assert resp_obj["alert"]["latitude"] >= alert.latitude - 0.0001
    assert resp_obj["alert"]["longitude"] <= alert.longitude + 0.0001
    assert resp_obj["alert"]["longitude"] >= alert.longitude - 0.0001
    assert resp_obj["alert"]["created_at"] == alert.created_at.isoformat()
    # Little security check: the user_id of the alert (sender user_id) should not be exposed in the API response 
    # (API returns AlertOut object, not Alert object)
    assert "user_id" not in resp_obj["alert"]
    # The caller (test_baseuser) is the alert sender in this test, 
    # but the caller has not high privileges, so he cannot read "sender" object completely.
    assert resp_obj["sender"] is None
    assert resp_obj["sender_firstname"] == caller.firstname
    assert resp_obj["sender_surname"] == caller.surname
    assert resp_obj["sender_reliability_score"] == caller.reliability_score
    # It's a local alert created by the caller (no alerted users)
    assert resp_obj["alerted_users_num"] == len(alerted_users)
    assert resp_obj["positive_votes_num"] == 0
    assert resp_obj["negative_votes_num"] == 0
    # The caller is the alert sender, so he is not an alerted user,
    # and even more, the caller is not the alert manager
    # and he cannot vote, because he is not an alerted user
    assert resp_obj["user_is_alerted"] is False
    assert resp_obj["user_is_manager"] is False
    assert resp_obj["user_vote"] == 0
    # The API caller (test_baseuser) is the alert sender in this test
    assert resp_obj["user_is_sender"] is True

def test_get_alert_not_created_by_me_and_not_involved(client, db_session, test_baseuser, test_chief):
    caller: User = test_baseuser['user']
    chief: User = test_chief['user']
    assert caller is not None
    assert chief is not None
    access_token = test_baseuser['access_token']
    # We select a non-general alert, not created by the caller
    # It's a "managed" alert created by test_chief user (see setup_alerts_data_and_teardown fixture)
    # In this fixture, all the alerts of type "managed" created by test_chief don't involve test_baseuser,
    # so, test_baseuser is not inserted as alerted user (he is not involved), and he can't see the alert
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.managed.value) # type: ignore
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.user_id == test_chief["user"].id
    assert alert.type == AlertType.managed.value
    # This alert has some alerted users for sure (see setup_alerts_data_and_teardown fixture),
    # and the caller is not one of them (see setup_alerts_data_and_teardown fixture)
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    for alerted_user in alerted_users:
        assert alerted_user.user_id != caller.id
    # Now we can test the API endpoint to get the alert details
    # The result is a forbidden error
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
 
def test_get_alert_not_created_by_me_but_involved(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None
    access_token = test_baseuser['access_token']
    # We select an alert_id of a non-general alert,
    # where the caller is an alerted user (he is involved in the alert)
    statement = select(AlertedUser).where(AlertedUser.user_id == caller.id)
    alerted_caller = db_session.exec(statement).first()
    # The caller (test_baseuser) is an alerted user for at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alerted_caller is not None
    # We extract the alert in which the caller is involved (he is an alerted user)
    alert = db_session.exec(select(Alert).where(Alert.id == alerted_caller.alert_id)).first()
    assert alert is not None
    assert alert.type != AlertType.general.value
    found_caller_in_alerted_users = False
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    for alerted_user in alerted_users:
        if alerted_user.user_id == caller.id:
            found_caller_in_alerted_users = True
            break
    assert found_caller_in_alerted_users
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    # The caller (test_baseuser) has not high privileges (he cannot read sender object completely)
    assert resp_data["sender"] is None
    assert resp_data["sender_firstname"] is not None
    assert resp_data["sender_surname"] is not None
    assert resp_data["sender_reliability_score"] is not None
    assert resp_data["alerted_users_num"] == len(alerted_users)
    # The caller is an alerted user for this alert, so he is involved in the alert
    # But the caller (a base user) cannot be the alert manager
    # The caller can vote, because he is an alerted user, but he has not voted yet in this test (vote=0)
    assert resp_data["user_is_alerted"] is True
    assert resp_data["user_is_manager"] is False
    assert resp_data["user_vote"] == 0
    # The API caller (test_baseuser) is not the alert sender in this test
    assert resp_data["user_is_sender"] is False

def test_get_alert_not_created_by_me_not_involved_but_caller_is_officer(client, db_session, test_officer, test_baseuser):
    caller: User = test_officer['user']
    baseuser: User = test_baseuser['user']
    assert caller is not None
    assert baseuser is not None
    access_token = test_officer['access_token']
    # We select an alert_id of a non-general alert, 
    # where test_officer is not the alert sender, and is not an alerted user
    # We take a local alert created by test_baseuser (see setup_alerts_data_and_teardown fixture), 
    # We can see that test_officer is not an alerted user for this alert
    statement = select(Alert).where(Alert.user_id == baseuser.id, Alert.type == AlertType.local.value) # type: ignore
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id == baseuser.id
    # Now we check that test_officer is not an alerted user for this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    for alerted_user in alerted_users:
        assert alerted_user.user_id != caller.id
    # So, if test_officer calls the API endpoint to get the alert details, 
    # he should receive a forbidden error
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    # But, if the alert sender has been authorized by the test_officer,
    # then test_officer can see the alert details, because the alert sender belongs to his jurisdiction
    # We simulate this scenario, setting the "authorized_by" field of the alert sender to the test_officer email
    # We remember that the alert sender is test_baseuser
    assert baseuser.id == alert.user_id
    baseuser.authorized_by = caller.email
    db_session.add(baseuser)
    db_session.commit()
    db_session.refresh(baseuser)
    # Now, if test_officer calls the API endpoint to get the alert details,
    # he should receive a success response, because the alert sender belongs to his jurisdiction
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    # The caller (test_officer) has not high privileges (he is not a chief or an admin),
    # so he cannot read "sender" object completely (only firstname, surname and reliability_score are visible)
    assert resp_data["sender"] is None
    assert resp_data["sender_firstname"] == baseuser.firstname
    assert resp_data["sender_surname"] == baseuser.surname
    assert resp_data["sender_reliability_score"] == baseuser.reliability_score
    assert resp_data["alerted_users_num"] == len(alerted_users)
    # The API caller (test_officer) is not an alerted user in this test
    # so, even more, he is not the alert manager
    # and he cannot vote, because he is not an alerted user
    assert resp_data["user_is_alerted"] == False
    assert resp_data["user_is_manager"] == False
    assert resp_data["user_vote"] == 0
    # The API caller (test_officer) is not the alert sender in this test
    assert resp_data["user_is_sender"] == False

def test_get_alert_called_by_a_chief(client, db_session, test_chief, test_baseuser):
    caller: User = test_chief['user']
    baseuser: User = test_baseuser['user']
    assert caller is not None
    assert baseuser is not None
    access_token = test_chief['access_token']
    # We select an alert_id of a non-general alert, 
    # where test_chief is not the alert sender, and is not an alerted user
    # We take a local alert created by test_baseuser (see setup_alerts_data_and_teardown fixture), 
    # We can see that test_chief is not an alerted user for this alert
    statement = select(Alert).where(Alert.user_id == baseuser.id, Alert.type == AlertType.local.value) # type: ignore
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id != caller.id
    # Now we check that test_chief is not an alerted user for this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    for alerted_user in alerted_users:
        assert alerted_user.user_id != caller.id
    # But the caller is a chief, so he can see the alert details anyway, 
    # even if he is not the alert sender and is not an alerted user
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    # The caller (test_chief) has high privileges (he is a chief), 
    # so he can read "sender" object completely
    assert resp_data["sender"] is not None
    resp_data_sender = resp_data["sender"]
    assert resp_data_sender["id"] == str(baseuser.id)
    assert resp_data_sender["email"] == baseuser.email
    assert resp_data_sender["phone"] == baseuser.phone
    assert resp_data_sender["street"] == baseuser.street
    assert resp_data_sender["city"] == baseuser.city
    assert "password" not in resp_data_sender
    assert "password_hash" not in resp_data_sender
    assert "activation_token" not in resp_data_sender
    assert resp_data_sender["birthdate"] == baseuser.birthdate
    assert resp_data["sender_firstname"] == baseuser.firstname
    assert resp_data["sender_surname"] == baseuser.surname
    assert resp_data["sender_reliability_score"] == baseuser.reliability_score
    assert resp_data["alerted_users_num"] == len(alerted_users)
    # The API caller (test_chief) is not an alerted user in this test
    # and even more, he is not the alert manager
    # and he cannot vote, because he is not an alerted user
    # and he is not the alert sender
    assert resp_data["user_is_alerted"] == False
    assert resp_data["user_is_manager"] == False
    assert resp_data["user_is_sender"] == False
    assert resp_data["user_vote"] == 0

def test_get_alert_called_by_admin(client, db_session, test_admin, test_baseuser):
    caller: User = test_admin['user']
    baseuser: User = test_baseuser['user']
    assert caller is not None
    assert baseuser is not None
    access_token = test_admin['access_token']
    # We select an alert_id of a non-general alert, 
    # where test_admin is not the alert sender, and is not an alerted user
    # We take a local alert created by test_baseuser (see setup_alerts_data_and_teardown fixture), 
    # We can see that test_admin is not an alerted user for this alert
    statement = select(Alert).where(Alert.user_id == baseuser.id, Alert.type == AlertType.local.value) # type: ignore
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.local.value
    assert alert.user_id != caller.id
    # Now we check that test_admin is not an alerted user for this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    assert len(alerted_users) > 0
    for alerted_user in alerted_users:
        assert alerted_user.user_id != caller.id
    # But the caller is an admin, so he can see the alert details anyway, 
    # even if he is not the alert sender and is not an alerted user
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    # The caller (test_admin) has high privileges (he is an admin), 
    # so he can read "sender" object completely
    assert resp_data["sender"] is not None
    resp_data_sender = resp_data["sender"]
    assert resp_data_sender["id"] == str(baseuser.id)
    assert resp_data_sender["email"] == baseuser.email
    assert resp_data_sender["phone"] == baseuser.phone
    assert resp_data_sender["street"] == baseuser.street
    assert resp_data_sender["city"] == baseuser.city
    assert resp_data_sender["birthdate"] == baseuser.birthdate
    assert "password" not in resp_data_sender
    assert "password_hash" not in resp_data_sender
    assert "activation_token" not in resp_data_sender
    assert resp_data["sender_firstname"] == baseuser.firstname
    assert resp_data["sender_surname"] == baseuser.surname
    assert resp_data["sender_reliability_score"] == baseuser.reliability_score
    assert resp_data["alerted_users_num"] == len(alerted_users)
    
def test_get_alert_check_votes_count_and_chief_alerted(client, db_session, test_officer, test_chief):
    caller: User = test_officer['user']
    chief: User = test_chief['user']
    assert caller is not None
    assert chief is not None
    access_token = test_officer['access_token']
    # We select an alert_id of a local alert, 
    # where the alert sender is test_officer, see setup_alerts_data_and_teardown fixture.
    # Between alerts created by test_officer, we select one alert in which test_chief is an alerted user
    statement = select(Alert).where(Alert.user_id == caller.id, Alert.type == AlertType.local.value) # type: ignore
    alerts = db_session.exec(statement).all()
    assert len(alerts) > 0
    alert_ids = [a.id for a in alerts]
    statement = (select(AlertedUser)
        .where(AlertedUser.user_id == chief.id)
        .where(AlertedUser.alert_id.in_(alert_ids)) # type: ignore
    )
    alerted_chief = db_session.exec(statement).first()
    # The chief (test_chief) is an alerted user for at least one alert (see setup_alerts_data_and_teardown fixture)
    # We simulate the scenario in which the chief is the alert manager (alerted user with is_manager=True)
    assert alerted_chief is not None
    alerted_chief.is_manager = True
    db_session.add(alerted_chief)
    db_session.commit()
    db_session.refresh(alerted_chief)
    # We extract the related alert (in which the chief is an alerted user)
    alert = db_session.exec(select(Alert).where(Alert.id == alerted_chief.alert_id)).first()
    assert alert is not None
    assert alert.type != AlertType.general.value
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == alert.id)).all()
    # Now we random modify the votes (positive, negative, or zero) 
    # of some alerted user and we set the closing vote of alert manager
    alerted_chief_closing_vote = 0
    for i, alerted_user in enumerate(alerted_users):
        if alerted_user.is_manager:
            alerted_user.closing_vote = -20
            alerted_chief_closing_vote = alerted_user.closing_vote
        if i % 3 == 0:
            alerted_user.vote = 1
        if i % 3 == 1:
            alerted_user.vote = -1
        if i % 3 == 2:
            alerted_user.vote = 0
        db_session.add(alerted_user)
    db_session.commit()
    alerted_chief_user = db_session.exec(select(User).where(User.id == alerted_chief.user_id)).first()
    assert alerted_chief_user is not None
    alerted_chief_firstname = alerted_chief_user.firstname
    alerted_chief_surname = alerted_chief_user.surname
    # We check the presence of alert messages
    statement = select(Message).where(Message.alert_id == alert.id)
    alert_messages = db_session.exec(statement).all()
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    assert resp_data["sender_firstname"] == caller.firstname
    assert resp_data["sender_surname"] == caller.surname
    assert resp_data["sender_reliability_score"] == caller.reliability_score
    assert resp_data["alerted_users_num"] == len(alerted_users)
    assert resp_data["positive_votes_num"] == sum(1 for au in alerted_users if au.vote > 0)
    assert resp_data["negative_votes_num"] == sum(1 for au in alerted_users if au.vote < 0)
    assert resp_data["chief_firstname"] == alerted_chief_firstname
    assert resp_data["chief_surname"] == alerted_chief_surname
    assert resp_data["chief_closing_vote"] != 0 
    assert resp_data["chief_closing_vote"] == alerted_chief_closing_vote
    assert resp_data["messages_num"] == len(alert_messages)
    # The API caller (test_officer) is not an alerted user in this test
    # and even more, he is not the alert manager
    # and he cannot vote, because he is not an alerted user
    assert resp_data["user_is_alerted"] == False
    assert resp_data["user_is_manager"] == False
    assert resp_data["user_vote"] == 0
    # The API caller (test_officer) is the alert sender in this test
    assert resp_data["user_is_sender"] == True

def test_get_alert_the_caller_has_voted(client, db_session, test_baseuser):
    caller: User = test_baseuser['user']
    assert caller is not None
    access_token = test_baseuser['access_token']
    # We select an alert_id of a non-general alert, 
    # where the caller is an alerted user (he is involved in the alert)
    statement = select(AlertedUser).where(AlertedUser.user_id == caller.id)
    alerted_caller = db_session.exec(statement).first()
    # The caller (test_baseuser) is an alerted user for at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alerted_caller is not None
    # We extract the alert in which the caller is involved (he is an alerted user)
    alert = db_session.exec(select(Alert).where(Alert.id == alerted_caller.alert_id)).first()
    assert alert is not None
    assert alert.type != AlertType.general.value
    # Now we set a vote for the caller (alerted user) to simulate that he has voted
    alerted_caller.vote = 1
    db_session.add(alerted_caller)
    db_session.commit()
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    assert resp_data["user_is_alerted"] is True
    assert resp_data["user_is_manager"] is False
    assert resp_data["user_vote"] == 1
    # The API caller (test_baseuser) is not the alert sender in this test
    assert resp_data["user_is_sender"] is False

def test_get_alert_the_caller_is_manager(client, db_session, test_chief):
    caller: User = test_chief['user']
    assert caller is not None
    access_token = test_chief['access_token']
    # We select an alert_id of a non-general alert, 
    # where the caller is an alerted user (he is involved in the alert)
    statement = select(AlertedUser).where(AlertedUser.user_id == caller.id)
    alerted_caller = db_session.exec(statement).first()
    # The caller (test_chief) is an alerted user for at least one alert (see setup_alerts_data_and_teardown fixture)
    assert alerted_caller is not None
    # We extract the alert in which the caller is involved (he is an alerted user)
    alert = db_session.exec(select(Alert).where(Alert.id == alerted_caller.alert_id)).first()
    assert alert is not None
    assert alert.type != AlertType.general.value
    # Now we set the caller as manager for this alert
    alerted_caller.is_manager = True
    db_session.add(alerted_caller)
    db_session.commit()
    # Now we can test the API endpoint to get the alert details,
    # and we verify that the results are the same of the results obtained from database
    alert_id = alert.id
    response = client.get(f"/api/alerts/{alert_id}", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    resp_data = response.json()
    assert resp_data["alert"]["id"] == alert.id
    assert resp_data["alert"]["type"] == alert.type
    assert resp_data["alert"]["description"] == alert.description
    assert resp_data["user_is_alerted"] is True
    assert resp_data["user_is_manager"] is True
    assert resp_data["user_vote"] == 0
    # The API caller (test_chief) is not the alert sender in this test
    assert resp_data["user_is_sender"] is False
