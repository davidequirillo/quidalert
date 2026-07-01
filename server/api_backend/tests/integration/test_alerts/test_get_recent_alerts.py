# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import datetime, timedelta
from fastapi import status
from sqlmodel import select, delete
from core.exceptions import (
    token_not_valid_exception
)
from models.general import User, Alert, AlertType, AlertedUser
from services.security import now_tz_naive
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown, # required (fixture automatically called)
)

def test_get_recent_alerts_not_authorized_missing_token(client):
    response = client.get("/api/recent-alerts")
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_recent_alerts_not_authorized_invalid_token(client):
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_recent_alerts(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    # Now we try to select from db all the following alerts: 
    # 1) Alerts created by test_baseuser
    # 2) Alerts where test_baseuser is an alerted user (the user is in the alerted_users table)
    # 3) All general alerts (general alerts)
    # Here we use simple (non efficient) queries, because we want to test the API endpoint and check the results against the API endpoint.
    # The alert are already recent (setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py), 
    # so we don't need to filter by date
    alerts_by_me_stmt = (select(Alert).where(Alert.user_id == user.id).where(Alert.type != AlertType.general.value))
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == user.id))
    alerts_general_stmt = (select(Alert).where(Alert.type == AlertType.general.value))
    alerts_by_me = db_session.exec(alerts_by_me_stmt).all()
    alerts_to_me = db_session.exec(alerts_to_me_stmt).all()
    alerts_general = db_session.exec(alerts_general_stmt).all()
    recent_alerts = alerts_by_me + alerts_to_me + alerts_general
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    assert len(alerts) > 0
    # Check that the number of alerts returned by the API endpoint is equal to the number of alerts we selected from the database
    assert len(alerts) == len(recent_alerts)
    # Now we check that the alerts are the same, by comparing the alert ids
    alert_ids_from_api = [str(alert["id"]) for alert in alerts]
    alert_ids_from_db = [str(alert.id) for alert in recent_alerts]
    assert set(alert_ids_from_api) == set(alert_ids_from_db)
    # No duplicates are present
    assert len(alert_ids_from_api) == len(set(alert_ids_from_api))
    # We check that the alerts returned are ordered by created_at descending (most recent first)
    created_at_from_api = [alert["created_at"] for alert in alerts]
    assert created_at_from_api == sorted(created_at_from_api, reverse=True)
    # We check that the alerts returned are only a part of all alerts in the database
    all_alerts_stmt = select(Alert)
    all_alerts = db_session.exec(all_alerts_stmt).all()
    assert len(alerts) < len(all_alerts)

def test_get_recent_alerts_some_are_expired(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    now = now_tz_naive()
    # We select from db all the following alerts:
    # 1) Alerts created by test_baseuser
    # 2) Alerts where test_baseuser is an alerted user (the user is in the alerted_users table)
    # 3) All general alerts (general alerts)
    alerts_by_me_stmt = (select(Alert).where(Alert.user_id == user.id).where(Alert.type != AlertType.general.value))
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == user.id))
    alerts_general_stmt = (select(Alert).where(Alert.type == AlertType.general.value))
    alerts_by_me = db_session.exec(alerts_by_me_stmt).all()
    alerts_to_me = db_session.exec(alerts_to_me_stmt).all()
    alerts_general = db_session.exec(alerts_general_stmt).all()
    recent_alerts = alerts_by_me + alerts_to_me + alerts_general
    # Now we expire some alerts (from each category of the three) by setting their created_at to more than 365 days ago
    # This categories are not empty for sure (see setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py)
    # so we can safely expire at least one alert from each category
    expired_alert_ids = []
    for alert in alerts_by_me[:1]: # expire the first alert created by me
        alert.created_at = now - timedelta(days=370)
        db_session.add(alert)
        expired_alert_ids.append(str(alert.id))
    for alert in alerts_to_me[:1]: # expire the first alert to me
        alert.created_at = now - timedelta(days=370)
        db_session.add(alert)
        expired_alert_ids.append(str(alert.id))
    for alert in alerts_general[:1]: # expire the first general alert
        alert.created_at = now - timedelta(days=370)
        db_session.add(alert)
        expired_alert_ids.append(str(alert.id))
    # Remember: recent_alerts variable still contains the alerts that we just expired
    # (we didn't delete them, just set their created_at to more than 365 days ago)
    # Now we commit the changes to the database
    db_session.commit()
    # Now we call the recent alerts API endpoint
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    # The result is positive, because we have some alerts that are not expired (see setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py)
    assert len(alerts) > 0
    # Check that the number of alerts returned by the API endpoint is equal to the number of alerts we selected from the database, minus the expired ones
    assert len(alerts) == len(recent_alerts) - 3
    # And check that alerts returned don't contain any expired alert
    for alert in alerts:
        assert str(alert["id"]) not in expired_alert_ids

