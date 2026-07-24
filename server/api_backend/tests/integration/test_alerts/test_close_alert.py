# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception,
    not_found_exception,
    invalid_request_exception
)
from models.general import (
    User, Alert, AlertType, ClosingType, AlertedUser
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required fixture (manually called as argument in test functions when needed)
)

def test_close_alert_not_authorized_missing_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    alert_id = test_alert.id
    response = client.post(f"/api/alerts/{alert_id}/close", json={"type": "neutral"})
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_close_alert_not_authorized_invalid_token(client, test_alert):
    assert test_alert is not None, "No alert found in the database for testing"
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": "neutral"}, headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_close_alert_called_by_non_chief_user(client, test_alert, test_baseuser):
    caller: User = test_baseuser["user"]
    assert caller is not None
    access_token: str = test_baseuser["access_token"]
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": "neutral"}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "only chiefs can close alerts" in response.json()["detail"].lower()

def test_close_alert_not_found(client, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    non_existent_alert_id = 999999  # Assuming this ID does not exist in the database
    response = client.post(
        f"/api/alerts/{non_existent_alert_id}/close", json={"type": "neutral"}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "alert not found" in response.json()["detail"].lower()

def test_close_alert_with_invalid_closing_type(client, test_chief, test_alert):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    alert_id = test_alert.id
    invalid_closing_type = "invalid_type"
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": invalid_closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_close_alert_already_closed(client, db_session, test_alert, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    alert_id = test_alert.id
    # We simulate closing the alert for the first time
    test_alert.is_closed = True  # Mark the alert as closed
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": "neutral"}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert already closed" in response.json()["message"].lower()
    db_session.refresh(test_alert)
    assert test_alert.is_closed == True

def test_close_alert_not_local_alert_success(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a non-local alert from the database for testing
    statement = select(Alert).where(Alert.type != AlertType.local.value)
    non_local_alert = db_session.exec(statement).first()
    # The alert has been created by test_chief user (see setup_alerts_data_and_teardown fixture)
    # so, test_chief (caller) is the chief alert manager of this alert, and he can close it.
    assert non_local_alert.user_id == caller.id
    assert non_local_alert.is_closed == False
    alert_id = non_local_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": "neutral"}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == ClosingType.neutral.value
    assert response_data["closing_vote"] == 0
    db_session.refresh(non_local_alert)
    assert non_local_alert.is_closed == True

def test_close_alert_not_local_alert_called_by_not_manager(client, db_session, test_chief, test_baseuser):
    caller: User = test_baseuser["user"]
    assert caller is not None
    access_token: str = test_baseuser["access_token"]
    # We select a non-local alert from the database for testing
    statement = select(Alert).where(Alert.type != AlertType.local.value)
    non_local_alert = db_session.exec(statement).first()
    # The alert is open and has been created by test_chief user (see setup_alerts_data_and_teardown fixture)
    # so, test_baseuser (caller) is NOT the chief alert manager of this alert, and he cannot close it, 
    # even if he would be a chief user, because he is not the manager of this alert.
    # Note: for non-local alerts, the chief alert manager is the alert sender (the user who created the alert), and only him can close it.
    assert non_local_alert.user_id != caller.id
    assert non_local_alert.user_id == test_chief["user"].id
    assert non_local_alert.is_closed == False
    caller.is_chief = True  # We simulate that the caller is a chief user
    db_session.add(caller)
    db_session.commit()
    db_session.refresh(caller)
    alert_id = non_local_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": "neutral"}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "only the chief alert sender (manager) can close this alert" in response.json()["detail"].lower()
    db_session.refresh(non_local_alert)
    # The alert should still be open, because the caller is not the manager of this alert
    assert non_local_alert.is_closed == False

def test_close_alert_not_local_alert_not_neutral_closing(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a non-local alert from the database for testing
    statement = select(Alert).where(Alert.type != AlertType.local.value)
    non_local_alert = db_session.exec(statement).first()
    # The alert is open and has been created by test_chief user (see setup_alerts_data_and_teardown fixture)
    # so, test_chief (caller) is the chief alert manager of this alert, and he can close it.
    assert non_local_alert.user_id == caller.id
    assert non_local_alert.is_closed == False
    # But we try to close it with a non-neutral closing, which should not be allowed
    alert_id = non_local_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": ClosingType.punitive.value}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == invalid_request_exception().status_code
    assert "non-local alerts can be closed only in a neutral way" in response.json()["detail"].lower()
    db_session.refresh(non_local_alert)
    # The alert should still be open, because the closing type was not neutral
    assert non_local_alert.is_closed == False

def test_close_alert_local_called_by_not_manager(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert, 
    # but he is not the alert manager (an alerted user with is_manager=True), 
    # so test_chief (caller) cannot close it.
    # Note: for local alerts, the alert manager is the alerted user with is_manager=True, and only him can close it. 
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    assert alerted_user.is_manager == False
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": ClosingType.neutral.value}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "only the chief alert manager can close this alert" in response.json()["detail"].lower()
    db_session.refresh(alert)
    # The alert should still be open, because the caller is not the manager of this alert
    assert alert.is_closed == False

def test_close_alert_local_called_by_manager(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert.
    # We simulate that test_chief is the alert manager (an alerted user with is_manager=True),
    # so test_chief (caller) can close it.
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": ClosingType.neutral.value}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    db_session.refresh(alert)
    # The alert should now be closed, because the caller is the manager of this alert
    assert alert.is_closed == True
    response_data = response.json()
    assert response_data["closing_type"] == ClosingType.neutral.value
    assert response_data["closing_vote"] == 0

def test_close_alert_local_positive_closing(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert.
    # We simulate that test_chief is the alert manager (an alerted user with is_manager=True),
    # so test_chief (who is also the api caller) can close it.
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    assert alerted_user.user_id == caller.id
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We select the alert sender (the user who created the alert) 
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    alert_sender.reliability_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    for alerted_user, user in results:
        user.reliability_score = random.randint(0, 100)
        alerted_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        votes_map[str(alerted_user.user_id)] = alerted_user.vote
        db_session.add(user)
        db_session.add(alerted_user)
    db_session.commit()
    alert_id = alert.id
    closing_type = ClosingType.positive.value
    # The closing vote for a positive closing type is +30 points
    closing_vote = 30
    # Now we call the close alert api endpoint with a positive closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users 
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have increased by closing_vote points, but not exceed 100
    assert alert_sender.reliability_score == min(sender_rel_score + abs(closing_vote), 100)
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have increased by int(closing_vote/2) points if their vote was positive (1), 
    # they have decreased by int(closing_vote/2) points if their vote was negative (-1), 
    # unchanged if their vote was neutral (0), 
    # but for all, they should not exceed 100 or go below 0
    for alerted_user, user in results:
        db_session.refresh(user)
        db_session.refresh(alerted_user)
        if alerted_user.user_id != caller.id:
            user_vote = votes_map[str(alerted_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            if user_vote == +1:
                expected_score = min(user_rel_score + abs(int(closing_vote/2)), 100)
            elif user_vote == -1:
                expected_score = max(user_rel_score - abs(int(closing_vote/2)), 0)
            else:
                expected_score = user_rel_score
            assert user.reliability_score == expected_score

def test_close_alert_local_negative_closing(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert.
    # We simulate that test_chief is the alert manager (an alerted user with is_manager=True),
    # so test_chief (who is also the api caller) can close it.
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    assert alerted_user.user_id == caller.id
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    db_session.refresh(alerted_user)
    # We select the alert sender (the user who created the alert) 
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    alert_sender.reliability_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    for alerted_user, user in results:
        user.reliability_score = random.randint(0, 100)
        alerted_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        votes_map[str(alerted_user.user_id)] = alerted_user.vote
        db_session.add(user)
        db_session.add(alerted_user)
    db_session.commit()
    alert_id = alert.id
    closing_type = ClosingType.negative.value
    # The closing vote for a negative closing type is -30 points
    closing_vote = -30
    # Now we call the close alert api endpoint with a negative closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have decreased by abs(closing_vote) points, but not go below 0
    assert alert_sender.reliability_score == max(sender_rel_score - abs(closing_vote), 0)
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have increased by int(abs(closing_vote)/2) points if their vote was negative (-1),
    # they have decreased by int(abs(closing_vote)/2) points if their vote was positive (+1),
    # unchanged if their vote was neutral (0),
    # their reliability score should not go below 0 or exceed 100
    for alerted_user, user in results:
        db_session.refresh(user)
        db_session.refresh(alerted_user)
        if alerted_user.user_id != caller.id:
            user_vote = votes_map[str(alerted_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            if user_vote == -1:
                expected_score = min(user_rel_score + abs(int(closing_vote/2)), 100)
            elif user_vote == +1:
                expected_score = max(user_rel_score - abs(int(closing_vote/2)), 0)
            else:
                expected_score = user_rel_score
            assert user.reliability_score == expected_score

def test_close_alert_local_neutral_closing(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert.
    # We simulate that test_chief is the alert manager (an alerted user with is_manager=True),
    # so test_chief (who is also the api caller) can close it.
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    assert alerted_user.user_id == caller.id
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # We select the alert sender (the user who created the alert) 
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    assert alert_sender is not None
    alert_sender.reliability_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    for alerted_user, user in results:
        user.reliability_score = random.randint(0, 100)
        alerted_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        votes_map[str(alerted_user.user_id)] = alerted_user.vote
        db_session.add(user)
        db_session.add(alerted_user)
    db_session.commit()
    # We call the close alert api endpoint with a neutral closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    # The closing vote for a neutral closing type is 0 points
    closing_vote = 0
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have remained unchanged, because the closing vote is 0
    assert alert_sender.reliability_score == sender_rel_score
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have remained unchanged, because the closing vote is 0
    for alerted_user, user in results:
        db_session.refresh(user)
        db_session.refresh(alerted_user)
        if alerted_user.user_id != caller.id:
            user_vote = votes_map[str(alerted_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            if user_vote == -1:
                expected_score = user_rel_score
            elif user_vote == +1:
                expected_score = user_rel_score
            else:
                expected_score = user_rel_score
            assert user.reliability_score == expected_score

def test_close_alert_local_punitive_closing(client, db_session, test_chief):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a local alert in which test_chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type: ignore
            .where(Alert.type == AlertType.local.value)
            .where(AlertedUser.user_id == caller.id))
    result = db_session.exec(statement).first()
    alerted_user = result[0]
    alert = result[1]
    # The local alert is open and has been created by another user,
    # and test_chief is an alerted user for this alert.
    # We simulate that test_chief is the alert manager (an alerted user with is_manager=True),
    # so test_chief (who is also the api caller) can close it.
    assert alert.user_id != caller.id
    assert alert.is_closed == False
    assert alerted_user.user_id == caller.id
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # We select the alert sender (the user who created the alert) 
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    assert alert_sender is not None
    alert_sender.reliability_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    for alerted_user, user in results:
        user.reliability_score = random.randint(0, 100)
        alerted_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        votes_map[str(alerted_user.user_id)] = alerted_user.vote
        db_session.add(user)
        db_session.add(alerted_user)
    db_session.commit()
    # We call the close alert api endpoint with a neutral closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    alert_id = alert.id
    closing_type = ClosingType.punitive.value
    # The closing vote for a punitive closing type is -100 points
    closing_vote = -100