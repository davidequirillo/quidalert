# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from unittest.mock import ANY
from fastapi import status
from sqlmodel import select, update
from core.exceptions import (
    token_not_valid_exception,
    not_found_exception,
    forbidden_exception
)
from models.general import (
    RefreshToken, 
    User, UserRole,
    Alert, AlertType, AlertedUser,
    ALERT_SPREAD_MAX_COUNT
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
    create_test_alert, # required by the fixture named "test_alert", and manually called as function argument when needed in test cases.
    setup_fake_functions
)

def test_expand_alert_not_authorized_missing_token(client, test_alert):
    assert test_alert is not None
    assert test_alert.id is not None
    data = {
        "radius": 30.0,
        "role": UserRole.wateroperator.value
    }
    alert_id = test_alert.id
    response = client.post(f"/api/alerts/{alert_id}/expand", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_expand_alert_not_authorized_invalid_token(client, test_alert):
    assert test_alert is not None
    assert test_alert.id is not None
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = test_alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_expand_alert_invalid_input_data(client, test_baseuser, test_alert):
    alert_id = test_alert.id
    access_token = test_baseuser['access_token']
    data = {
        "radius": 30.0,
        "role": "invalid_role"
    }
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Now we try with a negative radius
    data = {
        "radius": -10.0,
        "role": UserRole.usar.value
    }
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_expand_alert_called_by_not_chief(client, db_session, test_alert, test_baseuser):
    user: User = test_baseuser['user']
    alert: Alert = test_alert 
    assert user is not None
    access_token = test_baseuser['access_token']
    data = {
        "radius": 30.0,
        "role": UserRole.policeman.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Only chiefs can expand alerts" in response.json()["detail"]

def test_expand_alert_not_found(client, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = 111111111 # An alert id that does not exist in the database
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == not_found_exception().status_code
    assert "Alert not found" in response.json()["detail"]

def test_expand_alert_is_closed(client, db_session, test_alert, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    alert: Alert = test_alert
    # We set the alert as not pending, but closed
    alert.is_pending = False
    alert.is_closed = True
    db_session.add(alert)
    db_session.commit()
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Alert is closed" in response.json()["detail"]

def test_expand_alert_is_pending(client, db_session, test_alert, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    alert: Alert = test_alert
    assert alert.is_closed is False
    # Test alert is created with is_pending=True by default (for testing purposes),
    # so we don't need to set it explicitly, but we can assert it
    assert alert.is_pending is True
    db_session.add(alert)
    db_session.commit()
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Alert is in pending status" in response.json()["detail"]

def test_expand_alert_max_spread_count_reached(client, db_session, test_alert, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    alert: Alert = test_alert
    # We set the alert as not closed, not pending,
    # and we set the alert's spread count to the maximum, 
    # to simulate that the alert has already been expanded the maximum number of times allowed
    alert.is_pending = False
    alert.is_closed = False
    alert.spread_count = ALERT_SPREAD_MAX_COUNT
    db_session.add(alert)
    db_session.commit()
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Alert has reached the maximum number of expansions" in response.json()["detail"]

def test_expand_alert_local_called_by_a_chief_not_manager(client, db_session, test_chief):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # Now we select a local alert where the chief is an alerted user, 
    # but not the alert manager (it means the chief is a generic alerted user, 
    # but not the alerted user who is also the manager of the alert).
    # Remember: for local alerts, the alert manager is an alerted user with is_manager=True
    statement = (select(AlertedUser, Alert)
            .join(Alert, AlertedUser.alert_id == Alert.id) # type:ignore
            .where(AlertedUser.alert_id == Alert.id, AlertedUser.user_id == chief.id, AlertedUser.is_manager == False, Alert.type == AlertType.local.value)
        )
    result = db_session.exec(statement).first()
    # We assert that the result is not None, 
    # because there is for sure a local alert where the chief is an alerted user
    # (see setup_alerts_data_and_teardown fixture).
    assert result is not None
    alerted_user = result[0]
    assert alerted_user is not None
    assert alerted_user.is_manager == False
    alert = result[1]
    assert alert is not None
    assert alert.type == AlertType.local.value
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    # Now we call the API endpoint to expand the alert
    # The caller is the test_chief, who is a chief user, but not the alert manager of the alert
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Only the chief alert manager can expand this alert" in response.json()["detail"]

def test_expand_alert_non_local_called_by_a_chief_not_manager(client, db_session, test_chief, test_baseuser):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select an alert sent by test_baseuser, and we make it a non-local alert, 
    # to simulate a non-local alert where test_chief is not the alert manager (the alert sender in this case).
    # Note: for non-local alerts, the alert manager is the chief alert sender.
    # In this case, we want to test that a chief user who is not the alert manager (alert sender) cannot expand a non-local alert.
    statement = select(Alert).where(Alert.user_id == test_baseuser['user'].id)
    alert = db_session.exec(statement).first()
    alert.type = AlertType.managed.value
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    # Now we call the API endpoint to expand the alert, and we expect that the test_chief, 
    # who is a chief user but not the alert manager (alert sender), cannot expand the non-local alert.
    data = {
        "radius": 30.0,
        "role": UserRole.military.value
    }
    alert_id = alert.id
    # Now we call the API endpoint to expand the alert
    # The caller is the test_chief, who is a chief user, but not the alert manager of the alert
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "Only the chief alert sender (manager) can expand this alert" in response.json()["detail"]

def test_expand_alert_type_general_not_allowed(client, db_session, test_chief):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select a general alert, to simulate that the alert type is general, 
    # and we want to test that expanding a general alert is not allowed.
    statement = select(Alert).where(Alert.type == AlertType.general.value)
    alert = db_session.exec(statement).first()
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    # Now we call the API endpoint to expand the alert
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == forbidden_exception().status_code
    assert "General alerts can't be expanded" in response.json()["detail"]

def test_expand_alert_local_success(client, db_session, test_chief):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select a local alert where the chief is an alerted user
    statement = (select(AlertedUser, Alert)
            .join(Alert, AlertedUser.alert_id == Alert.id) # type:ignore
            .where(AlertedUser.user_id == chief.id, Alert.type == AlertType.local.value)
        )
    result = db_session.exec(statement).first()
    # We assert that the result is not None,
    # because there is for sure a local alert where the chief is an alerted user
    # (see setup_alerts_data_and_teardown fixture).
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    # We simulate that the chief is the alert manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # The spread count is 0 for alerts created by 
    # the setup_alerts_data_and_teardown fixture, so we assert it
    current_spread_count = alert.spread_count
    assert alert.spread_count == current_spread_count
    assert alert.is_expanded is False
    assert alert.radius == 1
    # We get all current alerted users related to this alert
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # There are at least some alerted users (see setup_alerts_data_and_teardown fixture), 
    # because the fixture is created in such a way that the alert has some alerted users, so we assert it
    assert alerted_users_num > 0
    # Now we call the API endpoint to expand the alert
    data = {
        "radius": 30.0,
        "role": UserRole.firefighter.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(alert)
    # We get alerted users 
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_expansion = db_session.exec(statement).all()
    alerted_users_after_expansion_num = len(alerted_users_after_expansion)
    # If the number of alerted users after the expansion is greater than the number of alerted users before the expansion,
    # it means that new users have been added as alerted users, so the spread count is incremented by 1.
    # If not (if firefighters specialists are not found in the alert radius), the spread count remains the same.
    if alerted_users_after_expansion_num > alerted_users_num:
        assert alert.spread_count == current_spread_count + 1
        current_spread_count = alert.spread_count
    assert alert.is_expanded is True
    assert alert.is_pending is False
    # The alert radius is the same because the expansion is performed only on a specific role, 
    # not on all users, so alert.radius is not changed.
    assert alert.radius == 1
    # If we do the same expansion with role equal to None,
    # alert.radius change to the new radius
    data = {
            "radius": 30.0,
            "role": None
        }
    response = client.post(
            f"/api/alerts/{alert_id}/expand", json=data,
            headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    assert alert.is_expanded is True
    # The spread count is incremented because during the second expansion (with role None),
    # new users have been added as alerted users for sure: in the previous expansion we have expanded only to firefighters specialists, 
    # but now we have expanded to all users, so new users have been added as alerted users for sure.
    assert alert.spread_count == current_spread_count + 1
    assert alert.is_pending is False
    # The alert.radius is now changed to the new radius, 
    # because the expansion is performed with role=None
    assert alert.radius == 30.0

def test_expand_alert_local_success_verify_notifications_called(client, db_session, test_chief, setup_fake_functions):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select a local alert where the chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type:ignore
            .where(AlertedUser.user_id == chief.id, Alert.type == AlertType.local.value)
        )
    result = db_session.exec(statement).first()
    # We assert that the result is not None,
    # because there is for sure a local alert where the chief is an alerted user
    # (see setup_alerts_data_and_teardown fixture).
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    # We simulate that the chief is the alert manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # The spread count is 0 for alerts created by 
    # the setup_alerts_data_and_teardown fixture, so we assert it
    assert alert.spread_count == 0
    assert alert.is_expanded is False
    assert alert.radius == 1
    # We count the number of alerted users before the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # There are at least some alerted users (see setup_alerts_data_and_teardown fixture),
    # because the fixture is created in such a way that the alert has some alerted users, so we assert it
    assert alerted_users_num > 0
    # Now we call the API endpoint to expand the alert
    data = {
        "radius": 30.0,
        "role": None
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    # We count the number of alerted users after the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_1st_expansion = db_session.exec(statement).all()
    alerted_users_after_1st_expansion_ids = [str(alerted_user.user_id) for alerted_user in alerted_users_after_1st_expansion]
    alerted_users_after_1st_expansion_num = len(alerted_users_after_1st_expansion)
    new_alerted_users_num = alerted_users_after_1st_expansion_num - alerted_users_num
    assert alert.is_expanded is True
    # The spread count is incremented because during the expansion (with role None),
    # new users have been added as alerted users for sure.
    assert alert.spread_count == 1
    assert alert.is_pending is False
    assert alert.radius == 30.0
    # We verify that alert notifications have been called, 
    # to send notifications to the following users:
    # 1. the chief manager
    # 2. the alert sender
    # 3. new alerted users
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_with(
        str(chief.id), ANY, 
        chief.language, ANY, 
        30.0, None, new_alerted_users_num,
        ANY, ANY)
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_called_with(
        str(alert.user_id), ANY, 
        chief.language, ANY,
        ANY, ANY)
    setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_called_once()
    args, _ = setup_fake_functions["mock_notify_nearby_users_about_expansion"].call_args
    notified_nearby_user_ids: list[str] = args[0] # the first argument is the list of notified user ids
    for user_id in notified_nearby_user_ids:
        assert user_id in alerted_users_after_1st_expansion_ids
    # During alert expansion, the number of notified nearby users must be equal to the number of new alerted users added 
    # (not all existing alerted users are notified, only the new ones added during the expansion)
    assert len(notified_nearby_user_ids) == new_alerted_users_num
    # Now we do another expansion with a lesser radius, 
    # to verify that the number of new alerted users is 0,
    # because the previous expansion has already added all the nearby users within the previous greater radius.
    data = {
        "radius": 10.0,
        "role": None
    }
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    # The alert.radius is not changed because is less than the previous radius
    assert alert.radius == 30.0
    assert alert.is_expanded is True
    # Spread count not changed because no new users have been added as alerted users in the second expansion.
    assert alert.spread_count == 1
    # We verify that the number of alerted users after the second expansion
    # is equal to the number of alerted users after the first expansion, 
    # because the second expansion has a lesser radius, so no new users are added as alerted users.
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_2nd_expansion = db_session.exec(statement).all()
    alerted_users_after_2nd_expansion_ids = [str(alerted_user.user_id) for alerted_user in alerted_users_after_2nd_expansion]
    alerted_users_after_2nd_expansion_num = len(alerted_users_after_2nd_expansion)
    assert alerted_users_after_2nd_expansion_num == alerted_users_after_1st_expansion_num
    assert alerted_users_after_2nd_expansion_ids == alerted_users_after_1st_expansion_ids
    
def test_expand_alert_local_success_but_no_new_users(client, db_session, test_chief, setup_fake_functions):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select a local alert where the chief is an alerted user
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type:ignore
        .where(AlertedUser.user_id == chief.id, Alert.type == AlertType.local.value)
    )
    result = db_session.exec(statement).first()
    # We assert that the result is not None,
    # because there is for sure a local alert where the chief is an alerted user
    # (see setup_alerts_data_and_teardown fixture).
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    # We simulate that the chief is the alert manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # The spread count is 0 for alerts created by 
    # the setup_alerts_data_and_teardown fixture, so we assert it
    assert alert.spread_count == 0
    assert alert.is_expanded is False
    assert alert.radius == 1
    # We count the number of alerted users before the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # There are at least some alerted users (see setup_alerts_data_and_teardown fixture),
    # because the fixture is created in such a way that the alert has some alerted users, so we assert it
    assert alerted_users_num > 0
    # Now we call the API endpoint to expand the alert with a radius that is too small to find new users
    data = {
        "radius": 0.000000000001, # A very small radius to simulate that no new users are found
        "role": None
    }
    response = client.post(
        f"/api/alerts/{alert.id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    # The alert radius is not changed because it is less than the previous alert.radius
    assert alert.radius == 1
    assert alert.is_expanded is True
    # Spread count not changed because no new users have been added
    assert alert.spread_count == 0
    # We verify that the number of alerted users after the expansion
    # is equal to the number of alerted users before the expansion.
    # In other words, no new users have been added as alerted users
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_expansion = db_session.exec(statement).all()
    alerted_users_after_expansion_num = len(alerted_users_after_expansion)
    assert alerted_users_after_expansion_num == alerted_users_num
    # We verify that alert notifications have been called
    # for the chief manager, the alert sender, but not for nearby users, 
    # because no new users have been added as alerted users during the expansion.
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_with(
        str(chief.id), ANY,
        chief.language, ANY,
        ANY, None, 0,
        ANY, ANY
    )
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_called_with(
        str(alert.user_id), ANY,
        chief.language, ANY,
        ANY, ANY
    )
    setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_not_called()

def test_expand_alert_local_success_but_no_fcm_tokens(client, db_session, test_chief, setup_fake_functions):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We remove all FCM tokens from the database 
    # to simulate the case where no users have FCM tokens, so no notifications can be sent.
    update_statement = (update(RefreshToken)
                .where(RefreshToken.fcm_token != None) # type:ignore
                .values(fcm_token=None)
    )
    db_session.exec(update_statement)
    # We select a local alert where test_chief is an alerted user
    # The alert is local for sure (see setup_alerts_data_and_teardown)
    statement = (select(AlertedUser, Alert).join(Alert, AlertedUser.alert_id == Alert.id) # type:ignore
            .where(AlertedUser.user_id == chief.id, Alert.type == AlertType.local.value)
        )
    result = db_session.exec(statement).first()
    # We assert that the result is not None,
    # because there is for sure a local alert where the chief is an alerted user
    # (see setup_alerts_data_and_teardown fixture).
    assert result is not None
    alerted_user = result[0]
    alert = result[1]
    assert alerted_user is not None
    assert alert is not None
    assert alert.type == AlertType.local.value
    # We simulate that the chief is the alert manager
    alerted_user.is_manager = True
    db_session.add(alerted_user)
    db_session.commit()
    # The spread count is 0 for alerts created by 
    # the setup_alerts_data_and_teardown fixture, so we assert it
    assert alert.spread_count == 0
    assert alert.is_expanded is False
    assert alert.radius == 1
    # We count the number of alerted users before the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # There are at least some alerted users (see setup_alerts_data_and_teardown fixture),
    # because the fixture is created in such a way that the alert has some alerted users, so we assert it
    assert alerted_users_num > 0
    # Now we call the API endpoint to expand the alert
    data = {
        "radius": 30.0, # in km, a radius that is large enough to find new users, but they have no FCM tokens, so they are not save in database and not notified
        "role": None
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    # We count the number of alerted users in database after the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_expansion = db_session.exec(statement).all()
    alerted_users_after_expansion_num = len(alerted_users_after_expansion)
    new_alerted_users_num = alerted_users_after_expansion_num - alerted_users_num
    # We assert that new_alerted_users_num is equal to 0, because during the expansion (with role None),
    # no new users have been added (in database) as alerted users,
    # because all the users found in the zone have no FCM token, so they are not saved in database as alerted users.
    assert new_alerted_users_num == 0
    # The spread count is not incremented because during the expansion (with role None),
    # no new users have been added as alerted users due to the lack of FCM tokens.
    assert alert.is_expanded is True
    assert alert.spread_count == 0
    assert alert.is_pending is False
    assert alert.radius == 30.0
    # No notification has been sent because 
    # the chief manager has no FCM token, the alert sender has no FCM token,
    # and new alerted users have no FCM token
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_not_called()
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_not_called()
    setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_not_called()

def test_expand_alert_managed_success(client, db_session, test_chief, setup_fake_functions):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select a managed alert where the chief is the alert sender (manager)
    # There is for sure a managed alert where the sender is test_chief (see setup_alerts_data_and_teardown)
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.managed.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.managed.value
    assert alert.is_closed is False
    assert alert.is_pending is False
    # The spread count is 0 for alerts created by 
    # the setup_alerts_data_and_teardown fixture, so we assert it
    assert alert.spread_count == 0
    assert alert.is_expanded is False
    assert alert.radius > 0
    assert alert.radius < 10
    # We count the number of alerted users before the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # There are at least some alerted users (see setup_alerts_data_and_teardown fixture), 
    # because the fixture is created in such a way that the alert has some alerted users, so we assert it
    assert alerted_users_num > 0
    # Now we call the API endpoint to expand the alert
    data = {
        "radius": 30.0,
        "role": UserRole.alpinerescuer.value
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    # We count the number of alerted users after the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users_after_expansion = db_session.exec(statement).all()
    new_alerted_users_num = len(alerted_users_after_expansion) - alerted_users_num
    assert alert.is_expanded is True
    if new_alerted_users_num > 0:
        assert alert.spread_count == 1
    else:
        assert alert.spread_count == 0
    assert alert.is_pending is False
    # The alert.radius is not changed because the expansion is performed only on a specific role,
    # not on all users, so alert.radius is not changed.
    assert alert.radius > 0
    assert alert.radius < 10
    # We verify that alert notifications have been called,
    # to send notifications to the following users:
    # 1. the chief manager
    # 2. new alerted users (if any)
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_with(
        str(chief.id), ANY,
        chief.language, ANY,
        30.0, UserRole.alpinerescuer.value, new_alerted_users_num,
        ANY, ANY
    )
    # For non-local alerts, the alert sender is the chief manager, so no notification is sent to the alert sender.
    # (because we notify the chief manager, who is the alert sender, and we don't notify the same user twice)
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_not_called()
    if new_alerted_users_num > 0:
        setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_called_once()
    else:
        setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_not_called()

def test_expand_alert_type_empty_success(client, db_session, test_chief, setup_fake_functions):
    # Test_chief is a chief user
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # We select an alert where the chief is the alert sender (manager)
    # The alert type is "empty"
    statement = select(Alert).where(Alert.user_id == chief.id, Alert.type == AlertType.empty.value)
    alert = db_session.exec(statement).first()
    assert alert is not None
    assert alert.type == AlertType.empty.value
    assert alert.spread_count == 0
    assert alert.is_expanded is False
    assert alert.radius > 0
    assert alert.radius < 10
    # We count the number of alerted users before the expansion
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    # Empty alerts obviously have no alerted users, so we assert that the number of alerted users is 0
    assert alerted_users_num == 0
    # Now we call the API endpoint to expand the alert
    data = {
        "radius": 30.0,
        "role": None
    }
    alert_id = alert.id
    response = client.post(
        f"/api/alerts/{alert_id}/expand", json=data,
        headers={"Authorization": f"Bearer {access_token}"})
    db_session.refresh(alert)
    assert response.status_code == status.HTTP_200_OK
    assert alert.is_expanded is True
    # We count the alerted users to verify that at least some alerted users 
    # have been saved in database 
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alerted_users = db_session.exec(statement).all()
    alerted_users_num = len(alerted_users)
    assert alerted_users_num > 0
    new_alerted_users_num = alerted_users_num
    # The spread count is incremented because during the expansion (with role None),
    # new users have been added as alerted users (in database) for sure.
    assert alert.spread_count == 1
    assert alert.is_pending is False
    # The alert.radius is changed to the new radius,
    # because the expansion is performed with role=None
    assert alert.radius == 30.0
    # In this case, the alert type change to "manager",
    # because we found new users, and we added them as "alerted users" in database,
    # so the alert is not empty anymore.
    assert alert.type == AlertType.managed.value
    # We verify that alert notifications have been called,
    # to send notifications to the following users:
    # 1. the chief manager
    # 2. new alerted users
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_once()
    setup_fake_functions['mock_notify_chief_manager_about_expansion'].assert_called_with(
        str(chief.id), ANY,
        chief.language, ANY,
        30.0, None, new_alerted_users_num,
        ANY, ANY
    )
    # For non-local alerts, the alert sender is the chief manager, so no notification is sent to the alert sender.
    # (because we notify the chief manager, who is the alert sender, and we don't notify the same user twice)
    setup_fake_functions['mock_notify_sender_about_expansion'].assert_not_called()
    setup_fake_functions['mock_notify_nearby_users_about_expansion'].assert_called_once()
    args, _ = setup_fake_functions["mock_notify_nearby_users_about_expansion"].call_args
    notified_nearby_user_ids: list[str] = args[0] # the first argument is the list of notified user ids
    for user_id in notified_nearby_user_ids:
        assert user_id in [str(alerted_user.user_id) for alerted_user in alerted_users]
    assert len(notified_nearby_user_ids) == new_alerted_users_num
