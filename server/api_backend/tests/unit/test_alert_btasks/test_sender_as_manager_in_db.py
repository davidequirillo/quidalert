# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select
from models.general import (
    string_as_uuid,
    User, RefreshToken, AlertedUser, Alert, AlertType
)
from services.alert_btasks import (
    save_sender_as_manager_in_db
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically used)
    create_test_alert, # required (fixture test_alert)
    create_test_request_info, # required (fixture test_request_info)
)

async def test_save_sender_as_manager_in_db_success(db_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    # The alert type is "managed" (in this case the sender of the alert, a chief, will be the alert manager)
    test_alert.type = AlertType.managed.value
    # Now we select a chief from the database (see tests/fixtures/alerts.py)
    statement = select(User).where(User.email == "chief3@example.com")
    user = db_session.exec(statement).first()
    assert user is not None
    assert user.id is not None
    # We fetch the user fcm token from database
    refresh_token = db_session.exec(select(RefreshToken).where(RefreshToken.user_id == user.id)).first()
    assert refresh_token is not None
    assert refresh_token.fcm_token is not None
    user_fcm_token = refresh_token.fcm_token
    # We assign the user id to the alert (to simulate a real alert created by a specific user) and save it in the database
    test_alert.user_id = user.id
    # Now "user" is the sender of the alert
    db_session.add(test_alert)
    db_session.commit()
    db_session.refresh(test_alert)
    db_engine = db_session.get_bind()
    chief, chief_fcm_token = save_sender_as_manager_in_db(test_alert, user, user_fcm_token, test_request_info, db_engine)
    assert chief_fcm_token is not None
    assert chief_fcm_token == user_fcm_token
    assert chief is not None
    assert string_as_uuid(chief["user_id"]) == user.id
    assert string_as_uuid(chief["user_id"]) == test_alert.user_id
    # We check that 1 alerted user has been saved in the database (as alerted manager)
    alerted_users = db_session.exec(select(AlertedUser).where(AlertedUser.alert_id == test_alert.id)).all()
    len_alerted_users = len(alerted_users)
    assert len_alerted_users == 1
    alerted_user = alerted_users[0]
    assert alerted_user is not None
    assert alerted_user.user_id == string_as_uuid(chief["user_id"])
    assert alerted_user.alert_id == test_alert.id
    assert alerted_user.is_manager == True
