# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
from models.general import (
    WhiteListEntry
)
from sqlmodel import Session, select, delete
from core.dbmgr import get_engine
from core.settings import settings

settings.db_engine_echo = False  # Disable database engine echo for cleaner output during seeding
db_engine = get_engine()

def delete_whitelist_entries_by_emails(emails, db_session):
    num = 0
    for email in emails:
        statement = select(WhiteListEntry).where(WhiteListEntry.email == email)
        entry = db_session.exec(statement).first()
        if entry:
            num += 1
            db_session.delete(entry)
        else:
            print(f"Whitelist entry with email {email} not found. Skipping deletion.")
    db_session.commit()
    print(f"Deleted {num} whitelist entries.")

def delete_all_whitelist_entries(db_session):
    statement = select(WhiteListEntry)
    entries = db_session.exec(statement).all()
    entries_num = len(entries)
    statement = delete(WhiteListEntry)
    db_session.exec(statement)
    db_session.commit()
    print(f"Whitelist entries in the database: {entries_num}")
    print(f"Deleted {entries_num} whitelist entries.")

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Delete whitelist entries for specific emails or all entries.")
    parser.add_argument("--emails", type=str, nargs="*", help="Email addresses of the whitelist entries to be deleted. If not provided, all entries will be deleted.")
    parser.add_argument("--all", action="store_true", help="Delete all whitelist entries. If this flag is set, the --emails argument will be ignored.")
    args = parser.parse_args()
    emails = args.emails if args.emails else []
    print(f"Deleting whitelist entries for the following emails: {emails}" if emails else "Deleting all whitelist entries...")
    with Session(db_engine) as db_session:
        if args.all:
            delete_all_whitelist_entries(db_session)
        elif emails:
            delete_whitelist_entries_by_emails(emails, db_session)
        else:
            print("No emails provided and --all flag not set. Nothing to delete.")
