# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
from models.general import (
    User,
    WhiteListEntry
)
from sqlmodel import Session, select, delete
from core.dbmgr import get_engine
from core.settings import settings
from services.network import FAKE_EMAIL_DOMAIN

settings.db_engine_echo = False  # Disable database engine echo for cleaner output during seeding
db_engine = get_engine()

def delete_fake_users_by_emails(emails, db_session):
    num = 0
    for email in emails:
        statement = select(User).where(User.email == email)
        user = db_session.exec(statement).first()
        if not user:
            print(f"User with email {email} not found. Skipping deletion.")
            continue
        if not user.email.endswith(f"@{FAKE_EMAIL_DOMAIN}"):
            print(f"User with email {email} is not a fake email. Skipping deletion.")
            continue
        if user:
            # We select the related whitelist entry and delete it if it exists
            statement = select(WhiteListEntry).where(WhiteListEntry.email == email)
            whitelist_entry = db_session.exec(statement).first()
            if whitelist_entry:
                db_session.delete(whitelist_entry)
            else:
                print(f"No whitelist entry found for email {email}.")
            num += 1
            db_session.delete(user)
    db_session.commit()
    print(f"Deleted {num} fake users and their related whitelist entries.")

def delete_all_fake_users(db_session):
    statement = select(User)
    users = db_session.exec(statement).all()
    users_num = len(users)
    statement = (delete(User)
            .where(User.email.endswith(f"@{FAKE_EMAIL_DOMAIN}"))) # type: ignore
    result = db_session.exec(statement)
    deleted_num_users = result.rowcount
    # Delete related whitelist entries for fake users
    statement = (delete(WhiteListEntry)
            .where(WhiteListEntry.email.endswith(f"@{FAKE_EMAIL_DOMAIN}"))) # type: ignore
    result = db_session.exec(statement)
    deleted_num_whitelist_entries = result.rowcount
    db_session.commit()
    print(f"Users in the database: {users_num}")
    print(f"Deleted {deleted_num_users} fake users")
    print(f"Deleted {deleted_num_whitelist_entries} related fake whitelist entries. Note: the fake superuser has not a whitelist entry.")

if __name__ == "__main__":
    if settings.fake_user_scripts_enabled.lower() not in ("true", "1", "yes"):
        print("Fake user scripts are disabled. Exiting.")
        raise SystemExit(0)
    parser = argparse.ArgumentParser(description="Delete fake users for specific emails or all fake users.")
    parser.add_argument("--emails", type=str, nargs="*", help="Email addresses of the users to be deleted. If not provided, all users will be deleted.")
    parser.add_argument("--all", action="store_true", help="Delete all users. If this flag is set, the --emails argument will be ignored.")
    args = parser.parse_args()
    emails = args.emails if args.emails else []
    print(f"Deleting fake users for the following emails: {emails}" if emails else "Deleting all fake users...")
    with Session(db_engine) as db_session:
        if args.all:
            delete_all_fake_users(db_session)
        elif emails:
            delete_fake_users_by_emails(emails, db_session)
        else:
            print("No emails provided and --all flag not set. Nothing to delete.")
