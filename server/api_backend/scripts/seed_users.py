# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import argparse
from faker import Faker
from core.settings import settings
from models.general import User, UserLanguage, UserRole, WhiteListEntry
from services.security import (
    get_password_hash, activation_expiry, now_tz_naive)
from sqlmodel import Session, select
from core.dbmgr import get_engine
from services.network import FAKE_EMAIL_DOMAIN

fake = Faker('en_US')
TOTAL_ADMINS = 3
TOTAL_OFFICERS = 10
TOTAL_CHIEFS = 7
TOTAL_BASEUSERS = 1000
ROLE_PROBABILITY = 0.10  # 10% of users have a role assigned
user_categories = ["admins", "officers", "chiefs", "baseusers"]
user_types = ["admin", "officer", "chief", "baseuser"] 
user_cardinalities = [TOTAL_ADMINS, TOTAL_OFFICERS, TOTAL_CHIEFS, TOTAL_BASEUSERS]
settings.send_emails = False  # Disable email sending during seeding to avoid spamming
settings.db_engine_echo = False  # Disable SQLAlchemy echo for cleaner output during seeding
db_engine = get_engine()
print(f"Generating a common password hash for all users...")
common_password = settings.fake_users_pass
common_password_hash = get_password_hash(common_password)

def seed_superuser_if_db_is_empty():
    with Session(db_engine) as session:
        first_user = session.exec(select(User)).first()
        if first_user:
            print("Superuser already exists because the database is not empty. Skipping superuser seeding.")
            return
        print("Creating superuser...")
        superuser = User.model_validate({
            "firstname": "Admin",
            "surname": "User",
            "email": f"superuser@{FAKE_EMAIL_DOMAIN}",
            "language": UserLanguage.en.value,
            "password_hash": get_password_hash(settings.admin_pass),
            "is_superuser": True,
            "is_admin": True,
            "is_officer": False,
            "is_chief": False,
            "role": None,
            "is_active": True,
            "activation_code": "fake-superuser-activation-code",
            "activation_code_expires_at": activation_expiry(),
            "pending_delete_since": None,
            "authorized_by": None,
            "authorized_at": None
        })
        session.add(superuser)
        session.commit()
        print("Superuser created successfully.")

def seed_users_whitelist():
    with Session(db_engine) as session:
        print(f"Populating PostgreSQL with whitelist entries...")
        try:
            for category, user_type, cardinality in zip(user_categories, user_types, user_cardinalities):
                for i in range(1, cardinality+1):
                    if user_type == "admin":
                        created_by = f"superuser@{FAKE_EMAIL_DOMAIN}"
                        created_at = now_tz_naive()
                    elif user_type == "officer":
                        rand_admin_index = fake.random.randint(1, TOTAL_ADMINS)
                        created_by = f"admin{rand_admin_index}@{FAKE_EMAIL_DOMAIN}"
                        created_at = now_tz_naive()
                    elif user_type == "chief":
                        rand_admin_index = fake.random.randint(1, TOTAL_ADMINS)
                        created_by = f"admin{rand_admin_index}@{FAKE_EMAIL_DOMAIN}"
                        created_at = now_tz_naive()
                    else:  # baseuser
                        rand_officer_index = fake.random.randint(1, TOTAL_OFFICERS)
                        created_by = f"officer{rand_officer_index}@{FAKE_EMAIL_DOMAIN}"
                        created_at = now_tz_naive()
                    entry = WhiteListEntry.model_validate({
                        "email": f"{user_type}{i}@{FAKE_EMAIL_DOMAIN}",
                        "created_by": created_by,
                        "created_at": created_at
                    })
                    dbentry = session.exec(select(WhiteListEntry).where(WhiteListEntry.email == entry.email)).first()
                    if dbentry:
                        print(f"Whitelist entry for {entry.email} already exists. Skipping.")
                        continue
                    session.add(entry)
                    # Commit every 100 entries to keep the transaction light
                    if i % 100 == 0:
                        session.commit()
                        print(f"{i}/{cardinality} whitelist entries for {category} inserted...")
                session.commit()
                print(f"Whitelist {cardinality}/{cardinality} entries for {category} inserted successfully.")
            print("Whitelist entries insertion completed!")
        except Exception as e:
            print(f"Error during whitelist seeding: {e}")
            session.rollback()

