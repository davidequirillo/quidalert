# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from unittest.mock import ANY
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception,
    not_found_exception,
    invalid_request_exception
)
from models.general import (
    User, RefreshToken, 
    Alert, AlertType, ClosingType, AlertedUser,
    CLOSING_VOTE_POSITIVE, CLOSING_VOTE_NEGATIVE, 
    CLOSING_VOTE_NEUTRAL, CLOSING_VOTE_PUNITIVE,
    HERO_SCORE_INC_VALUE_TO_ALERT_SENDER,
    HERO_SCORE_INC_VALUE_TO_ALERTED_USERS,
    Message
)
from services.alert_btasks import (
    alert_notification_templates
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required fixture (manually called as argument in test functions when needed)
    setup_fake_functions, # required (fixture automatically called)
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
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario.
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario 
    # (hero score is a game mechanic, and it can increase to virtually infinity, but here for simplicity we generate a random value between 0 and 100).
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    alert_sender.reliability_score = random.randint(0, 100)
    alert_sender.hero_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    sender_hero_score = alert_sender.hero_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    hero_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario.
    # We also set his hero score to random values between 0 and 100, to simulate a realistic scenario.
    for au_user, user in results:
        user.reliability_score = random.randint(0, 100)
        user.hero_score = random.randint(0, 100)
        au_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        hero_scores_map[str(user.id)] = user.hero_score
        votes_map[str(au_user.user_id)] = au_user.vote
        db_session.add(user)
        db_session.add(au_user)
    db_session.commit()
    alert_id = alert.id
    closing_type = ClosingType.positive.value
    # The closing vote for a positive closing type is +30 points
    closing_vote = CLOSING_VOTE_POSITIVE
    hero_score_add_to_sender = HERO_SCORE_INC_VALUE_TO_ALERT_SENDER
    hero_score_add_to_alerted_users = HERO_SCORE_INC_VALUE_TO_ALERTED_USERS
    # Now we call the close alert api endpoint with a positive closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users 
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alerted_user)
    assert alerted_user.closing_vote == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have increased by closing_vote points, but not exceed 100
    # The alert sender's hero score should have increased by hero_score_add_to_sender points
    assert alert_sender.reliability_score == min(sender_rel_score + abs(closing_vote), 100)
    assert alert_sender.hero_score == sender_hero_score + hero_score_add_to_sender
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have increased by int(closing_vote/2) points if their vote was positive (1), 
    # they have decreased by int(closing_vote/2) points if their vote was negative (-1), 
    # unchanged if their vote was neutral (0), 
    # but for all, they should not exceed 100 or go below 0
    # ---------------------------
    # We also check the hero scores of all alerted users (except the caller, who is the alert manager), and we expect that:
    # they have increased by hero_score_add_to_alerted_users points if their vote was positive (1), 
    # because they voted positively for the alert, and the alert was closed positively (by chief manager)
    for au_user, user in results:
        db_session.refresh(user)
        db_session.refresh(au_user)
        if au_user.user_id != caller.id:
            user_vote = votes_map[str(au_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            user_hero_score = hero_scores_map[str(user.id)]
            if user_vote == +1:
                expected_rel_score = min(user_rel_score + abs(int(closing_vote/2)), 100)
                expected_hero_score = user_hero_score + hero_score_add_to_alerted_users
            elif user_vote == -1:
                expected_rel_score = max(user_rel_score - abs(int(closing_vote/2)), 0)
                expected_hero_score = user_hero_score
            else:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            assert user.reliability_score == expected_rel_score
            assert user.reliability_score <= 100
            assert user.reliability_score >= 0
            assert user.hero_score == expected_hero_score
            assert user.hero_score >= 0

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
    # and we set his reliability score to a random value between 0 and 100, to simulate a realistic scenario.
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario.
    # (hero score is a game mechanic, and it can increase to virtually infinity, but here for simplicity we generate a random value between 0 and 100).
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    alert_sender.reliability_score = random.randint(0, 100)
    alert_sender.hero_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    sender_hero_score = alert_sender.hero_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    hero_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario.
    # We also set his hero score to random values between 0 and 100, to simulate a realistic scenario
    for au_user, user in results:
        user.reliability_score = random.randint(0, 100)
        user.hero_score = random.randint(0, 100)
        au_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        hero_scores_map[str(user.id)] = user.hero_score
        votes_map[str(au_user.user_id)] = au_user.vote
        db_session.add(user)
        db_session.add(au_user)
    db_session.commit()
    alert_id = alert.id
    closing_type = ClosingType.negative.value
    # The closing vote for a negative closing type is -30 points
    closing_vote = CLOSING_VOTE_NEGATIVE
    hero_score_add_to_alerted_users = HERO_SCORE_INC_VALUE_TO_ALERTED_USERS
    # Now we call the close alert api endpoint with a negative closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alerted_user)
    assert alerted_user.closing_vote == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have decreased by abs(closing_vote) points, but not go below 0
    # The alert sender's hero score should have remained unchanged, because the chief manager has closed the alert negatively
    assert alert_sender.reliability_score == max(sender_rel_score - abs(closing_vote), 0)
    assert alert_sender.hero_score == sender_hero_score
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have increased by int(abs(closing_vote)/2) points if their vote was negative (-1),
    # they have decreased by int(abs(closing_vote)/2) points if their vote was positive (+1),
    # unchanged if their vote was neutral (0),
    # their reliability score should not go below 0 or exceed 100
    # ---------------------------
    # We also check the hero scores of all alerted users (except the caller, who is the alert manager), and we expect that:
    # they have increased by hero_score_add_to_alerted_users points if their vote was negative (-1), 
    # because they voted negatively, and the alert was closed the same way (by the chief manager)
    for au_user, user in results:
        db_session.refresh(user)
        db_session.refresh(au_user)
        if au_user.user_id != caller.id:
            user_vote = votes_map[str(au_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            user_hero_score = hero_scores_map[str(user.id)]
            if user_vote == -1:
                expected_rel_score = min(user_rel_score + abs(int(closing_vote/2)), 100)
                expected_hero_score = user_hero_score + hero_score_add_to_alerted_users
            elif user_vote == +1:
                expected_rel_score = max(user_rel_score - abs(int(closing_vote/2)), 0)
                expected_hero_score = user_hero_score
            else:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            assert user.reliability_score == expected_rel_score
            assert user.reliability_score <= 100
            assert user.reliability_score >= 0
            assert user.hero_score == expected_hero_score
            assert user.hero_score >= 0

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
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario
    # (hero score is a game mechanic, and it can increase to virtually infinity, but here for simplicity we generate a random value between 0 and 100).
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    assert alert_sender is not None
    alert_sender.reliability_score = random.randint(0, 100)
    alert_sender.hero_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    sender_hero_score = alert_sender.hero_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    hero_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario, 
    for au_user, user in results:
        user.reliability_score = random.randint(0, 100)
        user.hero_score = random.randint(0, 100)
        au_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        hero_scores_map[str(user.id)] = user.hero_score
        votes_map[str(au_user.user_id)] = au_user.vote
        db_session.add(user)
        db_session.add(au_user)
    db_session.commit()
    # We call the close alert api endpoint with a neutral closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    # The closing vote for a neutral closing type is 0 points
    closing_vote = CLOSING_VOTE_NEUTRAL
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alerted_user)
    assert alerted_user.closing_vote == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have remained unchanged, because the closing vote is 0
    assert alert_sender.reliability_score == sender_rel_score
    assert alert_sender.hero_score == sender_hero_score
    # We check the reliability scores and hero scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have remained unchanged, because the closing vote is 0 (neutral closing)
    for au_user, user in results:
        db_session.refresh(user)
        db_session.refresh(au_user)
        if au_user.user_id != caller.id:
            user_vote = votes_map[str(au_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            user_hero_score = hero_scores_map[str(user.id)]
            if user_vote == -1:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            elif user_vote == +1:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            else:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            assert user.reliability_score == expected_rel_score
            assert user.reliability_score <= 100
            assert user.reliability_score >= 0
            assert user.hero_score == expected_hero_score
            assert user.hero_score >= 0

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
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario
    # (hero score is a game mechanic, and it can increase to virtually infinity, but here for simplicity we generate a random value between 0 and 100).
    alert_sender_stmt = select(User).where(User.id == alert.user_id)
    alert_sender = db_session.exec(alert_sender_stmt).first()
    assert alert_sender is not None
    alert_sender.reliability_score = random.randint(0, 100)
    alert_sender.hero_score = random.randint(0, 100)
    sender_rel_score = alert_sender.reliability_score
    sender_hero_score = alert_sender.hero_score
    db_session.add(alert_sender)
    db_session.commit()
    # We select all alerted users for this alert, with User information
    statement = (select(AlertedUser, User).join(User, AlertedUser.user_id == User.id) # type: ignore
            .where(AlertedUser.alert_id == alert.id))
    results = db_session.exec(statement).all()
    reliability_scores_map = {}
    hero_scores_map = {}
    votes_map = {}
    # For each alerted user, we set his reliability score to random values between 0 and 100, to simulate a realistic scenario, 
    # and we set his vote to random values in [-1, 0, 1] to simulate a realistic scenario
    # We also set his hero score to a random value between 0 and 100, to simulate a realistic scenario,
    for au_user, user in results:
        user.reliability_score = random.randint(0, 100)
        user.hero_score = random.randint(0, 100)
        au_user.vote = random.randint(-1, 1)
        reliability_scores_map[str(user.id)] = user.reliability_score
        hero_scores_map[str(user.id)] = user.hero_score
        votes_map[str(au_user.user_id)] = au_user.vote
        db_session.add(user)
        db_session.add(au_user)
    db_session.commit()
    # We call the close alert api endpoint with a neutral closing type, which should be allowed for local alerts,
    # and we check the effect on reliability scores of the alert sender and alerted users
    alert_id = alert.id
    closing_type = ClosingType.punitive.value
    # The closing vote for a punitive closing type is -100 points
    closing_vote = CLOSING_VOTE_PUNITIVE
    hero_score_add_to_alerted_users = HERO_SCORE_INC_VALUE_TO_ALERTED_USERS
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    response_data = response.json()
    assert response_data["closing_type"] == closing_type
    assert response_data["closing_vote"] == closing_vote
    db_session.refresh(alerted_user)
    assert alerted_user.closing_vote == closing_vote
    db_session.refresh(alert_sender)
    # The alert sender's reliability score should have decreased to 0, because the closing vote is -100 (punitive closing)
    # The alert sender's hero score is reset to 0, because it's a punitive closing
    assert alert_sender.reliability_score == max(sender_rel_score - abs(closing_vote), 0)
    assert alert_sender.reliability_score == 0
    assert alert_sender.hero_score == 0 * sender_hero_score
    assert alert_sender.hero_score == 0
    # We check the reliability scores of all alerted users (except the caller, who is the alert manager), and we expect that: 
    # they have increased by int(abs(closing_vote)/2) points if their vote was negative (-1),
    # they have decreased by int(abs(closing_vote)/2) points if their vote was positive (+1),
    # unchanged if their vote was neutral (0),
    # their reliability score should not go below 0 or exceed 100
    # ---------------------------
    # We also check the hero scores of all alerted users (except the caller, who is the alert manager), and we expect that:
    # they have increased by hero_score_add_to_alerted_users points if their vote was negative (-1), 
    # because they voted negatively, and the alert was closed the same way (by the chief manager).
    # They have their hero score reset to 0 if their vote was positive (+1), 
    # because they voted positively, the opposite of the chief manager closing type (punitive)
    for au_user, user in results:
        db_session.refresh(user)
        db_session.refresh(au_user)
        if au_user.user_id != caller.id:
            user_vote = votes_map[str(au_user.user_id)]
            user_rel_score = reliability_scores_map[str(user.id)]
            user_hero_score = hero_scores_map[str(user.id)]
            if user_vote == -1:
                expected_rel_score = min(user_rel_score + abs(int(closing_vote/2)), 100)
                expected_hero_score = user_hero_score + hero_score_add_to_alerted_users
            elif user_vote == +1:
                expected_rel_score = max(user_rel_score - abs(int(closing_vote/2)), 0)
                expected_hero_score = 0
            else:
                expected_rel_score = user_rel_score
                expected_hero_score = user_hero_score
            assert user.reliability_score == expected_rel_score
            assert user.reliability_score <= 100
            assert user.reliability_score >= 0
            assert user.hero_score == expected_hero_score
            assert user.hero_score >= 0
    # The alert should be banned (is_banned=True) because it was closed with a punitive closing type
    # All related messages should be banned too (is_banned=True)
    db_session.refresh(alert)
    assert alert.is_banned == True
    messages_stmt = select(Message).where(Message.alert_id == alert.id)
    messages = db_session.exec(messages_stmt).all()
    for message in messages:
        assert message.is_banned == True

def test_close_alert_local_punitive_messages_banned(client, db_session, test_chief):
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
    # We insert a few messages for this alert, 
    # to test that they will be banned when the alert is closed with a punitive closing type
    for i in range(5):
        message = Message(
            alert_id=alert.id,
            user_id=caller.id,
            content=f"Test message {i+1} for alert {alert.id}",
            is_banned=False
        )
        db_session.add(message)
    db_session.commit()
    # We call the close alert api endpoint with a punitive closing type, which should be allowed for local alerts,
    # and we check that the alert and all related messages are banned (is_banned=True)
    alert_id = alert.id
    closing_type = ClosingType.punitive.value
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    db_session.refresh(alert)
    db_session.refresh(alerted_user)
    assert alerted_user.closing_vote == CLOSING_VOTE_PUNITIVE
    # The alert should be banned (is_banned=True) because it was closed with a punitive closing type
    assert alert.is_banned == True
    # All related messages should be banned too (is_banned=True)
    messages_stmt = select(Message).where(Message.alert_id == alert.id)
    messages = db_session.exec(messages_stmt).all()
    for message in messages:
        assert message.is_banned == True

def test_close_alert_notifications_for_type_general(client, db_session, test_chief, setup_fake_functions):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a general alert created by test_chief (the sender)
    statement = (select(Alert).where(Alert.type == AlertType.general.value)
            .where(Alert.user_id == caller.id))
    alert = db_session.exec(statement).first()
    assert alert is not None
    # We call the close alert api endpoint with a neutral closing type, which should be allowed
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    # For general alerts, there should be no notification sent to the sender or any user, 
    # because general alerts are not associated with any alerted users.
    # (the background task is not called for general or empty alerts)
    setup_fake_functions["mock_notify_about_closure"].assert_not_called()

def test_close_alert_notifications_for_type_empty(client, db_session, test_chief, setup_fake_functions):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select an empty alert created by test_chief (the sender)
    statement = (select(Alert).where(Alert.type == AlertType.empty.value)
            .where(Alert.user_id == caller.id))
    alert = db_session.exec(statement).first()
    assert alert is not None
    # We call the close alert api endpoint with a neutral closing type, which should be allowed
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    # For empty alerts, there should be no notification sent to the sender or any user, 
    # because empty alerts are not associated with any alerted users.
    # (the background task is not called for general or empty alerts)
    setup_fake_functions["mock_notify_about_closure"].assert_not_called()

def test_close_alert_notifications_for_type_local(client, db_session, test_chief, setup_fake_functions):
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
    # We select the alert sender (joined with refresh token)
    # The sender has a refresh token with fcm_token not None 
    # (see setup_users_data_and_teardown fixture, which creates a refresh token with fcm_token for each user)
    statement = (select(User, RefreshToken).join(
        RefreshToken, RefreshToken.user_id == User.id)  # type: ignore
        .where(User.id == alert.user_id)
        .where(RefreshToken.fcm_token != None))
    result = db_session.exec(statement).first()
    sender = result[0]
    sender_refresh_token = result[1]
    assert sender is not None
    assert sender_refresh_token is not None
    assert sender_refresh_token.fcm_token is not None
    # We also select all alerted users (joined with refresh tokens) for this alert
    statement = (select(AlertedUser, RefreshToken).join(
        RefreshToken, RefreshToken.user_id == AlertedUser.user_id)  # type: ignore
        .where(AlertedUser.alert_id == alert.id)
        .where(RefreshToken.fcm_token != None))
    results = db_session.exec(statement).all()
    alerted_users = []
    refresh_tokens = []
    # The implementation excludes the alert manager from the list of alerted users to notify, 
    # so we simulate this scenario by filtering out the alert manager (test_chief) from the list of alerted users to notify.
    for res in results:
        if (res[0].is_manager == False):
            alerted_users.append(res[0])
            refresh_tokens.append(res[1])
    # There should be at least one alerted user (except the alert manager) with fcm_token not None
    # (see setup_alerts_data_and_teardown fixture and setup_users_data_and_teardown fixture, 
    # which creates a local alert with at least one alerted user with fcm_token)
    assert len(alerted_users) > 0
    assert len(refresh_tokens) > 0
    for rt in refresh_tokens:
        assert rt.fcm_token is not None
    # The sender and all alerted users (except the manager) will be notified about the closure of the alert
    users_to_notify_ids = [au.user_id for au in alerted_users]
    users_to_notify_ids.insert(0, sender.id)
    users_to_notify_fcm_tokens = [rt.fcm_token for rt in refresh_tokens]
    users_to_notify_fcm_tokens.insert(0, sender_refresh_token.fcm_token)
    # We call the close alert api endpoint with a neutral closing type, which should be allowed
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    db_session.refresh(alert)
    # For local alerts, there should be a notification sent to the sender and all alerted users
    # (the background task is called for local alerts)
    # Note: in the implementation of alert notifications, we use the caller's language for simplicity
    # (we could use the language of each receiving user, in a future improvement of the system, if possible)
    language = caller.language
    msg_type = "close_alert"
    msg_title = alert_notification_templates[language]["close_alert_title"]
    msg_body = alert_notification_templates[language]["close_alert_text"].format(
        date=alert.created_at.strftime("%Y-%m-%d"),
        hour=alert.created_at.strftime("%H:%M"),
        closing_type=closing_type
    )
    setup_fake_functions["mock_notify_about_closure"].assert_called_once()
    args, kwargs = setup_fake_functions["mock_notify_about_closure"].call_args
    print("Number of notified user ids: ", len(args[1]), "fcm_tokens: ", len(args[2]))
    # We check that the notified user ids and fcm tokens 
    # (used inside the mock_notify_about_closure call) 
    # match the alerted users (plus the sender) for this local alert, 
    # and message type, title and body are correct
    for id in users_to_notify_ids:
        assert str(id) in args[1]
    for fcm_token in users_to_notify_fcm_tokens:
        assert fcm_token in args[2]
    assert kwargs["type"] == msg_type
    assert kwargs["title"] == msg_title
    assert kwargs["content"] == msg_body

def test_close_alert_notifications_for_type_managed(client, db_session, test_chief, setup_fake_functions):
    caller: User = test_chief["user"]
    assert caller is not None
    access_token: str = test_chief["access_token"]
    # We select a managed alert created by test_chief (the sender)
    statement = (select(Alert).where(Alert.type == AlertType.managed.value)
            .where(Alert.user_id == caller.id))
    alert = db_session.exec(statement).first()
    assert alert is not None
    # We select all alerted users (joined with refresh tokens) for this alert
    statement = (select(AlertedUser, RefreshToken).join(
        RefreshToken, RefreshToken.user_id == AlertedUser.user_id)  # type: ignore
        .where(AlertedUser.alert_id == alert.id)
        .where(RefreshToken.fcm_token != None))
    results = db_session.exec(statement).all()
    alerted_users = []
    refresh_tokens = []
    for res in results:
        alerted_users.append(res[0])
        refresh_tokens.append(res[1])
    # There are for sure some alerted users for this managed alert 
    # (see setup_alerts_data_and_teardown fixture)
    assert len(alerted_users) > 0
    assert len(refresh_tokens) > 0
    # There is no alerted manager because the alert is managed, 
    # so the alert manager is the alert sender (test_chief)
    for alerted_user in alerted_users:
        assert alerted_user.is_manager == False
    alerted_user_ids = [au.user_id for au in alerted_users]
    alerted_user_fcm_tokens = [rt.fcm_token for rt in refresh_tokens]
    for fcm_token in alerted_user_fcm_tokens:
        assert fcm_token is not None
    # We call the close alert api endpoint with a neutral closing type, which should be allowed
    alert_id = alert.id
    closing_type = ClosingType.neutral.value
    # For managed alerts, there should be a notification sent to all alerted users
    # (the background task is called for managed alerts)
    # Note: in the implementation of alert notifications, we use the caller's language for simplicity
    # (we could use the language of each receiving user, in a future improvement of the system, if possible)
    language = caller.language
    msg_type = "close_alert"
    msg_title = alert_notification_templates[language]["close_alert_title"]
    msg_body = alert_notification_templates[language]["close_alert_text"].format(
            date=alert.created_at.strftime("%Y-%m-%d"),
            hour=alert.created_at.strftime("%H:%M"),
            closing_type=closing_type
        )
    response = client.post(
        f"/api/alerts/{alert_id}/close", json={"type": closing_type}, headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    assert "alert closed successfully" in response.json()["message"].lower()
    db_session.refresh(alert)
    setup_fake_functions["mock_notify_about_closure"].assert_called_once()
    args, kwargs = setup_fake_functions["mock_notify_about_closure"].call_args
    # We check that the notified user ids and fcm tokens 
    # (used inside the mock_notify_about_closure call) 
    # match the alerted users for this managed alert,
    # and message type, title and body are correct
    for id in alerted_user_ids:
        assert str(id) in args[1]
    for fcm_token in alerted_user_fcm_tokens:
        assert fcm_token in args[2]
    assert kwargs["type"] == msg_type
    assert kwargs["title"] == msg_title
    assert kwargs["content"] == msg_body
