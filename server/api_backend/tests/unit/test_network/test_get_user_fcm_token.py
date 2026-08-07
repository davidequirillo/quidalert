# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import select
from models.general import User, RefreshToken
from services.network import get_user_fcm_token

def test_get_user_fcm_token_is_none(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    refresh_token = db_session.exec(statement).first()
    # Test user is logged and has a refresh token (see conftest.py)
    assert refresh_token is not None
    # We simulate the case where the user has no FCM token in the database (fcm token null)
    refresh_token.fcm_token = None
    db_session.add(refresh_token)
    db_session.commit()
    db_session.refresh(refresh_token)
    assert refresh_token.fcm_token is None
    # We check that the function returns None if the user has no FCM token in the database (fcm token null)
    user_fcm_token = get_user_fcm_token(user.id, db_session)
    assert user_fcm_token is None

def test_get_user_fcm_token_success(db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    refresh_token = db_session.exec(statement).first()
    # Test user is logged and has a refresh token (see conftest.py)
    assert refresh_token is not None
    assert refresh_token.user_id == user.id
    # Test user has a FCM token not null in the database (see conftest.py)
    assert refresh_token.fcm_token is not None
    assert refresh_token.fcm_token != ""
    db_session.add(refresh_token)
    db_session.commit()
    # We check that the function returns the FCM token we set in the database
    user_fcm_token = get_user_fcm_token(user.id, db_session)
    assert user_fcm_token == refresh_token.fcm_token