def seed_users():
    with Session(db_engine) as session:
        languages = [lang.value for lang in UserLanguage]
        user_roles = [role.value for role in UserRole]
        print(f"Populating PostgreSQL with fake users... (emails ending with @{FAKE_EMAIL_DOMAIN})")
        try:
            for category, user_type, cardinality in zip(user_categories, user_types, user_cardinalities):
                for i in range(1, cardinality+1):
                    email = f"{user_type}{i}@{FAKE_EMAIL_DOMAIN}"
                    whitelist_entry = session.exec(select(WhiteListEntry).where(WhiteListEntry.email == email)).first()
                    if not whitelist_entry:
                        print(f"Skipping {email} as it is not in the whitelist.")
                        continue                    
                    authorized_by = whitelist_entry.created_by
                    authorized_at = whitelist_entry.created_at
                    if (user_type == "baseuser"):
                        random_value = fake.random.random()
                        if random_value < ROLE_PROBABILITY:
                            role = fake.random.choice(user_roles)
                        else:
                            role = None
                    else:
                        role = None
                    user = User.model_validate({
                        "firstname": fake.first_name(),
                        "surname": fake.last_name(),
                        "email": f"{user_type}{i}@{FAKE_EMAIL_DOMAIN}",
                        "language": fake.random.choice(languages),
                        "password_hash": common_password_hash,
                        "is_superuser": False,
                        "is_admin": user_type == "admin",
                        "is_officer": user_type == "officer",
                        "is_chief": user_type == "chief",
                        "role": role,
                        "is_active": True,
                        "activation_code": f"fake-{user_type}-activation-code-{i}",
                        "activation_code_expires_at": activation_expiry(),
                        "pending_delete_since": None,
                        "authorized_by": authorized_by,
                        "authorized_at": authorized_at
                    })
                    dbuser = session.exec(select(User).where(User.email == user.email)).first()
                    if dbuser:
                        print(f"User with email {user.email} already exists. Skipping.")
                        continue
                    session.add(user)
                    # Commit every 100 users to keep the transaction light
                    if i % 100 == 0:
                        session.commit()
                        print(f"{i}/{cardinality} {category} inserted...")
            session.commit()
            print("User insertion completed!")
            print(f"Superuser inserted: 1")
            print(f"Admins inserted: {TOTAL_ADMINS}")
            print(f"Officers inserted: {TOTAL_OFFICERS}")
            print(f"Chiefs inserted: {TOTAL_CHIEFS}")
            print(f"Base users inserted: {TOTAL_BASEUSERS}")
            print("-------------------")
            print(f"Total users inserted: {sum(user_cardinalities)} + 1 (superuser) = {sum(user_cardinalities) + 1}")
            specialists = session.exec(select(User).where(User.role != None)).all()
            specialists_num = len(specialists)
            print("Number of specialists (users with a role):", specialists_num)
        except Exception as e:
            print(f"Error during user seeding: {e}")
            session.rollback()

if __name__ == "__main__":
    parser = argparse.ArgumentParser(description="Seed the database with a superuser, whitelist entries, and users.")
    # Add argument baseusers_count to specify the number of base users to seed
    parser.add_argument("--baseusers_count", type=int, default=TOTAL_BASEUSERS)
    args = parser.parse_args()
    TOTAL_BASEUSERS = args.baseusers_count
    user_cardinalities[3] = TOTAL_BASEUSERS  # Update the cardinality for baseusers
    if TOTAL_BASEUSERS < 1000:
        print("The number of base users to seed must be at least 1000 (the default). Exiting.")
        exit(1)
    if TOTAL_BASEUSERS > 10000:
        print("The number of base users to seed is too high (max 10000). Exiting.")
        exit(1)
    seed_superuser_if_db_is_empty()
    seed_users_whitelist()
    seed_users()
