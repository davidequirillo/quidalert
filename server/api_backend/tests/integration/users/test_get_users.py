# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from fastapi import status
from sqlmodel import select, delete
from models.general import User, UserRole, UserLanguage, UserStatus, UserType
from core.exceptions import token_not_valid_exception, forbidden_exception
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

## TESTS: GET /api/users

def test_get_users_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    response = client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_users_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    response = client.get("/api/users", headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_users_forbidden_access_by_chief(client, test_chief):
    user: User = test_chief['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_chief['access_token']}"}
    response = client.get("/api/users", headers=headers)
    # Chief role is not allowed to access this endpoint, only admin or officers can access it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_users_by_email_success(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    statement = select(User).where(User.email == "testuser5@example.com")
    user5 = db_session.exec(statement).first()
    assert user5 is not None
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    data = {
        "email": "testuser5@example.com"
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["id"] == str(user5.id)
    assert user_data["email"] == "testuser5@example.com"
    assert "password" not in user_data
    assert "password_hash" not in user_data

def test_get_users_by_email_not_found(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "email": "not.found@example.com"
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0

def test_get_users_pagination(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # We select all users from db to get the total count and check pagination
    statement = select(User)
    users = db_session.exec(statement).all()
    # This should be 35 (see setup fixture, plus test_admin)
    total_users_num = len(users)
    assert total_users_num == 35
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "limit": 10
    }
    # Get the first page
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the last page (should have 5 entries)
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == total_users_num % 10
    assert len(page_entries) == 5
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page (should be empty)
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor is None

def test_get_users_pagination_with_perfect_multiple_of_limit(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # We select all users from db to get the total count and check pagination
    statement = select(User)
    users = db_session.exec(statement).all()
    # This should be 35 (see setup fixture, plus test_admin)
    total_users_num = len(users)
    assert total_users_num == 35
    # We add 5 more users to make the total count a perfect multiple of the limit (40 users with limit 10)
    for i in range(36, 41):
        test_user = User(
            email=f"testuser{i}@example.com",
            firstname=f"Test{i}",
            surname=f"User{i}",
            is_active=True,
            role=UserRole.citizen.value,
            authorized_by=user.email,
            authorized_at=now_tz_naive(),
            password_hash="hashed_password",    
        )
        db_session.add(test_user)
    db_session.commit()
    statement = select(User)
    users = db_session.exec(statement).all()
    total_users_num = len(users)
    assert total_users_num == 40
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "limit": 10
    }
    # Get the first page
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the second page
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the third page
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the fourth page (should have 10 entries)
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page (should be empty)
    data["last_seen_id"] = next_cursor
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor is None

def test_get_users_pagination_default_limit(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    statement = select(User)
    users = db_session.exec(statement).all()
    total_users_num = len(users)
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # Get the first page without specifying the limit (should use default limit of 100)
    response = client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == total_users_num if total_users_num < 100 else 100
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Now we try to specify a different limit other than the default
    data = {
        "limit": 5
    }
    # It will still return 100 entries (or total_users_num if less than 100) because the limit is not in [10, 100, 1000] possible limits
    response = client.get("/api/users", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == (total_users_num if total_users_num < 100 else 100)
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    for user_data in page_entries:
        assert "password" not in user_data
        assert "password_hash" not in user_data

def test_get_users_called_by_an_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    statement = select(User)
    users = db_session.exec(statement).all()
    assert users is not None
    total_users_num = len(users)
    # Create 7 users authorized by test_officer
    for i in range(total_users_num + 1, total_users_num + 8):
        test_user = User(
            email=f"testuser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"User{i}",
            surname=f"Surname{i}",
            is_active=True,
            role=UserRole.citizen.value,
            authorized_by=user.email,
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(test_user)
    db_session.commit()
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    # The officer should only see (in bulk) the users that he authorized, so it should be 7
    assert len(data["users"]) == 7
    for user_data in data["users"]:
        assert user_data["authorized_by"] == user.email
    # But the user can see the other users if he search them by email (a single user at a time)
    # Example
    statement = select(User).where(User.email == "testuser1@example.com")
    user1 = db_session.exec(statement).first()
    assert user1 is not None
    assert user1.authorized_by != user.email # testuser1 is not authorized by test_officer
    data = {
        "email": "testuser1@example.com"
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["email"] == "testuser1@example.com"
    # Now we try to set "authorizer" parameter
    # But it will fail, because the officer can only see his users (in bulk)
    data = {
        "authorizer": "officer1@example.com"
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0
    # But if "authorizer" is equal to test_officer.email, it will work
    data = {
        "authorizer": user.email
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 7

def test_get_users_called_by_an_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    statement = select(User)
    users = db_session.exec(statement).all()
    assert users is not None
    total_users_num = len(users)
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    response = client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The admin can see all users
    assert len(data["users"]) > 0
    assert len(data["users"]) == total_users_num
    # Now we try to do the query with "authorizer" parameter
    data = {
        "authorizer": "officer1@example.com"
    }
    statement = select(User).where(User.authorized_by=="officer1@example.com")
    result = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(result)

def test_get_users_by_type_and_role(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for all officers with role "citizen"
    data = {
        "type": "officer",
        "role": UserRole.citizen.value
    }
    statement = select(User).where(User.is_officer == True).where(User.role == UserRole.citizen.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_officer"] == True
        assert user_data["role"] == "citizen"
    # Now we search for all chiefs with role "citizen"
    data = {
        "type": "chief",
        "role": UserRole.citizen.value
    }
    statement = select(User).where(User.is_chief == True).where(User.role == UserRole.citizen.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_chief"] == True
        assert user_data["role"] == UserRole.citizen.value
    # Now we search for all admins with role "citizen"
    data = {
        "type": "admin",
        "role": UserRole.citizen.value
    }
    statement = select(User).where(User.is_admin == True).where(User.role == UserRole.citizen.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_admin"] == True
        assert user_data["role"] == UserRole.citizen.value
    # Now we search for all users with role "citizen" (without specifying the type)
    data = {
        "role": UserRole.citizen.value
    }
    statement = select(User).where(User.role == UserRole.citizen.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # There are at least 13 users with role "citizen" (see setup fixture, and the test_admin user that is a citizen)
    assert user.role == UserRole.citizen.value # test_admin user is a citizen
    assert len(data["users"]) >= 13 
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["role"] == UserRole.citizen.value
    # Now we search for all base users with role "citizen"
    data = {
        "type": UserType.base.value,
        "role": UserRole.citizen.value
    }
    statement = select(User).where(
        User.is_chief == False).where(
            User.is_admin == False).where(
                User.is_officer == False).where(User.role == UserRole.citizen.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_chief"] == False
        assert user_data["is_admin"] == False
        assert user_data["is_officer"] == False
        assert user_data["role"] == UserRole.citizen.value
    # Now we search for all users with type "officer" and role "firefighter" (which should be 0)
    data = {
        "type": "officer",
        "role": UserRole.firefighter
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0
    # Now we search for all firefighters (base users)
    data = {
        "type": UserType.base.value,
        "role": UserRole.firefighter.value
    }
    statement = select(User).where(
        User.is_admin == False).where(
            User.is_officer == False).where(
                User.is_chief == False).where(
                    User.role == UserRole.firefighter.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)

def test_get_users_by_all_parameters(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for a specific user with all parameters
    statement = select(User).where(User.email=="testuser2@example.com")
    res_user: User = db_session.exec(statement).first()
    assert res_user is not None
    data = {
        "firstname": "Firstname2",
        "surname": "Surname2",
        # "email": "testuser2@example.com", we don't specify email as search filter
        "type": UserType.base.value,
        "role": res_user.role,
        "status": UserStatus.ok.value,
        "authorizer": res_user.authorized_by
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # Note: the result is only 1. Even test_admin user has the same firstname and surname
    # but it's authorized by a different user, so it will not be included in the result
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["firstname"] == res_user.firstname
    assert user_data["surname"] == res_user.surname
    assert user_data["is_admin"] == False
    assert user_data["is_officer"] == False
    assert user_data["is_chief"] == False
    assert user_data["role"] == res_user.role
    assert user_data["is_reliable"] == True
    assert user_data["is_blocked"] == False
    assert user_data["email"] == res_user.email

def test_get_users_by_firstname_and_surname(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    assert user.firstname == "Firstname1"
    assert user.surname == "Surname1"
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for a specific user with firstname and surname
    data = {
        "firstname": "Firstname1",
        "surname": "Surname1"
    }
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # There are 2 users with firstname "Firstname1" and surname "Surname1" (one in the setup fixture and one is test_admin user)
    assert len(data["users"]) == 2
    user_data1 = data["users"][0]
    user_data2 = data["users"][1]
    assert user_data1["firstname"] == "Firstname1"
    assert user_data1["surname"] == "Surname1"
    assert user_data2["firstname"] == "Firstname1"
    assert user_data2["surname"] == "Surname1"

def test_get_users_by_status(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for all users with status "ok"
    data = {
        "status": UserStatus.ok.value
    }
    statement = select(User).where(User.is_blocked == False).where(User.is_reliable == True)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_blocked"] == False
        assert user_data["is_reliable"] == True
    # Now we search for all users with status "blocked" (we add 2 blocked users)
    for i in range(1, 3):
        test_user = User(
            email=f"blockeduser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Blocked{i}",
            surname=f"User{i}",
            is_blocked=True,
            is_reliable=False,
            role=UserRole.citizen.value 
        )
        db_session.add(test_user)
    db_session.commit()
    data = {
        "status": UserStatus.blocked.value
    }
    statement = select(User).where(User.is_blocked == True).where(User.is_reliable == False)
    results = db_session.exec(statement).all()
    assert len(results) == 2
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_blocked"] == True
        assert user_data["is_reliable"] == False # blocked users are also unreliable
    # Now we search for all users with status "unreliable" (we add 2 unreliable users)
    for i in range(1, 3):
        test_user = User(
            email=f"unreliableuser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Unreliable{i}",
            surname=f"User{i}",
            is_reliable=False,
            is_blocked=False,
            role=UserRole.volunteer.value
        )
        db_session.add(test_user)
    db_session.commit()
    data = {
        "status": UserStatus.unreliable.value
    }
    statement = select(User).where(User.is_reliable == False)
    results = db_session.exec(statement).all()
    # 2 blocked users that are also unreliable, plus 2 unreliable but not blocked
    assert len(results) == 4
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_reliable"] == False
    # Now we search for unreliable and role=volunteers (should be 2)
    data = {
        "status": UserStatus.unreliable.value,
        "role": UserRole.volunteer.value
    }
    statement = select(User).where(User.is_reliable == False).where(User.role == UserRole.volunteer.value)
    results = db_session.exec(statement).all()
    assert len(results) == 2
    response = client.get("/api/users", headers=headers, params=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_reliable"] == False
        assert user_data["role"] == UserRole.volunteer.value

## TESTS: POST "/api/users/get-by-emails"

def test_get_users_by_emails_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_users_by_emails_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_users_by_emails_forbidden_access(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_baseuser['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    # Base user role is not allowed to access this endpoint, only admin or officers can access it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_user_by_emails_not_found(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "emails": ["nonexistentuser1@example.com", "nonexistentuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0

def test_get_users_by_emails_success(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # We select some users from db to get their emails and check the response
    statement = select(User).where(User.email.in_(["testuser1@example.com", "testuser2@example.com"])) # type:ignore
    results = db_session.exec(statement).all()
    assert len(results) == 2
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser2@example.com"]
        assert "password" not in user_data
        assert "password_hash" not in user_data
    # Now we try with 1 existing email and one non-existing email
    data = {
        "emails": ["testuser1@example.com", "nonexistentuser@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["email"] == "testuser1@example.com"
    assert "password" not in user_data
    assert "password_hash" not in user_data

def test_get_users_by_emails_with_duplicates(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # We select some users from db to get their emails and check the response
    statement = select(User).where(User.email.in_(["testuser1@example.com", "testuser2@example.com"])) # type:ignore
    results = db_session.exec(statement).all()
    assert len(results) == 2
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser2@example.com"]
        assert "password" not in user_data
        assert "password_hash" not in user_data

def test_get_users_by_emails_called_by_an_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    # We select some users from db to get their emails and check the response
    statement = select(User).where(User.email.in_(["testuser1@example.com", "testuser2@example.com"])) # type:ignore
    results = db_session.exec(statement).all()
    assert len(results) == 2
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The officer can see the users if he search them by email, 
    # even if they are not authorized by him, because conceptually 
    # the officer should be able to see any user if he knows their email
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser2@example.com"]
        assert "password" not in user_data
        assert "password_hash" not in user_data

def test_get_users_by_emails_with_pagination(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # See pytest fixture "setup_users" for the creation of 22 users with emails
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We get all base users by emails (22 base users created in the fixture)
    data = {
        "emails": [f"testuser{i}@example.com" for i in range(1, 23)],
    }
    params = {
        "limit": 10
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "users" in response_data
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    # Get the remaining users
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 2
    assert next_cursor is not None
    # Get the next page (should be empty)
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor is None

def test_get_users_by_emails_with_perfect_multiple_of_limit(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # We add 8 users with specific emails to make the total count of users
    # a perfect multiple of the limit (30 users with limit 10)
    for i in range(23, 31):
        test_user = User(
            email=f"testuser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Test{i}",
            surname=f"User{i}",
            is_active=True,
            role=UserRole.citizen.value,
            authorized_by=user.email,
        )
        db_session.add(test_user)
    db_session.commit()
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "emails": [f"testuser{i}@example.com" for i in range(1, 31)]
    }
    params = {
        "limit": 10
    }
    # Get the first page
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the second page
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the third page (should have 10 entries)
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Get the next page (should be empty)
    params["last_seen_id"] = next_cursor
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor is None

def test_get_users_by_emails_with_default_limit(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We get all base users by emails (22 base users created in the fixture)
    data = {
        "emails": [f"testuser{i}@example.com" for i in range(1, 23)]
    }
    # Get the first page without specifying the limit (should use default limit of 100)
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "users" in response_data
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 22 # all users are returned because they are less than the default limit of 100
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]
    # Now we try to specify a different limit other than the default
    data = {
        "emails": [f"testuser{i}@example.com" for i in range(1, 23)]
    }
    params = {
        "limit": 5
    }
    # It will still return 22 entries because the limit is not in [10, 100, 1000] possible limits
    response = client.post("/api/users/get-by-emails", headers=headers, json=data, params=params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "users" in response_data
    page_entries = response_data["users"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 22 # all users are returned because they are less than the default limit of 100
    assert next_cursor is not None
    assert next_cursor == page_entries[-1]["id"]

def test_get_users_by_emails_with_none_input_values(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We get users by emails, but some of the emails in the list are None
    data = {
        "emails": ["testuser1@example.com", None, "testuser3@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_get_users_by_emails_with_empty_input_values(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We get users by emails, but some of the emails in the list are empty strings
    data = {
        "emails": ["testuser1@example.com", "", "testuser3@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # It should return the users with valid emails and ignore the empty email
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser3@example.com"]

def test_get_users_by_emails_with_invalid_input_values(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We get users by emails, but some of the emails in the list are invalid (
    # not in a valid email format)
    data = {
        "emails": ["testuser1@example.com", "invalid-email", "testuser3@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # It should return the users with valid emails and ignore the invalid email
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser3@example.com"]
