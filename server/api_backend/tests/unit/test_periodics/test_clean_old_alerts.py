# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from sqlmodel import Session, select, delete
from models.general import Alert, AlertType, AlertedUser, Message
from services.periodics import (
    ALERT_TTL_DAYS,
    ALERT_TTSO_DAYS,
    do_alerts_cleanup
)
from services.security import now_tz_naive 
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown # required (fixture automatically called)
)

def test_clean_old_alerts_one_old_alert_in_db(db_session: Session):
    now = now_tz_naive()
    statement = select(Alert)
    # We get the first alert from the database (see setup_alerts_data fixture)
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    # There is at least one alert in the database (see setup_alerts_data fixture)
    assert alerts_num > 0
    alert = alerts[0]
    alerted_users_stmt = select(AlertedUser).where(AlertedUser.alert_id == alert.id)
    alert_messages_stmt = select(Message).where(Message.alert_id == alert.id)
    alerted_users = db_session.exec(alerted_users_stmt).all()
    alert_messages = db_session.exec(alert_messages_stmt).all()
    assert alert is not None
    assert alerted_users is not None
    assert alert_messages is not None
    assert len(alerted_users) > 0 # see setup_alerts_data fixture
    assert len(alert_messages) > 0 # see setup_alerts_data fixture
    # see setup_alerts_data fixture, each alerted user has at least 3 messages for the alert
    assert len(alert_messages) == len(alerted_users) * 3
    # Set the alert's created_at to be older than ALERT_TTL_DAYS
    alert.created_at = now - timedelta(days=ALERT_TTL_DAYS + 1)
    db_session.add(alert)
    db_session.commit()
    db_session.refresh(alert)
    db_engine = db_session.get_bind()
    # Call the do_alerts_cleanup function (periodic task)
    alert_id = alert.id   
    _, deleted_count = do_alerts_cleanup(db_engine)
    # Check if the alert has been deleted
    assert deleted_count == 1
    alerts_after_cleanup = db_session.exec(statement).all()
    alerts_num_after_cleanup = len(alerts_after_cleanup)
    assert alerts_num_after_cleanup == alerts_num - 1
    # The alerted users and messages related to the deleted alert should also be deleted,
    # because in our sqlmodel definitions (see models/general.py), we have set cascade="all, delete" 
    # for the relationships between Alert and AlertedUser, and between Alert and Message.
    statement = select(Message).where(Message.alert_id == alert_id)
    alert_messages_after_cleanup = db_session.exec(statement).all()
    assert len(alert_messages_after_cleanup) == 0
    statement = select(AlertedUser).where(AlertedUser.alert_id == alert_id)
    alerted_users_after_cleanup = db_session.exec(statement).all()
    assert len(alerted_users_after_cleanup) == 0

def test_clean_old_alerts_no_old_alerts_in_db(db_session: Session):
    now = now_tz_naive()
    statement = select(Alert)
    # We get alerts from the database (see setup_alerts_data fixture)
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    # There is at least one alert in the database (see setup_alerts_data fixture)
    assert alerts_num > 0
    # We verify that all alerts in the database are newer than ALERT_TTL_DAYS
    # so that no alert is old enough to be deleted
    for alert in alerts:
        assert alert.created_at > now - timedelta(days=ALERT_TTL_DAYS)
    # Set the alert's created_at to be newer than ALERT_TTL_DAYS
    # So, no alert is old enough to be deleted
    alert = alerts[0]
    alert.created_at = now - timedelta(days=ALERT_TTL_DAYS - 1)
    db_session.add(alert)
    db_session.commit()
    db_engine = db_session.get_bind()
    # Call the do_alerts_cleanup function (periodic task)
    _, deleted_count = do_alerts_cleanup(db_engine)
    # Check that no alert has been deleted
    assert deleted_count == 0

def test_clean_old_alerts_empty_table(db_session: Session):
    # We manually delete all alerts from the database
    # so, we simulate the case where there are no alerts in the database
    db_session.exec(delete(Alert))
    db_session.commit()
    # Check that there are no alerts in the database
    alerts_after_cleanup = db_session.exec(select(Alert)).all()
    alerts_num_after_cleanup = len(alerts_after_cleanup)
    assert alerts_num_after_cleanup == 0
    db_engine = db_session.get_bind()
    # Now we call the do_alerts_cleanup function (periodic task)
    _, deleted_count = do_alerts_cleanup(db_engine)
    # Check that no alert has been deleted, because there are no alerts in the database
    assert deleted_count == 0

