# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import sys
import argparse
from models.general import (
    User,
    RefreshToken
)
from services.security import (
    now_tz_naive
)
from sqlmodel import Session, select
from core.dbmgr import get_engine
from core.settings import settings
from services.network import FAKE_EMAIL_DOMAIN

settings.db_engine_echo = False  # Disable database engine echo for cleaner output during seeding
db_engine = get_engine()

def select_the_seeding_user(email, db_session):
    statement = select(User).where(User.email == email)
    user = db_session.exec(statement).first()
    return user

def get_refresh_token_for_user(user):
    statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
    refresh_token = db_session.exec(statement).first()
    return refresh_token

def assign_fcm_token_to_all_fake_users(refresh_token, db_session):
    now = now_tz_naive() 
    print("Selecting all fake users from the database...")
    fake_users = db_session.exec(select(User).where(User.email.endswith(f"@{FAKE_EMAIL_DOMAIN}"))).all()
    print(f"Found {len(fake_users)} fake users. Updating their FCM tokens...")
    for user in fake_users:
        if user.id == refresh_token.user_id:
            print(f"Skipping user '{user.email}' as it is the seeding user (he already has the valid FCM token).")
            continue
        # Select user refresh token if exists, otherwise we create a new one
        statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
        rtoken = db_session.exec(statement).first()
        if rtoken:
            rtoken.fcm_token = refresh_token.fcm_token
            rtoken.fcm_token_updated_at = now
        else:
            rtoken = RefreshToken.model_validate({
                "user_id": user.id,
                "raw_hash": "dummy-hash-for-fcm-token-seeding",
                "fcm_token": refresh_token.fcm_token, # Assign the FCM token from the seeding user
                "fcm_token_updated_at": now,
                "updated_at": now
            })
        db_session.add(rtoken)
    db_session.commit()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description=f"Seed FCM tokens for all fake users (users with emails ending with @{FAKE_EMAIL_DOMAIN}) using the FCM token from a specific user: after running this script, all fake users will have the same FCM token as the specified user.")
    parser.add_argument("--email", type=str, required=True, help="Email of the user whose FCM token will be used for seeding.")
    args = parser.parse_args()
    email = args.email
    with Session(db_engine) as db_session:
        user = select_the_seeding_user(email, db_session)
        if not user:
            print(f"User with email '{email}' not found. Please ensure the user exists before seeding FCM tokens.")
            sys.exit(1)
        refresh_token = get_refresh_token_for_user(user)
        if not refresh_token:
            print(f"No refresh token found for user '{email}'. Please ensure the user has a valid refresh token before seeding.")
            sys.exit(1)
        print(f"Seeding FCM tokens for all fake users using the FCM token from user '{email}'...")
        print(f"FCM token to be assigned: {refresh_token.fcm_token}")
        assign_fcm_token_to_all_fake_users(refresh_token, db_session)
        print("All fake users have been updated with the new FCM token.")
