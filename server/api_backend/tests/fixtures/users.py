# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from sqlmodel import delete
from models.general import User, UserRole, UserLanguage
from services.security import now_tz_naive

@pytest.fixture(autouse=True)
def setup_and_teardown(db_session):
    # Create a superuser
    superuser = User(
        email="superuser@example.com",
        password_hash="hashed_password",
        firstname="Super",
        surname="User",
        is_active=True,
        is_superuser=True,
        is_admin=True,
        role=None,
        language=UserLanguage.en.value
    )
    db_session.add(superuser)
    db_session.commit()
    # Create 2 admins
    for i in range(1, 3):
        admin_user = User(
            email=f"admin{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Admin{i}",
            surname=f"User{i}",
            is_active=True,
            is_admin=True,
            role=UserRole.volunteer.value, # Note: it can be any role, or None
            authorized_by=superuser.email,
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(admin_user)
    db_session.commit()
    # Create 5 officers
    for i in range(1, 6):
        officer_user = User(
            email=f"officer{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Officer{i}",
            surname=f"User{i}",
            is_active=True,
            is_officer=True,
            role=UserRole.volunteer.value, # Note: it can be any role, or None
            authorized_by=f"admin{i%2 + 1}@example.com", # Alternate authorization between the 2 admins
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(officer_user)
    db_session.commit()
    # Create 4 chiefs
    for i in range(1,5):
        chief_user = User(
            email=f"chief{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Chief{i}",
            surname=f"User{i}",
            is_active=True,
            is_chief=True,
            role=UserRole.usar.value, # Note: it can be any role, or None
            authorized_by=f"admin{i%2 + 1}@example.com", # Alternate authorization between the 2 admins
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(chief_user)
    db_session.commit()
    roles = [None] + [r.value for r in UserRole]
    roles_len = len(roles)
    # Create many base users with random roles
    for i in range(1, 23):
        random_role_index = i % roles_len
        test_user = User(
            email=f"testuser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Firstname{i}",
            surname=f"Surname{i}",
            is_active=True,
            role=roles[random_role_index],
            authorized_by=f"officer{i%5 + 1}@example.com", # Alternate authorization between the 5 officers
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(test_user)
    db_session.commit()
    yield
    # Clean up the database after each test
    db_session.exec(delete(User))
    db_session.commit()
