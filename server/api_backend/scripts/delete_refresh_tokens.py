# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
from models.general import (
    User,
    RefreshToken
)
from sqlmodel import Session, select
from core.dbmgr import get_engine
from core.settings import settings
from services.network import FAKE_EMAIL_DOMAIN

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

if __name__ == "__main__":
    if settings.fake_user_scripts_enabled.lower() not in ("true", "1", "yes"):
        print("Fake user scripts are disabled. Exiting.")
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description="Delete refresh tokens for specific fake users")
    parser.add_argument("--emails", type=str, nargs="*", help="Email addresses of the users whose refresh tokens will be deleted.")
    args = parser.parse_args()
    emails = args.emails if args.emails else []
    fake_emails = []
    for email in emails:
        if email.endswith(f"@{FAKE_EMAIL_DOMAIN}"):
            fake_emails.append(email)
        else:
            print(f"Email {email} does not belong to a fake user, skipping it.")
    if fake_emails:
        print(f"Deleting refresh tokens for the following fake users: {fake_emails}")
    with Session(db_engine) as db_session:
        if fake_emails:
            delete_refresh_token_by_emails(fake_emails, db_session)
        else:
            print("No fake user emails provided. Nothing to delete.")
