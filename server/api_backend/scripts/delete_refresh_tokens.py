# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
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
from sqlmodel import Session, select, delete
from core.dbmgr import get_engine
from core.settings import settings

settings.db_engine_echo = False  # Disable database engine echo for cleaner output during seeding
db_engine = get_engine()

def delete_refresh_token_by_emails(emails, db_session):
    num = 0
    for email in emails:
        statement = select(User).where(User.email == email)
        user = db_session.exec(statement).first()
        if user:
            statement = select(RefreshToken).where(RefreshToken.user_id == user.id)
            refresh_token = db_session.exec(statement).first()
            if refresh_token:
                db_session.delete(refresh_token)
                num += 1
    db_session.commit()
    print(f"Deleted {num} refresh tokens.")
    print("NOTE: the number of refresh tokens deleted can be less than the number of emails provided, because not all users may have a refresh token in the database (e.g. if they never logged in).")

def delete_refresh_token_for_all(db_session):
    statement = select(User)
    users = db_session.exec(statement).all()
    users_num = len(users)
    statement = select(RefreshToken)
    refresh_tokens = db_session.exec(statement).all()
    rtokens_num = len(refresh_tokens)
    statement = delete(RefreshToken)
    db_session.exec(statement)
    db_session.commit()
    print(f"Users in the database: {users_num}")
    print(f"Deleted {rtokens_num} refresh tokens.")
    print("NOTE: the number of refresh tokens deleted can be less than the number of users, because not all users may have a refresh token in the database (e.g. if they never logged in).")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete refresh tokens for specific users or all users.")
    parser.add_argument("--emails", type=str, nargs="*", help="Email addresses of the users whose refresh tokens will be deleted. If not provided, refresh tokens for all users will be deleted.")
    parser.add_argument("--all", action="store_true", help="Delete refresh tokens for all users. If this flag is set, the --emails argument will be ignored.")
    args = parser.parse_args()
    emails = args.emails if args.emails else []
    print(f"Deleting refresh tokens for the following users: {emails}" if emails else "Deleting refresh tokens for all users...")
    with Session(db_engine) as db_session:
        if args.all:
            delete_refresh_token_for_all(db_session)
        elif emails:
            delete_refresh_token_by_emails(emails, db_session)
        else:
            print("No emails provided and --all flag not set. Nothing to delete.")