def test_get_recent_alerts_empty_table(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    # We delete all alerts from the database, so that the API endpoint returns an empty list
    db_session.exec(delete(Alert))
    db_session.commit()
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    assert len(alerts) == 0

def test_get_recent_alerts_no_alerts_by_me(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    # We delete all alerts (not general alerts) created by the user, so that the API endpoint returns only alerts to me and general alerts
    db_session.exec(delete(Alert).where(Alert.user_id == user.id, Alert.type != AlertType.general.value)) # type: ignore
    db_session.commit()
    # Now we select from db all the following alerts:
    # 1) Alerts where test_baseuser is an alerted user (the user is in the alerted_users table)
    # 2) All general alerts (general alerts)
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == user.id))
    alerts_general_stmt = (select(Alert).where(Alert.type == AlertType.general.value))
    alerts_to_me = db_session.exec(alerts_to_me_stmt).all()
    alerts_general = db_session.exec(alerts_general_stmt).all()
    recent_alerts = alerts_to_me + alerts_general
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    # Some alerts are returned for sure (alerts to me and general alerts), but not all alerts in the database
    assert len(alerts) > 0
    # Check that the number of alerts returned by the API endpoint is equal to the number of alerts we selected from the database
    assert len(alerts) == len(recent_alerts)
    # We confirm that the recent alerts (from database) have as "user_id" a different user than the test_baseuser, because we deleted all alerts created by the test_baseuser
    for alert in recent_alerts:
        assert alert.user_id != user.id