def test_clean_old_alerts_some_old_alerts_in_db(db_session: Session):
    now = now_tz_naive()
    statement = select(Alert)
    # We get alerts from the database (see setup_alerts_data fixture)
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    # There is at least one alert in the database (see setup_alerts_data fixture)
    assert alerts_num > 0
    # We set some alerts to be older than ALERT_TTL_DAYS
    old_alerts_ids = []
    for i, alert in enumerate(alerts):
        if i % 2 != 0:
            alert.created_at = now - timedelta(days=ALERT_TTL_DAYS + 1)
            old_alerts_ids.append(alert.id)
        else:
            alert.created_at = now - timedelta(days=ALERT_TTL_DAYS - 1)
        db_session.add(alert)
    db_session.commit()
    db_engine = db_session.get_bind()
    # Call the do_alerts_cleanup function (periodic task)
    _, deleted_count = do_alerts_cleanup(db_engine)
    assert deleted_count == alerts_num // 2
    # We check that the remaining alerts in the database are all newer than ALERT_TTL_DAYS
    remaining_alerts = db_session.exec(statement).all()
    for alert in remaining_alerts:
        assert alert.id not in old_alerts_ids
        assert alert.created_at > now - timedelta(days=ALERT_TTL_DAYS)
    # We also check that the alerted users and messages related to the deleted alerts have been deleted
    for old_alert_id in old_alerts_ids:
        statement = select(Message).where(Message.alert_id == old_alert_id)
        alert_messages_after_cleanup = db_session.exec(statement).all()
        assert len(alert_messages_after_cleanup) == 0
        statement = select(AlertedUser).where(AlertedUser.alert_id == old_alert_id)
        alerted_users_after_cleanup = db_session.exec(statement).all()
        assert len(alerted_users_after_cleanup) == 0

def test_clean_old_alerts_close_and_delete_some_alerts(db_session: Session):
    now = now_tz_naive()
    statement = select(Alert)
    # We get alerts from the database (see setup_alerts_data fixture)
    alerts = db_session.exec(statement).all()
    alerts_num = len(alerts)
    # There is at least one alert in the database (see setup_alerts_data fixture)
    # and all alerts initially are in open status (is_closed=False)
    assert alerts_num > 0
    assert all(not alert.is_closed for alert in alerts)
    # We set some local alert to be older than ALERT_TTSO_DAYS (to be closed) 
    # and some alerts to be older than ALERT_TTL_DAYS (to be deleted)
    alerts_to_close_ids = []
    alerts_to_close_num = 0
    alerts_to_delete_ids = []
    alerts_to_delete_num = 0
    for i, alert in enumerate(alerts):
        if i % 3 == 0:
            alert.created_at = now - timedelta(days=ALERT_TTL_DAYS + 1)
            alerts_to_delete_ids.append(alert.id)
            alerts_to_delete_num += 1
            # We simulate that it's already closed
            # So it will not count as an alert to be closed, but it will be deleted because it's older than ALERT_TTL_DAYS
            alert.is_closed = True
        elif i % 3 == 1:
            alert.created_at = now - timedelta(days=ALERT_TTSO_DAYS + 1)
            if (alert.type == AlertType.local.value) and (not alert.is_closed):
                alerts_to_close_ids.append(alert.id)
                alerts_to_close_num += 1
        else:
            alert.created_at = now - timedelta(days=ALERT_TTSO_DAYS - 1)
        db_session.add(alert)
    db_session.commit()
    assert alerts_to_close_num > 0
    assert alerts_to_delete_num > 0
    db_engine = db_session.get_bind()
    # Call the do_alerts_cleanup function (periodic task)
    # We verify the results with the results coming from db
    closed_num, deleted_num = do_alerts_cleanup(db_engine)
    assert deleted_num > 0
    assert closed_num > 0
    assert closed_num == alerts_to_close_num
    assert deleted_num == alerts_to_delete_num
    for alert_id in alerts_to_close_ids:
        alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
        assert alert is not None
        assert alert.is_closed is True
    for alert_id in alerts_to_delete_ids:
        alert = db_session.exec(select(Alert).where(Alert.id == alert_id)).first()
        assert alert is None
