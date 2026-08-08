# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
from models.general import (
    User
)
from sqlmodel import Session, select, delete
from core.dbmgr import get_engine
from core.settings import settings

settings.db_engine_echo = False  # Disable database engine echo for cleaner output during seeding
db_engine = get_engine()

def delete_users_by_emails(emails, db_session):
    num = 0
    for email in emails:
        statement = select(User).where(User.email == email)
        user = db_session.exec(statement).first()
        if user:
            num += 1
            db_session.delete(user)
        else:
            print(f"User with email {email} not found. Skipping deletion.")
    db_session.commit()
    print(f"Deleted {num} users.")

def delete_all_users(db_session):
    statement = select(User)
    users = db_session.exec(statement).all()
    users_num = len(users)
    statement = delete(User)
    db_session.exec(statement)
    db_session.commit()
    print(f"Users in the database: {users_num}")
    print(f"Deleted {users_num} users.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete users for specific emails or all users.")
    parser.add_argument("--emails", type=str, nargs="*", help="Email addresses of the users to be deleted. If not provided, all users will be deleted.")
    parser.add_argument("--all", action="store_true", help="Delete all users. If this flag is set, the --emails argument will be ignored.")
    args = parser.parse_args()
    emails = args.emails if args.emails else []
    print(f"Deleting users for the following emails: {emails}" if emails else "Deleting all users...")
    with Session(db_engine) as db_session:
        if args.all:
            delete_all_users(db_session)
        elif emails:
            delete_users_by_emails(emails, db_session)
        else:
            print("No emails provided and --all flag not set. Nothing to delete.")