def test_get_recent_alerts_no_alerts_by_me_and_to_me(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    # We delete all alerts by me and all alerts to me
    db_session.exec(delete(Alert).where(Alert.user_id == user.id, Alert.type != AlertType.general.value)) # type: ignore
    db_session.exec(delete(Alert).where(Alert.id.in_(select(AlertedUser.alert_id).where(AlertedUser.user_id == user.id)))) # type: ignore
    db_session.commit()
    # Now we select from db all the following alerts:
    # 1) All general alerts (general alerts)
    alerts_general_stmt = (select(Alert).where(Alert.type == AlertType.general.value))
    alerts_general = db_session.exec(alerts_general_stmt).all()
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    # Some alerts are returned for sure (general alerts), but not all alerts in the database
    assert len(alerts) > 0
    # Check that the number of alerts returned by the API endpoint is equal to the number of general alerts we selected from the database
    assert len(alerts) == len(alerts_general)
    # The returned alerts are only a part of all alerts in the database, 
    # because we deleted all alerts by me and to me, 
    # we have not deleted any specific alert created by other users, example by "test_chief", see setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py)
    assert len(alerts) < len(db_session.exec(select(Alert)).all())

def test_get_recent_alerts_no_alerts_by_me_and_to_me_and_no_general_alerts(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    # We delete all alerts by me, all alerts to me and all general alerts
    db_session.exec(delete(Alert).where(Alert.user_id == user.id, Alert.type != AlertType.general.value)) # type: ignore
    db_session.exec(delete(Alert).where(Alert.id.in_(select(AlertedUser.alert_id).where(AlertedUser.user_id == user.id)))) # type: ignore
    db_session.exec(delete(Alert).where(Alert.type == AlertType.general.value)) # type: ignore
    db_session.commit()
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    # No alerts are returned, because we deleted all alerts by me, to me and general alerts
    assert len(alerts) == 0
    # We check that there are still some alerts in the database, 
    # because we deleted all alerts by me, to me and general alerts, 
    # but we have not deleted any specific alert created by other users, example by "test_chief", see setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py)
    assert 0 < len(db_session.exec(select(Alert)).all())

def test_get_recent_alerts_called_by_testchief(client, db_session, test_chief):
    chief: User = test_chief['user']
    assert chief is not None
    access_token = test_chief['access_token']
    # Now we try to select from db all the following alerts: 
    # 1) Alerts created by test_chief
    # 2) Alerts where test_chief is an alerted user (the user is in the alerted_users table)
    # 3) All general alerts (general alerts)
    # Here we use simple (non efficient) queries, because we want to test the API endpoint and check the results against the API endpoint.
    # The alert are already recent (setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py), 
    # so we don't need to filter by date
    alerts_by_me_stmt = (select(Alert).where(Alert.user_id == chief.id).where(Alert.type != AlertType.general.value))
    alerts_to_me_stmt = (select(Alert).join(AlertedUser, Alert.id == AlertedUser.alert_id) # type: ignore
        .where(AlertedUser.user_id == chief.id))
    alerts_general_stmt = (select(Alert).where(Alert.type == AlertType.general.value))
    alerts_by_me = db_session.exec(alerts_by_me_stmt).all()
    alerts_to_me = db_session.exec(alerts_to_me_stmt).all()
    alerts_general = db_session.exec(alerts_general_stmt).all()
    recent_alerts = alerts_by_me + alerts_to_me + alerts_general
    response = client.get(
        "/api/recent-alerts", headers={"Authorization": f"Bearer {access_token}"})
    assert response.status_code == status.HTTP_200_OK
    alerts = response.json()
    assert len(alerts) > 0
    # Check that the number of alerts returned by the API endpoint is equal to the number of alerts we selected from the database
    assert len(alerts) == len(recent_alerts)
    # Now we check that the alerts are the same, by comparing the alert ids
    alert_ids_from_api = [str(alert["id"]) for alert in alerts]
    alert_ids_from_db = [str(alert.id) for alert in recent_alerts]
    assert set(alert_ids_from_api) == set(alert_ids_from_db)
    # No duplicates are present
    assert len(alert_ids_from_api) == len(set(alert_ids_from_api))
    # We check that the alerts returned are ordered by created_at descending (most recent first)
    created_at_from_api = [alert["created_at"] for alert in alerts]
    assert created_at_from_api == sorted(created_at_from_api, reverse=True)
    # We check that the alerts returned are only a part of all alerts in the database,
    # because if we analyze the setup_alerts_data_and_teardown fixture in tests/fixtures/alerts.py, 
    # we can see that there are some alerts in which the test_chief is not involved
    all_alerts_stmt = select(Alert)
    all_alerts = db_session.exec(all_alerts_stmt).all()
    assert len(alerts) < len(all_alerts)
    api_alert_ids = [str(alert["id"]) for alert in alerts]
    # We calculate the alerts in which the test_chief is not involved, 
    # and for each of these alerts, we check that the test_chief is not involved (is not the creator of the alert, is not an alerted user for this alert, and the alert is not a general alert)
    chief_not_involved_alerts = [alert for alert in all_alerts if str(alert.id) not in api_alert_ids]
    for alert in chief_not_involved_alerts:
        assert alert.user_id != chief.id
        alerted_users_stmt = select(AlertedUser).where(AlertedUser.alert_id == alert.id, AlertedUser.user_id == chief.id)
        alerted_users = db_session.exec(alerted_users_stmt).all()
        assert len(alerted_users) == 0
        assert alert.type != AlertType.general.value
