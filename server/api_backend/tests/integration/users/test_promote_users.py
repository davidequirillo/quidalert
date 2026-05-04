# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from datetime import timedelta
from fastapi import status
from sqlmodel import delete, select
from core.exceptions import (
    token_not_valid_exception,
    forbidden_exception
)
from models.general import (
    User, UserType, UserRole, UserLanguage, UserStatus
)
from services.security import (
    now_tz_naive
)
from core.dbmgr import (
    get_redis_chief_demotions_key,
    get_redis_chief_locations_key
)

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
        role=UserRole.citizen.value,
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
            role=UserRole.citizen.value,
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
            role=UserRole.citizen.value,
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
            role=UserRole.citizen.value,
            authorized_by=f"admin{i%2 + 1}@example.com", # Alternate authorization between the 2 admins
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(chief_user)
    db_session.commit()
    roles = [r.value for r in UserRole]
    roles_len = len(roles)
    # Create many users to test pagination with random roles
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

## TESTS: POST /api/users/promote

def test_promote_users_not_authorized_missing_token(client):
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.volunteer.value
    }
    response = client.post("/api/users/promote", params=params, json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_promote_users_not_authorized_invalid_token(client):
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.volunteer.value
    }
    response = client.post(
        "/api/users/promote", params=params, json=data,
        headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_promote_users_method_not_allowed(client, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/users/promote", headers=headers)
    # GET method is not allowed for this endpoint, only POST is allowed
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

def test_promote_users_empty_promotion_data(client, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {}
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_promote_users_invalid_promotion_data(client, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": "invalid_role"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_promote_users_forbidden_for_baseuser(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.policeman.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    # Chief role is not allowed to access this endpoint, only admin or officers can access it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail 

def test_promote_users_forbidden_for_chief(client, test_chief):
    user: User = test_chief['user']
    assert user is not None
    access_token = test_chief['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.policeman.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    # Chief role is not allowed to access this endpoint, only admin or officers can access it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_called_by_officer_cannot_modify_the_type(client, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "type": UserType.chief.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    # Officer role is not allowed to modify the type of the users, only admin can modify it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # User chief1 is authorized by an admin (see setup fixture)
    # Officer role cannot update users not authorized by them, so the promotion should not be applied
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officer role cannot update users not authorized by them
    assert response_data["updated_count"] == 0
    # Another example
    params = {
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officer role cannot update users not authorized by them
    assert response_data["updated_count"] == 0
    # Now try to promote a user authorized by test_officer, the promotion should be applied
    # But we must first create a user authorized test_officer
    new_user = User(
        email="authorized_by_this_officer@example.com",
        password_hash="hashed_password",
        firstname="Authorized",
        surname="ByThisOfficer",
        is_active=True,
        role=UserRole.citizen.value,
        authorized_by=user.email,
        authorized_at=now_tz_naive(),
        language=UserLanguage.en.value
    )
    db_session.add(new_user)
    db_session.commit()
    params = {
        "email": "authorized_by_this_officer@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officer role can update users authorized by them
    assert response_data["updated_count"] == 1
    # We verify the update in the database
    statement = select(User).where(User.email=="authorized_by_this_officer@example.com")
    chiefuser1 = db_session.exec(statement).first()
    assert chiefuser1.role == UserRole.medic.value
    assert chiefuser1.updated_by == user.email # The update should be applied by test_officer
    assert chiefuser1.updated_at is not None
    assert chiefuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example with authorizer filter
    # This time the authorizer is test_officer, so the update should succeed
    params = {
        "authorizer": user.email
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officer role can update users authorized by them
    assert response_data["updated_count"] > 0

def test_promote_users_called_by_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    # We find in the db the user with email "testuser1@example.com"
    select_stmt = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(select_stmt).first()
    assert testuser1 is not None
    assert testuser1.updated_at is None # The user has not been updated yet
    assert testuser1.updated_by is None # The user has not been updated yet
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Admin role can update any user
    assert response_data["updated_count"] == 1
    # We verify the update in the database
    statement = select(User).where(User.email=="testuser1@example.com")
    updated_user = db_session.exec(statement).first()
    assert updated_user.role == UserRole.medic.value
    assert updated_user.updated_by == user.email
    assert updated_user.updated_at is not None
    assert updated_user.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example with authorizer filter
    params = {
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Admin role can update any user
    assert response_data["updated_count"] > 0

def test_promote_users_modify_role_and_notes(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # Admin user is a "citizen"
    assert user.role == UserRole.citizen.value
    assert user.firstname == "Firstname1"
    assert user.surname == "Surname1"
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "firstname": "Firstname1",
        "surname": "Surname1"
    }
    data = {
        "role": UserRole.volunteer.value,
        "notes": "This user has been promoted to volunteer for testing purposes."
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are 2 users with firstname "Firstname1" and surname "Surname1" (one in the setup fixture, and one is test_admin user), so both should be updated to volunteer role and with the notes
    assert response_data["updated_count"] == 2
    # We verify that test_admin user has been updated to "volunteer"
    db_session.refresh(user) # Refresh the user instance to get the updated data from the database
    assert user.role == UserRole.volunteer.value
    assert user.notes == "This user has been promoted to volunteer for testing purposes."
    # We verify that the other user has been updated
    statement = select(User).where(User.firstname=="Firstname1", User.surname=="Surname1", User.email != user.email)
    updated_user = db_session.exec(statement).first()
    assert updated_user.role == UserRole.volunteer.value
    assert updated_user.notes == "This user has been promoted to volunteer for testing purposes."
    assert updated_user.email != user.email
    assert updated_user.updated_by == user.email
    assert updated_user.updated_at is not None
    assert updated_user.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example with role filter
    params = {
        "role": UserRole.citizen.value
    }
    data = {
        "role": UserRole.volunteer.value,
        "notes": "This user has been promoted to volunteer for testing purposes."
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are at least 12 users with role citizen (see setup fixture), so at least those should be updated to volunteers role and with the notes
    assert response_data["updated_count"] >= 12
    # Another example with role filter + status filter
    params = {
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value
    }
    data = {
        "role": UserRole.usar.value,
        "notes": "This user has been promoted to usar for testing purposes."
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There were at least 13 users with role "volunteer" and status ok
    # Yes, 13 users (12 from the previous step, and test_admin user that we promoted to volunteer in the first step)
    assert user.role == UserRole.usar.value # the test_admin user was a volunteer in the previous step, so it should be updated to usar role
    assert user.notes == "This user has been promoted to usar for testing purposes."
    assert response_data["updated_count"] >= 13
    # All volunteers have been promoted to usar, so in the database there should be no more volunteers with status ok
    statement = select(User).where(User.role==UserRole.volunteer.value, User.is_reliable==True)
    volunteers_ok = db_session.exec(statement).all()
    assert len(volunteers_ok) == 0
    # Now we try to update all blocked "usar" users to military role, but there are not blocked users, so the update should not be applied to any user
    params = {
        "role": UserRole.usar.value,
        "status": UserStatus.blocked.value
    }
    data = {
        "role": UserRole.military.value,
        "notes": "This user has been promoted to military for testing purposes."
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are no users with role "usar" and status blocked, so no user should be updated
    # All usar users have status ok, so no user should be updated to military role
    assert response_data["updated_count"] == 0

def test_promote_users_modify_status(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "role": UserRole.citizen.value
    }
    data = {
        "status": UserStatus.blocked.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are at least 13 users with role citizen (see setup fixture, plus test_admin user), so at least those should be updated to blocked status
    assert response_data["updated_count"] >= 13
    # We verify that test_admin user has been updated to blocked status
    db_session.refresh(user) # Refresh the user instance to get the updated data from the database
    # Yes, test_admin has blocked himself :)
    assert user.is_blocked == True
    assert user.is_reliable == False # when a user is blocked, it should also be "not reliable"
    # We verify that the other users with role citizen have been updated to blocked status
    statement = select(User).where(User.role==UserRole.citizen.value)
    blocked_citizens = db_session.exec(statement).all()
    for blocked_user in blocked_citizens:
        assert blocked_user.is_blocked == True
        assert blocked_user.is_reliable == False # when a user is blocked, it should also be set as not reliable
        assert blocked_user.updated_by == user.email
        assert blocked_user.updated_at is not None
        assert blocked_user.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Now we try to declare as "unreliable" only 1 user with specific email
    params = {"email": "testuser1@example.com"}
    data = {
        "status": UserStatus.unreliable.value
    }
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.is_reliable == True
    assert testuser1.is_blocked == False # The user should not be blocked, but only set as unreliable
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    db_session.refresh(testuser1)
    # After the api call, testuser1 is not reliable
    assert testuser1.is_reliable == False
    assert testuser1.is_blocked == False # The user should not be blocked, but only set as unreliable

def test_promote_users_modify_authorizer_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "officer1@example.com"
    }
    statement = select(User).where(User.email=="chief1@example.com")
    chief1 = db_session.exec(statement).first()
    assert chief1.authorized_by != "officer1@example.com"
    assert chief1.authorized_by != user.authorized_by
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The user "test_officer" cannot modify the authorizer in this case
    # because the target user (chief1) has not been authorized by him.
    assert response_data["updated_count"] == 0
    db_session.refresh(chief1)
    assert chief1.authorized_by != "officer1@example.com"
    # Obviously, the officer cannot declare himself as authorizer of a user that is not authorized by him
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": user.email
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(chief1)
    assert chief1.authorized_by != user.email
    # Now we try to modify the authorizer of a user owned by test_officer
    user_owned = User(
        email="authorized_by_this_officer@example.com",
        password_hash="hashed_password",
        firstname="Authorized",
        surname="ByThisOfficer",
        is_active=True,
        role=UserRole.citizen.value,
        authorized_by=user.email,
        authorized_at=now_tz_naive(),
        language=UserLanguage.en.value
    )
    db_session.add(user_owned)
    db_session.commit()
    params = {
        "email": "authorized_by_this_officer@example.com"
    }
    data = {
        "authorizer": "officer1@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The user "test_officer" can modify the authorizer in this case 
    # because the target user is owned by him (authorized by him).
    assert response_data["updated_count"] == 1
    db_session.refresh(user_owned)
    assert user_owned.authorized_by == "officer1@example.com"
    assert user_owned.updated_by == user.email
    assert user_owned.updated_at is not None
    assert user_owned.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute

def test_promote_users_modify_authorizer_called_by_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "admin1@example.com"
    }
    statement = select(User).where(User.email=="chief1@example.com")
    chief1 = db_session.exec(statement).first()
    # Chief1 is authorized by an admin (see setup fixture), but not by "test_admin"
    assert chief1.authorized_by != user.email
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The user "test_admin" can modify the authorizer in this case 
    # because the admin role can modify any user, 
    # even if the target user (chief1) is owned (authorized) by another admin.
    assert response_data["updated_count"] == 1
    db_session.refresh(chief1)
    assert chief1.authorized_by == "admin1@example.com"
    # Admin can also declare himself as authorizer of a user, even if the user was not previously authorized by him
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": user.email
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(chief1)
    assert chief1.authorized_by == user.email
    # Now we try to modify the authorizer of many users with a single call
    params = {
        "role": UserRole.citizen.value
    }
    data = {
        "authorizer": "admin1@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are at least 13 users with role citizen (see setup fixture, plus test_admin user)
    # They should be updated to have "admin1@example.com" as their authorizer
    assert response_data["updated_count"] >= 13
    statement = select(User).where(User.role==UserRole.citizen.value)
    citizens = db_session.exec(statement).all()
    # We verify that all citizens have "admin1@example.com" as their authorizer
    for citizen in citizens:
        assert citizen.authorized_by == "admin1@example.com"
    # Now we try to modify the authorizer, using an invalid new authorizer
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "nonexistent@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(chief1)
    # The authorizer must be an existing user
    assert chief1.authorized_by != "nonexistent@example.com"
    # Note: the new authorizer must be an "officer" or an "admin"
    # if we use a normal user (or a chief) as new authorizer, the update will fail
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "chief2@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(chief1)
    # The authorizer must be an existing user
    assert chief1.authorized_by != "chief2@example.com"
    # Now we use an officer as new authorizer, and the update will succeed
    # if we use a normal user (or a chief) as new authorizer, the update will fail
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "officer2@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(chief1)
    assert chief1.authorized_by == "officer2@example.com"

async def test_promote_users_modify_type_called_by_admin(client, db_session, redis_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "type": UserType.chief.value
    }
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    # The user should be normal type before
    assert testuser1.is_chief == False
    assert testuser1.is_officer == False 
    assert testuser1.is_admin == False 
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Admin role can modify the type of any user
    assert response_data["updated_count"] == 1
    # We verify the update in the database
    db_session.refresh(testuser1)
    assert testuser1.is_chief == True
    assert testuser1.is_officer == False
    assert testuser1.is_admin == False
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # in Redis cache, the chief users just promoted should be removed from chief demoted zset
    # so, the user should not be present in the chief demoted zset
    chief_demotion_key = get_redis_chief_demotions_key(str(testuser1.id))
    chief_demoted = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted is None
    # We can also manually add, in Redis, a gps chief location for testuser1
    chief_location_key = get_redis_chief_locations_key(str(testuser1.id))
    positions = await redis_session.geopos(chief_location_key, str(testuser1.id))
    assert all(p is None for p in positions) # The user should not have a location in Redis before we add it
    longitude = 12.34
    latitude = 56.78
    await redis_session.geoadd(chief_location_key, (longitude, latitude, str(testuser1.id)))
    positions = await redis_session.geopos(chief_location_key, str(testuser1.id))
    assert positions is not None
    assert all(p is not None for p in positions) # The user should have a location in Redis after we add it
    # Now we try to demote the same user back to normal type, but this time we use an officer token, so the update should fail because only admin can modify the type of the users
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "type": UserType.base.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Now, we verify that testuser1 is not a chief anymore
    db_session.refresh(testuser1)
    assert testuser1.is_chief == False
    assert testuser1.is_officer == False
    assert testuser1.is_admin == False
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # in Redis cache, the chief users just demoted should be added to chief demoted zset
    # so, the user should be present in the chief demoted zset
    chief_demoted = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted is not None
    # The chief location should be removed from Redis when the user is demoted from chief
    positions = await redis_session.geopos(chief_location_key, str(testuser1.id))
    assert all(p is None for p in positions)
    # Now we try to demote all current chiefs to normal type
    # We add a gps position in Redis for all current chiefs to verify that the positions are removed when they are demoted
    statement = select(User).where(User.is_chief==True)
    chiefs = db_session.exec(statement).all()
    for chief in chiefs:
        chief_location_key = get_redis_chief_locations_key(str(chief.id))
        await redis_session.geoadd(chief_location_key, (longitude, latitude, str(chief.id)))
    params = {
        "type": UserType.chief.value
    }
    data = {
        "type": UserType.base.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # All chief users should be demoted to normal type
    assert response_data["updated_count"] >= 4 # In the setup fixture we created 4 chief users, so at least those should be updated
    # We verify that all chief users are now normal type
    statement = select(User).where(User.is_chief==True)
    chiefs = db_session.exec(statement).all()
    assert len(chiefs) == 0
    # And all those users should be present in the chief demoted zset in Redis
    for chief in chiefs:
        # The chief users just demoted should be added to chief demoted zset
        chief_demotion_key = get_redis_chief_demotions_key(str(chief.id))
        chief_demoted = await redis_session.zscore(chief_demotion_key, str(chief.id))
        assert chief_demoted is not None
        # The chief location should be removed from Redis when the user is demoted from chief
        chief_location_key = get_redis_chief_locations_key(str(chief.id))
        positions = await redis_session.geopos(chief_location_key, str(chief.id))
        assert all(p is None for p in positions)

## TESTS: POST /api/users/promote-by-emails

def test_promote_users_by_emails_not_authorized_missing_token(client):
    params = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    data = {
        "role": UserRole.volunteer.value
    }
    response = client.post("/api/users/promote-by-emails", params=params, json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_promote_users_by_emails_not_authorized_invalid_token(client):
    params = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    data = {
        "role": UserRole.volunteer.value
    }
    response = client.post("/api/users/promote-by-emails", params=params, json=data, headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail
