# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select
from models.general import User, Alert, RefreshToken
from services.alert_btasks import get_sender_fcm_token
from tests.fixtures.alerts import (
    create_test_alert, 
    create_test_request_info
)

def test_get_sender_fcm_token_is_none(db_session, test_alert, test_request_info):
    statement = select(User).where(User.id == test_alert.user_id)   
    user = db_session.exec(statement).first()
    assert user is not None
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    refresh_token = db_session.exec(statement).first()
    # The alert user is logged and has a refresh token
    assert refresh_token is not None
    # But the default is that the refresh token has no FCM token (fcm_token is null), initially
    assert refresh_token.fcm_token is None
    db_engine = db_session.get_bind()
    assert db_engine is not None
    # We check that the function returns None if the user has no FCM token in the database (fcm token null)
    sender_fcm_token = get_sender_fcm_token(test_alert, user, test_request_info, db_engine)
    assert sender_fcm_token is None

def test_get_sender_fcm_token_success(db_session, test_alert, test_request_info):
    statement = select(User).where(User.id == test_alert.user_id)   
    user: User = db_session.exec(statement).first()
    assert user is not None
    assert test_alert.user_id == user.id
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    refresh_token: RefreshToken = db_session.exec(statement).first()
    # The alert user is logged and has a refresh token
    assert refresh_token is not None
    assert refresh_token.user_id == test_alert.user_id
    # We set an FCM token for the refresh token
    refresh_token.fcm_token = "test_fcm_token"
    db_session.add(refresh_token)
    db_session.commit()
    db_engine = db_session.get_bind()
    assert db_engine is not None
    # We check that the function returns the FCM token we set in the database
    sender_fcm_token = get_sender_fcm_token(test_alert, user, test_request_info, db_engine)
    assert sender_fcm_token == "test_fcm_token"
