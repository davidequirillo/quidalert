# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from models.general import User, UserRole, UserLanguage, UserStatus, UserType
from core.exceptions import (
    token_not_valid_exception, forbidden_exception,
    invalid_request_exception)
from services.security import now_tz_naive
from routers.users import EMAIL_LIST_MAX_LENGTH_FOR_SEARCH, get_users
from tests.fixtures.users import setup_and_teardown # required (fixture automatically called)

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

def test_get_users_forbidden_access_by_baseuser(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_baseuser['access_token']}"}
    response = client.get("/api/users", headers=headers)
    # Base user role is not allowed to access this endpoint, only admin or officers can access it
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_users_by_invalid_role(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    search_params = {
        "role": "invalid_role"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "role not admitted" in response.json()["detail"]
    # Citizen role is also invalid, if used in the search. 
    # Allowed roles for search operations are contained in UserRole enum. 
    # (see UserRole enum in models/general.py, and get_users API in routes/users.py)
    search_params = {
        "role": "citizen"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "role not admitted" in response.json()["detail"]

def test_get_users_by_invalid_type(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    search_params = {
        "type": "invalid_type"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "type not admitted" in response.json()["detail"]
    # Base type is invalid too, if used in the search. 
    # Allowed types for search operations are "admin", "officer", "chief"
    # (see get_users API in routes/users.py)
    search_params = {
        "type": UserType.base.value
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "type not admitted" in response.json()["detail"]

def test_get_users_by_invalid_status(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    search_params = {
        "status": "invalid_status"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "status not admitted" in response.json()["detail"]
    # Status "ok" is invalid too, if used in the search. 
    # Allowed values for search operations are "blocked", "unreliable"
    # (see get_users API in routes/users.py)
    search_params = {
        "status": UserStatus.ok.value
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "status not admitted" in response.json()["detail"]

def test_get_users_by_firstname_without_surname(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    search_params = {
        "firstname": "John"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "cannot be used without surname" in response.json()["detail"]

def test_get_users_by_authorizer_called_by_an_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    # An officer cannot call the API with "authorizer" parameter, 
    # because he can only see the users (in bulk mode) authorized by him
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    search_params = {
        "authorizer": "officer1@example.com"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == "Only admins can filter by authorizer"

def test_get_users_by_email_success(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    # We select a user from db to search for it by email (see setup fixture)
    statement = select(User).where(User.email == "testuser5@example.com")
    testuser5 = db_session.exec(statement).first()
    assert testuser5 is not None
    # Now we search for it by email using the API
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    search_params = {
        "email": "testuser5@example.com"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    # Check that the returned user data matches the user we searched for
    assert user_data["id"] == str(testuser5.id)
    assert user_data["email"] == testuser5.email
    assert user_data["firstname"] == testuser5.firstname
    assert user_data["surname"] == testuser5.surname
    # Some security checks
    assert "password" not in user_data
    assert "password_hash" not in user_data
    assert "activation_code" not in user_data
    assert "reset_code_hash" not in user_data
    assert "login_code_hash" not in user_data

def test_get_users_by_email_with_wrong_role(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    # We select a user from db to search for it by email (see setup fixture)
    statement = select(User).where(User.email == "officer5@example.com")
    officer5 = db_session.exec(statement).first()
    assert officer5 is not None
    # Officer5 is a volunteer
    assert officer5.role == UserRole.volunteer.value
    # Now we search for it by email using the API, but we set the "role" parameter to a different role than the actual user's role
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    search_params = {
        "email": "officer5@example.com",
        "role": UserRole.medic.value
    }
    # Even if the role is different, the search by email has a particular behavior.
    # Searching by email will ignore the other search parameters (see get_users API in routes/users.py), 
    # so the search will succeed and return the user anyway
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    assert data["users"][0]["email"] == officer5.email
    assert data["users"][0]["firstname"] == officer5.firstname
    assert data["users"][0]["surname"] == officer5.surname

def test_get_users_by_email_not_found(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    search_params = {
        "email": "not.found@example.com"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "users" in response_data
    assert len(response_data["users"]) == 0

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
    # This should be 35 (see setup fixture, plus test_admin fixture)
    total_users_num = len(users)
    assert total_users_num == 35
    # We add 5 more users to make the total count a perfect multiple of the limit (40 users with limit 10)
    for i in range(36, 41):
        test_user = User(
            email=f"testuser{i}@example.com",
            firstname=f"Test{i}",
            surname=f"User{i}",
            is_active=True,
            role=None,
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
    # Some security checks: ensure that no sensitive information is returned in the user data
    for user_data in page_entries:
        assert "password" not in user_data
        assert "password_hash" not in user_data
        assert "activation_code" not in user_data

def test_get_users_called_by_an_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    statement = select(User)
    users = db_session.exec(statement).all()
    assert users is not None
    total_users_num = len(users)
    # Here, no user in the test database is authorized by test_officer. We verify it
    for u in users:
        assert u.authorized_by != test_officer['user'].email
    # We create 7 users authorized by test_officer
    for i in range(total_users_num + 1, total_users_num + 8):
        test_user = User(
            email=f"testuser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"User{i}",
            surname=f"Surname{i}",
            is_active=True,
            role=None,
            authorized_by=user.email,
            authorized_at=now_tz_naive(),
            language=UserLanguage.en.value
        )
        db_session.add(test_user)
    db_session.commit()
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    # Now we call the API to get all users (remember that test_officer is the caller)
    response = client.get("/api/users", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) > 0
    # The officer should only see (in bulk mode) the users that he authorized, 
    # not all users in db, so they should be 7
    assert len(data["users"]) == 7
    for user_data in data["users"]:
        assert user_data["authorized_by"] == user.email
    # But an officer can see all the other users if he searches them by email (single user search), 
    # even if they are not authorized by him, example:
    statement = select(User).where(User.email == "testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1 is not None
    assert testuser1.authorized_by != user.email # testuser1 is not authorized by test_officer for sure (see setup fixture)
    search_params = {
        "email": "testuser1@example.com"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["email"] == "testuser1@example.com"
    # Now we try to set "authorizer" parameter in the search (to search for all users authorized by "officer1")
    # But it will fail, because test_officer can only see his users (in bulk mode), not users authorized by "officer1"
    search_params = {
        "authorizer": "officer1@example.com"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == forbidden_exception().status_code
    assert "Only admins can" in response.json()["detail"]

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
    # The admin can get all users in bulk (obviously in pagination)
    assert len(data["users"]) > 0
    assert total_users_num < 100 # the default limit for pagination
    assert len(data["users"]) == total_users_num
    # Now we try to do the query with "authorizer" parameter,
    # searching for all users authorized by "officer1@example.com"
    # Admin obviously has the permission to do this
    search_params = {
        "authorizer": "officer1@example.com"
    }
    statement = select(User).where(User.authorized_by=="officer1@example.com")
    result = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    assert len(data["users"]) == len(result)
    assert len(data["users"]) > 0 # see setup fixture, there are for sure some users authorized by officer1, and test_admin can see them all
    for user_data in data["users"]:
        assert user_data["authorized_by"] == "officer1@example.com"

def test_get_users_by_type_and_role(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for officers with role volunteer (there are for sure 5 of them, see setup fixtures)
    search_params = {
        "type": UserType.officer.value,
        "role": UserRole.volunteer.value,
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.is_officer == True, User.role == UserRole.volunteer.value)
    results = db_session.exec(statement).all()
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    # And there are for sure 5 officers with role volunteer (see setup fixtures)
    assert len(data["users"]) == 5
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_officer"] == True
    # Now we search for chiefs with role usar (there are for sure 4 of them, see setup fixtures)
    search_params = {
        "type": UserType.chief.value,
        "role": UserRole.usar.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.is_chief == True, User.role == UserRole.usar.value)
    results = db_session.exec(statement).all()
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    # And there are for sure 4 chiefs with role usar (see setup fixtures)
    assert len(data["users"]) == 4
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_chief"] == True
    # Another example: we search for all volunteers
    search_params = {
        "role": UserRole.volunteer.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.role == UserRole.volunteer.value)
    results = db_session.exec(statement).all()
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    # And there are for sure at least 9 volunteers (officers + chiefs + some base users, see setup fixtures)
    assert len(data["users"]) >= 9
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["role"] == UserRole.volunteer.value
    # Now we search for all users with type "officer" and role "firefighter" (which should be 0)
    # (see the setup fixture for users, there are no officers with role firefighter)
    search_params = {
        "type": UserType.officer.value,
        "role": UserRole.firefighter.value
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0
    # Now we search for all firefighters in general
    search_params = {
        "role": UserRole.firefighter.value
    }
    statement = select(User).where(
        User.role == UserRole.firefighter.value)
    results = db_session.exec(statement).all()
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == len(results)
    # Now we search for all policemen
    search_params = {
        "role": UserRole.policeman.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(
        User.role == UserRole.policeman.value)
    results = db_session.exec(statement).all()
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # Check that the API returns the same number of users as the manual query result
    assert len(data["users"]) == len(results)

def test_get_users_by_many_parameters(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We fetch a specific user from the database
    # We will use this user to search for it by firstname, surname, role, type, and authorizer
    statement = select(User).where(User.email=="officer3@example.com")
    officer3: User = db_session.exec(statement).first()
    assert officer3 is not None
    # See setup fixtures if you want to verify firstname and surname of this user
    assert officer3.firstname == "Officer3"
    assert officer3.surname == "User3"
    search_params = {
        "firstname": officer3.firstname,
        "surname": officer3.surname,
        "type": UserType.officer.value,
        "role": officer3.role,
        "authorizer": officer3.authorized_by
    }
    # Now we call the API
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # Note: the result is only 1
    assert len(data["users"]) == 1
    user_data = data["users"][0]
    assert user_data["firstname"] == officer3.firstname
    assert user_data["surname"] == officer3.surname
    assert user_data["email"] == officer3.email
    assert user_data["is_admin"] == False
    assert user_data["is_officer"] == True
    assert user_data["is_chief"] == False
    assert user_data["role"] == officer3.role
    assert user_data["is_reliable"] == True
    assert user_data["is_blocked"] == False
    # Now we try to do a similar search, but with a wrong parameter
    search_params["role"] = UserRole.firefighter.value # wrong role, the user is not a firefighter
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The result is 0, because the search parameters do not match perfectly with officer3@example.com
    # No user is found that matches all the search parameters, so the result is empty
    assert len(data["users"]) == 0

def test_get_users_by_firstname_and_surname(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    assert user.firstname == "Firstname1"
    assert user.surname == "Surname1"
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for a specific user with firstname and surname
    search_params = {
        "firstname": "Firstname1",
        "surname": "Surname1"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # There are 2 users with firstname "Firstname1" and surname "Surname1" (one in the setup fixture and one is test_admin fixture)
    assert len(data["users"]) == 2
    user_data1 = data["users"][0]
    user_data2 = data["users"][1]
    assert user_data1["firstname"] == "Firstname1"
    assert user_data1["surname"] == "Surname1"
    assert user_data2["firstname"] == "Firstname1"
    assert user_data2["surname"] == "Surname1"
    # We confirm this check with a manual query to the database
    statement = select(User).where(User.firstname=="Firstname1").where(User.surname=="Surname1")
    results = db_session.exec(statement).all()
    assert len(results) == 2
    assert len(data["users"]) == len(results)

def test_get_users_by_surname_only(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We search for all users with surname "Surname3"
    search_params = {
        "surname": "Surname3"
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.surname=="Surname3")
    results = db_session.exec(statement).all()
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    # there is for sure 1 user with surname "Surname3" (see setup fixtures)
    assert len(data["users"]) == len(results)
    assert len(data["users"]) == 1
    for user_data in data["users"]:
        assert user_data["surname"] == "Surname3"
    # Another example: we search for all users with surname "Surname1"
    statement = select(User).where(User.surname=="Surname1")
    results = db_session.exec(statement).all()
    search_params = {
        "surname": "Surname1"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    # there are for sure 2 users with surname "Surname1" (see setup fixtures and test_admin fixture)
    assert len(data["users"]) == len(results)
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["surname"] == "Surname1"

def test_get_users_by_firstname_only(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # Note: if firstname parameter is provided without a surname parameter,
    # the search is not valid, because the API requires that if firstname is provided, surname must also be provided 
    # (see get_users API in routes/users.py)
    search_params = {
        "firstname": "Firstname4"
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == invalid_request_exception().status_code
    assert "cannot be used without surname" in response.json()["detail"]

def test_get_users_by_status(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # In the database there are no blocked users, we verify it
    statement = select(User).where(User.is_blocked == True)
    results = db_session.exec(statement).all()
    assert len(results) == 0
    # We verify it, calling API for blocked users, which should return an empty list
    search_params = {
        "status": UserStatus.blocked.value
    }
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    assert len(data["users"]) == 0
    # Now we add 2 blocked users in the database, to do a new search for blocked users
    for i in range(1, 3):
        test_user = User(
            email=f"blockeduser{i}@example.com",
            password_hash="hashed_password",
            firstname=f"Blocked{i}",
            surname=f"User{i}",
            is_blocked=True,
            is_reliable=False,
            role=None
        )
        db_session.add(test_user)
    db_session.commit()
    search_params = {
        "status": UserStatus.blocked.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.is_blocked == True)
    results = db_session.exec(statement).all()
    assert len(results) == 2
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_blocked"] == True
        assert user_data["is_reliable"] == False # blocked users are also unreliable
    # Now we add 2 unreliable users in the database, to do a new search for unreliable users
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
    search_params = {
        "status": UserStatus.unreliable.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.is_reliable == False)
    results = db_session.exec(statement).all()
    # The result is 4, because in this moment there are the following users:
    # 2 blocked users (blocked users are also unreliable) 
    # 2 unreliable users not blocked
    assert len(results) == 4
    # Now we call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["is_reliable"] == False
    # Now we search for unreliable users with role=volunteers (should be 2)
    search_params = {
        "status": UserStatus.unreliable.value,
        "role": UserRole.volunteer.value
    }
    # Manual query to get the expected results from the database
    statement = select(User).where(User.is_reliable == False).where(User.role == UserRole.volunteer.value)
    results = db_session.exec(statement).all()
    assert len(results) == 2
    # We call the API with the same search parameters
    response = client.get("/api/users", headers=headers, params=search_params)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The API should return the same number of users as the manual query result
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

def test_get_users_by_emails_called_with_get_method(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = { "emails": ["testuser1@example.com", "testuser2@example.com"] }
    response = client.get("/api/users/get-by-emails", headers=headers, params=data)
    # If the method is GET, the api call becomes "GET /api/users/get-by-emails"
    # where the string "get-by-emails" is interpreted as an id to search by,
    # so the API will try to find a user with id="get-by-emails" and it will not find it, returning 404 Not Found
    assert response.status_code == status.HTTP_404_NOT_FOUND
    # The correct method is POST, so the API should be called like this:
    data = { "emails": ["testuser1@example.com", "testuser2@example.com"] }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK

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

def test_get_users_by_emails_too_many_input_emails(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We create a list with too many input emails
    emails = [f"user{i}@example.com" for i in range(EMAIL_LIST_MAX_LENGTH_FOR_SEARCH + 1)]
    data = {"emails": emails}
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == invalid_request_exception().status_code
    assert "Email list too long" in response.json()["detail"]

def test_get_users_by_emails_many_input_emails(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    # We create a list with the maximum allowed input emails
    emails = [f"testuser{i}@example.com" for i in range(EMAIL_LIST_MAX_LENGTH_FOR_SEARCH)]
    data = {"emails": emails}
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    assert "users" in response.json()
    assert len(response.json()["users"]) <= EMAIL_LIST_MAX_LENGTH_FOR_SEARCH
    # There are for sure some users in the database with emails in the list, so the result should not be empty (see setup fixtures)
    assert len(response.json()["users"]) > 0 

def test_get_users_by_emails_not_found(client, test_admin):
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
    # Now we call the API with the emails of the users we just queried from the database
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The result of the API call is equal to the result from the query
    assert len(data["users"]) == len(results)
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
    # Now we call the API with duplicate emails in the input list
    headers = {"Authorization": f"Bearer {test_admin['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The result of the API call is equal to the result from the query
    assert len(data["users"]) == len(results)
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser2@example.com"]
        # Some security checks
        assert "password" not in user_data
        assert "password_hash" not in user_data
        assert "activation_code" not in user_data

def test_get_users_by_emails_called_by_an_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    # We select some users from db to get their emails and check the response
    statement = select(User).where(User.email.in_(["testuser1@example.com", "testuser2@example.com"])) # type:ignore
    results = db_session.exec(statement).all()
    assert len(results) == 2
    # Now we call the API with the emails of the users we just queried from the database
    headers = {"Authorization": f"Bearer {test_officer['access_token']}"}
    data = {
        "emails": ["testuser1@example.com", "testuser2@example.com"]
    }
    response = client.post("/api/users/get-by-emails", headers=headers, json=data)
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert "users" in data
    # The officer can see the users if he searches them by emails, 
    # even if they are not authorized by him, because conceptually 
    # the officer should be able to see any user if he knows their email
    assert len(data["users"]) == len(results)
    assert len(data["users"]) == 2
    for user_data in data["users"]:
        assert user_data["email"] in ["testuser1@example.com", "testuser2@example.com"]
        # Some security checks
        assert "password" not in user_data
        assert "password_hash" not in user_data
        assert "activation_code" not in user_data

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
            role=None,
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
