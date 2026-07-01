# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from doctest import Example
from fastapi import status
from sqlmodel import select
from core.exceptions import (
    invalid_request_exception,
    token_not_valid_exception,
    forbidden_exception
)
from models.general import (
    User, UserType, UserRole, UserLanguage, UserStatus
)
from services.security import (
    now_tz_naive, ensure_tz_aware
)
from core.dbmgr import (
    get_redis_chief_demotions_key,
    get_redis_chief_locations_key
)
from routers.users import EMAIL_LIST_MAX_LENGTH_FOR_SEARCH
from tests.fixtures.users import setup_and_teardown # required (fixture automatically called)

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
    params = {
        "email": "testuser1@example.com"
    }
    response = client.get("/api/users/promote", params=params, headers=headers)
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
    # Base user role is not allowed to access this endpoint, only admin or officers can access it
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

def test_promote_users_search_by_invalid_role(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "role": "invalid_role"
    }
    data = {
        "role": "citizen",
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "role not admitted" in response.json()["detail"]
    # Another example: we cannot search users by "citizen", because "citizen" is not allowed as a search param (it's allowed only in promotion data)
    # See models/general.py, UserRole enum, and promote_users api call to verify this
    params = {
        "role": "citizen" # not allowed
    }
    data = {
        "role": "citizen", # allowed, if used as update value
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "role not admitted" in response.json()["detail"]

def test_promote_users_search_by_invalid_status(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "status": "invalid_status"
    }
    data = {
        "role": UserRole.medic.value,
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "status not admitted" in response.json()["detail"]
    # Another example: we cannot search users by "ok" status, 
    # because "ok" status is not allowed as a search param (it's allowed only in promotion data)
    # Allowed status values for search are "blocked", "unreliable" 
    params = {
        "status": UserStatus.ok.value # not allowed
    }
    data = {
        "status": UserStatus.ok.value, # allowed, if used as update value
        "role": UserRole.medic.value,
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "status not admitted" in response.json()["detail"]

def test_promote_users_search_by_invalid_type(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "type": "invalid_type"
    }
    data = {
        "role": UserRole.volunteer.value,
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "type not admitted" in response.json()["detail"]
    # Another example: we cannot search users by "base" type, 
    # because "base" type is not allowed as a search param (it's allowed only in promotion data)
    # Allowed types for search are "admin", "officer", "chief" 
    params = {
        "type": UserType.base.value # not allowed here
    }
    data = {
        "type": UserType.base.value, # allowed, if used as update value
        "role": UserRole.medic.value,
        "status": UserStatus.unreliable.value,
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "type not admitted" in response.json()["detail"]

def test_promote_users_search_by_firstname_without_surname(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "firstname": "Firstname1"
    }
    data = {
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "cannot be used without surname" in response.json()["detail"]

def test_promote_users_search_by_authorizer_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # Officer role cannot update users not authorized by them, so the promotion should not be applied
    # They cannot filter users by authorizer, because they are not allowed to update users not authorized by them
    params = {
        "role": UserRole.volunteer.value,
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value,
        "notes": "Example notes",
        "status": UserStatus.unreliable.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert "Only admins can" in response.json()["detail"]

def test_promote_users_search_by_not_enough_keywords(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = { 
        "no good param": "value" # This is not a valid search param, so the API should return an error
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "At least one search filter keyword must be provided" in response.json()["detail"]
    # Another example: 
    # we cannot search users only by "authorizer" filter, 
    # because the authorizer filter is a valid and effective keyword to search for users, 
    # but it's not sufficient (if used alone) to do an efficient search.
    # We need at least one more filter (email, surname, role, status, type). 
    # See promote_users in routes/users.py for details
    params = {
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value,
        "notes": "Example notes"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "At least one search filter keyword must be provided" in response.json()["detail"]

def test_promote_users_modify_type_called_by_officer(client, test_officer):
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
    # Officer role is not allowed to modify the type of the users (only admin can modify it)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # "chief1" is authorized by an admin (see setup fixture)
    # Officer role cannot update users not authorized by them, so the promotion should not be applied
    select_stmt = select(User).where(User.email=="chief1@example.com")
    chief1 = db_session.exec(select_stmt).first()
    assert chief1 is not None
    assert chief1.authorized_by != user.email # The officer is not the authorizer of chief1
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    # Another example
    select_stmt = select(User).where(User.email=="officer1@example.com")
    officer1 = db_session.exec(select_stmt).first()
    assert officer1 is not None
    assert officer1.authorized_by != user.email # The officer is not the authorizer of officer1
    params = {
        "role": UserRole.firefighter.value,
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert "Only admins can" in response.json()["detail"]
    # Now try to promote a user authorized by test_officer, the promotion should be applied
    # But we must first create a user authorized test_officer
    new_user = User(
        email="authorized_by_this_officer@example.com",
        password_hash="hashed_password",
        firstname="Authorized",
        surname="ByThisOfficer",
        is_active=True,
        role=UserRole.volunteer.value,
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
    myuser = db_session.exec(statement).first()
    assert myuser.role == UserRole.medic.value
    assert myuser.updated_by == user.email # The update should be applied by test_officer
    assert myuser.updated_at is not None
    assert myuser.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Note: searching by email ignores the other input parameters, 
    # even if they are set to a different value than the actual user's value,
    # so the update is applied anyway (see promote_users in routes/users.py)
    params = {
        "email": "authorized_by_this_officer@example.com",
        "role": UserRole.policeman.value
    }
    data = {
        "role": UserRole.military.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(myuser)
    assert myuser.role == UserRole.military.value
    # Another example with role and type filters and users not authorized by test_officer
    usar_role_chiefs_stmt = select(User).where(User.is_chief == True, User.role == UserRole.usar.value)
    usar_role_chiefs = db_session.exec(usar_role_chiefs_stmt).all()
    assert len(usar_role_chiefs) == 4 # see setup fixture, there are 4 chiefs with role "usar"
    # All chiefs having role "usar" are not authorized by test_officer
    for u in usar_role_chiefs:
        assert u.authorized_by != test_officer["user"].authorized_by
    params = {
        "type": UserType.chief.value,
        "role": UserRole.usar.value
    }
    data = {
        "role": UserRole.medic.value
    }
    # Now we call the promote API, but it should not modify any users, 
    # because they are not authorized by test_officer,
    # so test_officer has not the permission to promote them
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    # Now we try to change type and role of a user authorized by test_officer
    myuser.role = UserRole.usar.value
    myuser.is_chief = True
    db_session.add(myuser)
    db_session.commit()
    # "Myuser" now has role="usar" and type="chief"
    assert myuser.role == UserRole.usar.value
    assert myuser.is_chief == True
    # Now we re-search for all chiefs having role "usar" in the database
    usar_role_chiefs_stmt = select(User).where(User.is_chief == True, User.role == UserRole.usar.value)
    usar_role_chiefs = db_session.exec(usar_role_chiefs_stmt).all()
    # There are 5 chiefs with role "usar" (4 from setup fixture, and 1 is "myuser" authorized by test_officer)
    assert len(usar_role_chiefs) == 5 
    # We retry the same request, but this time it should update 1 user (myuser), because test_officer is the authorizer of that user
    params = {
        "type": UserType.chief.value,
        "role": UserRole.usar.value
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Myuser (authorized by test_officer) has been updated
    assert response_data["updated_count"] == 1
    db_session.refresh(myuser)
    assert myuser.role == UserRole.medic.value

def test_promote_users_called_by_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We find in the db the user with email "testuser1@example.com"
    select_stmt = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(select_stmt).first()
    assert testuser1 is not None
    assert testuser1.updated_at is None # The user has not been updated yet
    assert testuser1.updated_by is None # The user has not been updated yet
    # Now we call the promote API to change the role of testuser1 to "medic"
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "role": UserRole.medic.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The API has updated 1 user (testuser1) to role "medic"
    # The admin obviously can update any user, no matter who authorized them
    assert response_data["updated_count"] == 1
    # We verify the update in the database
    db_session.refresh(testuser1)
    assert testuser1.role == UserRole.medic.value
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example with authorizer filter (usable only by admins)
    # ...and test_admin is an admin :)
    select_stmt = select(User).where(User.authorized_by=="officer1@example.com")
    user_authorized_by_officer1 = db_session.exec(select_stmt).first()  
    # There is for sure at least one user authorized by officer1@example.com (see the setup fixture)
    assert user_authorized_by_officer1 is not None
    params = {
        "role": user_authorized_by_officer1.role,
        "authorizer": "officer1@example.com"
    }
    data = {
        "role": UserRole.medic.value,
        "notes": "Example notes by test_admin",
        "status": UserStatus.unreliable.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Admin role can update any user, so the promotion has been done
    assert response_data["updated_count"] > 0
    # We verify it in the database
    statement = select(User).where(User.authorized_by=="officer1@example.com", User.role == UserRole.medic.value, User.is_reliable == False)
    updated_users = db_session.exec(statement).all()
    assert len(updated_users) > 0
    for u in updated_users:
        assert u is not None
        assert u.role == UserRole.medic.value
        assert u.is_reliable == False
        assert u.notes == "Example notes by test_admin"
        assert u.updated_by == user.email
        assert u.updated_at is not None
        assert u.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute

def test_promote_users_modify_role_and_notes(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    # Test admin user has no role (it means he has a base role, "citizen")
    assert user.role is None
    assert user.firstname == "Firstname1" # see test_admin fixture in conftest.py
    assert user.surname == "Surname1"
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    params = {
        "firstname": "Firstname1",
        "surname": "Surname1"
    }
    data = {
        "role": UserRole.wateroperator.value,
        "notes": "Promoted to wateroperator by test_admin"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # There are 2 users with firstname "Firstname1" and surname "Surname1" (one in the setup fixture, and one is test_admin user), 
    # so both should be updated to wateroperator role and with the notes
    assert response_data["updated_count"] == 2
    # We verify that test_admin user has been updated to "wateroperator"
    db_session.refresh(user) # Refresh the user instance to get the updated data from the database
    assert user.role == UserRole.wateroperator.value
    assert user.notes == "Promoted to wateroperator by test_admin"
    # We verify that the other user has been updated
    statement = select(User).where(User.firstname=="Firstname1", User.surname=="Surname1", User.email != user.email)
    the_other_user = db_session.exec(statement).first()
    assert the_other_user.role == UserRole.wateroperator.value
    assert the_other_user.notes == "Promoted to wateroperator by test_admin"
    assert the_other_user.email != user.email
    assert the_other_user.updated_by == user.email
    assert the_other_user.updated_at is not None
    assert the_other_user.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example with "role" filter
    select_stmt = select(User).where(User.is_officer == True, User.role == UserRole.volunteer.value)
    volunteer_officers = db_session.exec(select_stmt).all()
    # There are 5 officers with role "volunteer" in db (see setup fixture)
    assert len(volunteer_officers) == 5
    # Now we call the promote API to change all officers having role "volunteer" to role "military"
    params = {
        "type": UserType.officer.value,
        "role": UserRole.volunteer.value,
    }
    data = {
        "role": UserRole.military.value,
        "notes": "Promoted to military by test_admin"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == len(volunteer_officers)
    # Another example
    # Now we try to update all blocked "volunteer" users to military role, 
    # but there are not any blocked users in test database (see setup fixture), so no user should be updated
    select_stmt = select(User).where(User.is_blocked==True)
    blocked_users = db_session.exec(select_stmt).all()
    assert len(blocked_users) == 0
    # Now we do the API call, but it should not modify any user
    params = {
        "role": UserRole.volunteer.value,
        "status": UserStatus.blocked.value
    }
    data = {
        "role": UserRole.military.value,
        "notes": "This user has been promoted to military for testing purposes."
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0

def test_promote_users_modify_status(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    assert user.role is None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We block all volunteer users in the database, 
    # so that we can test the "blocked" status promotion (it's really a demotion, but the API call is the same)
    # We search for all volunteer users in the database, and we verify that they are not blocked yet
    select_stmt = select(User).where(User.role == UserRole.volunteer.value)
    volunteer_users = db_session.exec(select_stmt).all()
    # At least 5 volunteer users should be present in the database (see setup fixture)
    # Before the API call they are "ok", so they have is_blocked=False and is_reliable=True (see setup fixture)
    assert len(volunteer_users) >= 5 
    for v in volunteer_users:
        assert v.is_blocked == False
        assert v.is_reliable == True
    # Now we call the promote API to change all volunteer users to blocked status
    params = {
        "role": UserRole.volunteer.value
    }
    data = {
        "status": UserStatus.blocked.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # The API has updated all volunteer users to blocked status
    assert response_data["updated_count"] == len(volunteer_users)
    # We verify it, querying the database (all volunteers users are "blocked", so 0 volunteers users are "ok")
    statement = select(User).where(User.role == UserRole.volunteer.value, User.is_blocked == True)
    blocked_volunteers = db_session.exec(statement).all()    
    statement = select(User).where(User.role == UserRole.volunteer.value, User.is_blocked == False)
    not_blocked_volunteers = db_session.exec(statement).all()
    assert len(not_blocked_volunteers) == 0
    assert len(blocked_volunteers) == len(volunteer_users) 
    for bv in blocked_volunteers:
        assert bv.is_blocked == True
        assert bv.is_reliable == False # when a user is blocked, it should also be set as not reliable
        assert bv.updated_by == user.email
        assert bv.updated_at is not None
        assert bv.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Another example:
    # we try to declare as "unreliable" a single user with specific email
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "status": UserStatus.unreliable.value
    }
    # Now we do the API call to change his status to "unreliable"
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(testuser1)
    # After the api call, testuser1 is not reliable
    assert testuser1.is_reliable == False
    assert testuser1.is_blocked == False # when a user is set as unreliable, it should not be set as blocked
    # Now we try to change testuser1 status to "ok"
    params = {
        "email": "testuser1@example.com"
    }
    data = {
        "status": UserStatus.ok.value
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(testuser1)
    # After the api call, testuser1 is ok
    assert testuser1.is_reliable == True
    assert testuser1.is_blocked == False

def test_promote_users_modify_authorizer_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We select a user that is not authorized by test_officer, but by an admin (see setup fixture)
    statement = select(User).where(User.email=="chief1@example.com")
    chief1 = db_session.exec(statement).first()
    # Chief1 is authorized by an admin (see setup fixture), not by "test_officer", and not by "officer1@example.com"
    assert chief1.authorized_by != "officer1@example.com"
    assert chief1.authorized_by != user.authorized_by
    # Now we try to modify the authorizer of chief1, but it should not be applied, because test_officer is not the authorizer of chief1
    params = {
        "email": "chief1@example.com"
    }
    data = {
        "authorizer": "officer1@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # 0 users have been updated, because test_officer is not the authorizer of chief1
    # so, the authorizer of chief1 is unchanged
    assert response_data["updated_count"] == 0
    db_session.refresh(chief1)
    assert chief1.authorized_by != "officer1@example.com"
    # Another example:
    # obviously, the officer cannot declare himself as authorizer of a user that is not authorized by him
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
    # Another example:
    # now we try to modify the authorizer of a user owned by test_officer
    user_owned = User(
        email="authorized_by_this_officer@example.com",
        password_hash="hashed_password",
        firstname="Authorized",
        surname="ByThisOfficer",
        is_active=True,
        role=None,
        authorized_by=user.email,
        authorized_at=now_tz_naive(),
        language=UserLanguage.en.value
    )
    db_session.add(user_owned)
    db_session.commit()
    db_session.refresh(user_owned)
    # We verify that the user is owned by test_officer
    assert user_owned.authorized_by == user.email
    # Now we try to modify the authorizer of that user, and it should be applied, because test_officer is the authorizer of that user
    # so, he can modify the authorizer of that user
    params = {
        "email": "authorized_by_this_officer@example.com"
    }
    data = {
        "authorizer": "officer1@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
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
    # Now we try to modify the authorizer of chief1, 
    # and it should be applied, because test_admin is an admin, 
    # and admins can modify any user, even if they are not the authorizer of that user
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(chief1)
    assert chief1.authorized_by == "admin1@example.com"
    assert chief1.updated_by == test_admin["user"].email
    # Admin can also declare himself as authorizer of a user, 
    # even if the user was not previously authorized by him
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
    assert chief1.authorized_by == test_admin["user"].email
    assert chief1.updated_by == test_admin["user"].email
    # Now we try to modify the authorizer of many users with a single call
    select_stmt = select(User).where(User.is_chief==True, User.role==UserRole.usar.value)
    usar_chiefs = db_session.exec(select_stmt).all()
    # There are for sure 4 chiefs with role "usar" in the database (see setup fixture)
    assert len(usar_chiefs) == 4
    # Now we call the promote API to change the authorizer of all chiefs with role "usar" to "admin1@example.com"
    # The api caller is test_admin (test_admin@example.com)
    assert user.email == "test_admin@example.com"
    params = {
        "type": UserType.chief.value,
        "role": UserRole.usar.value
    }
    data = {
        "authorizer": "admin1@example.com"
    }
    response = client.post("/api/users/promote", params=params, json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == len(usar_chiefs)
    # We verify that all "usar" chiefs now have "admin1@example.com" as their authorizer
    # The caller is test_admin, so the updated_by field of all modified users should be set to test_admin's email
    for c in usar_chiefs:
        db_session.refresh(c)
        assert c.authorized_by == "admin1@example.com"
        assert c.updated_by == test_admin["user"].email
    # Another example:
    # now, we try to modify the authorizer of "chief1@example.com", using an invalid new authorizer
    # Obviously, the update should not be applied, because the new authorizer must be an existing user
    # In other words: the caller is test_admin, so he can modify the authorizer (the "authorized_by" field) of any user, 
    # but the new authorizer must be a valid existing user
    select_stmt = select(User).where(User.email=="chief1@example.com")
    chief1 = db_session.exec(select_stmt).first()
    assert chief1 is not None
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
    assert chief1.authorized_by != "nonexistent@example.com"
    # Another example: 
    # the new authorizer must be an "officer" or an "admin"
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
    # The authorizer must be an existing valid admin or officer, not "chief2@example.com"
    assert chief1.authorized_by != "chief2@example.com"
    # Another example:
    # now we use an officer as new authorizer, and the update will succeed
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
    assert chief1.updated_by == test_admin["user"].email

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
    chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted_score is None
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
    # Now we try to demote the same user back to normal type, 
    # and we verify that the chief location in Redis is removed and the user is added to chief demoted zset in Redis
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
    chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted_score is not None
    # we check the timestamp of the chief demotion, it should be recent
    now_timestamp_tz = ensure_tz_aware(now_tz_naive()).timestamp()
    assert now_timestamp_tz >= chief_demoted_score
    assert chief_demoted_score >= now_timestamp_tz - 60 # The chief demotion should have been applied within the last minute
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
        chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(chief.id))
        assert chief_demoted_score is not None
        # The chief location should be removed from Redis when the user is demoted from chief
        chief_location_key = get_redis_chief_locations_key(str(chief.id))
        positions = await redis_session.geopos(chief_location_key, str(chief.id))
        assert all(p is None for p in positions)

## TESTS: POST /api/users/promote-by-emails

def test_promote_users_by_emails_not_authorized_missing_token(client):
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_promote_users_by_emails_not_authorized_invalid_token(client):
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.volunteer.value} 
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers={"Authorization": "Bearer invalidtoken"})
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_promote_users_by_emails_method_not_allowed(client, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get("/api/users/promote-by-emails", headers=headers)
    # GET method is not allowed for this endpoint, only POST is allowed
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

def test_promote_users_by_emails_empty_or_invalid_args(client, test_admin):
    admin: User = test_admin['user']
    assert admin is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We try to call the endpoint with missing or invalid arguments
    data = {
        # no email list
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Missing update_fields
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        # no update_fields
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Email list with a none email
    data = {
        "email_list": {"emails": ["testuser1@example.com", None]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Empty update fields
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Invalid role value in update fields
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {"role": "invalid_role"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Empty email list
    data = {
        "email_list": {"emails": []},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    # Invalid email in email list
    data = {
        "email_list": {"emails": ["testuser1@example.com", "invalidemail"]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1

def test_promote_users_by_emails_forbidden_called_by_baseuser(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    # Base user role is not allowed to promote users, only officer and admin can promote users
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_by_emails_forbidden_called_by_chief(client, test_chief):
    user: User = test_chief['user']
    assert user is not None
    access_token = test_chief['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    # Chief role is not allowed to promote users, only officer and admin can promote users
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_by_emails_too_many_input_emails(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We create a megalist that exceeds the maximum allowed number of emails
    max_size = EMAIL_LIST_MAX_LENGTH_FOR_SEARCH
    email_list = [f"testuser{i}@example.com" for i in range(max_size + 1)]
    data = {
        "email_list": {"emails": email_list},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == invalid_request_exception().status_code
    assert "Email list too long" in response.json()["detail"]

def test_promote_users_by_emails_many_input_emails(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We create a list of emails that is within the maximum allowed number of emails
    max_size = EMAIL_LIST_MAX_LENGTH_FOR_SEARCH
    email_list = [f"testuser{i}@example.com" for i in range(max_size)]
    data = {
        "email_list": {"emails": email_list},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    # We verify that at least one user has been updated, 
    # because some of the emails in the list should exist in the database (see setup fixture
    assert response.json()["updated_count"] > 0

def test_promote_users_by_emails_officer_cannot_modify_the_type(client, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"type": UserType.chief.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_promote_users_by_emails_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We try to promote 2 users that are not authorized by test_officer, so the update should not be applied
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.volunteer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officer role can only update users authorized by them, 
    # In this case the target users are not authorized by test_officer (see setup fixture), 
    # so the update should not be applied
    assert response_data["updated_count"] == 0
    # Now we try to promote 1 user that is authorized by test_officer, so the update should be applied to that user
    # We create a user authorized by test_officer
    user_owned = User(
        email="authorizeduser@example.com",
        password_hash="hashed_password",
        firstname="Authorized",
        surname="User",
        is_active=True,
        role=None,
        authorized_by=user.email,
        authorized_at=now_tz_naive(),
    )
    db_session.add(user_owned)
    db_session.commit()
    testuser1 = db_session.exec(select(User).where(User.email=="testuser1@example.com")).first()
    assert testuser1 is not None
    assert testuser1.authorized_by != user.email
    assert testuser1.updated_by != user.email
    # Now we try to promote both users, one authorized by test_officer and one not authorized by test_officer
    data = {
        "email_list": {"emails": ["authorizeduser@example.com", "testuser1@example.com"]},
        "update_fields": {"role": UserRole.alpinrescuer.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    # We verify that the authorized user has been updated
    db_session.refresh(user_owned)
    assert user_owned.role == UserRole.alpinrescuer.value
    assert user_owned.updated_by == user.email
    assert user_owned.updated_at is not None
    assert user_owned.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Testuser1 should not have been updated, because he is not authorized by test_officer
    assert testuser1.updated_by != user.email
    # Another similar example
    data = {
        "email_list": {"emails": ["authorizeduser@example.com", "testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"status": UserStatus.blocked.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(user_owned)
    assert user_owned.is_blocked == True
    assert user_owned.is_reliable == False # when a user is blocked, it should also be set as not reliable
    assert user_owned.updated_by == user.email
    assert user_owned.updated_at is not None
    assert user_owned.updated_at > now_tz_naive() - timedelta(minutes=1)
    # We check that the update is not applied to users that are not authorized by the officer, even if they are included in the email list
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.is_blocked == False
    assert testuser1.is_reliable == True
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.is_blocked == False
    assert testuser2.is_reliable == True

def test_promote_users_by_emails_called_by_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.alpinrescuer.value, "status": UserStatus.blocked.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Admin role can update any user, so both users should be updated
    assert response_data["updated_count"] == 2
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.role == UserRole.alpinrescuer.value
    assert testuser1.is_blocked == True
    assert testuser1.is_reliable == False
    assert testuser1.authorized_by != user.email
    assert testuser1.updated_by == user.email
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.role == UserRole.alpinrescuer.value
    assert testuser2.is_blocked == True
    assert testuser2.is_reliable == False
    assert testuser2.authorized_by != user.email
    assert testuser2.updated_by == user.email

def test_promote_users_by_emails_modify_role_and_notes(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {"role": UserRole.alpinrescuer.value, "notes": "Updated by admin"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.role == UserRole.alpinrescuer.value
    assert testuser1.notes == "Updated by admin"
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # We try to update 2 users
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"role": UserRole.usar.value, "notes": "Updated by admin for testing purposes"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.role == UserRole.usar.value
    assert testuser1.notes == "Updated by admin for testing purposes"
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.role == UserRole.usar.value
    assert testuser2.notes == "Updated by admin for testing purposes"
    assert testuser2.updated_by == user.email
    assert testuser2.updated_at is not None
    assert testuser2.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute

def test_promote_users_by_emails_modify_status(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We try to block 2 users by email
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"status": UserStatus.blocked.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.is_blocked == True
    assert testuser1.is_reliable == False # when a user is blocked, it should also be set as not reliable
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.is_blocked == True
    assert testuser2.is_reliable == False # when a user is blocked, it should also be set as not reliable
    assert testuser2.updated_by == user.email
    assert testuser2.updated_at is not None
    assert testuser2.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Now we try to change the status of those users to "unreliable"
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"status": UserStatus.unreliable.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    db_session.refresh(testuser1)
    db_session.refresh(testuser2)
    assert testuser1.is_reliable == False
    assert testuser1.is_blocked == False
    assert testuser2.is_reliable == False
    assert testuser2.is_blocked == False

def test_promote_users_by_emails_modify_authorizer_called_by_officer(client, db_session, test_officer):
    user: User = test_officer['user']
    assert user is not None
    access_token = test_officer['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We try to change the authorizer of 2 users, but since those users are not authorized by test_officer, the update should not be applied
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": user.email}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    assert testuser1.authorized_by != "admin1@example.com"
    assert testuser1.updated_by != user.email
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.authorized_by != "admin1@example.com"
    assert testuser2.updated_by != user.email
    # Now we create a user authorized by test_officer, so the update should be applied to that user
    # We create a user authorized by test_officer
    user_owned = User(
        email="testowneduser@example.com",
        password_hash="hashed_password",
        firstname="Test",
        surname="OwnedUser",
        is_active=True,
        role=None,
        authorized_by=user.email,
        authorized_at=now_tz_naive(),
    )
    db_session.add(user_owned)
    db_session.commit()
    # We call the endpoint with a list of 2 emails, one authorized by test_officer and one not authorized by test_officer
    data = {
        "email_list": {"emails": ["testowneduser@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": user.email}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    db_session.refresh(user_owned)
    assert user_owned.authorized_by == user.email
    assert user_owned.updated_by == user.email
    assert user_owned.updated_at is not None
    assert user_owned.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # We check that the update is not applied to the user that is not authorized by the test_officer
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.authorized_by != user.email
    assert testuser2.updated_by != user.email
    # Another example, trying with another authorizer
    # "testowneduser" is authorized by test_officer
    # We want to change the authorizer of "testowneduser" from test_officer@example.com to "admin1@example.com"
    data = {
        "email_list": {"emails": ["testowneduser@example.com"]},
        "update_fields": {"authorizer": "admin1@example.com"}
    }
    # Before the update, the authorizer of "testowneduser" should be testofficer
    db_session.refresh(user_owned)
    assert user_owned.authorized_by == test_officer['user'].email
    # We call the endpoint to change the authorizer to "admin1@example.com"
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 1
    # We verify that the authorizer of "testowneduser" has been changed to "admin1@example.com"
    db_session.refresh(user_owned)
    assert user_owned.authorized_by == "admin1@example.com"
    assert user_owned.updated_by == user.email
    assert user_owned.updated_at is not None
    assert user_owned.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # Now we try to use a non existing authorizer
    # Obviously, the update should not be applied, because the authorizer must be an existing user
    data = {
        "email_list": {"emails": ["testowneduser@example.com"]},
        "update_fields": {"authorizer": "nonexistent@example.com"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(user_owned)
    assert user_owned.authorized_by != "nonexistent@example.com"
    # The authorizer must be an "officer" or an "admin", 
    # so if we use a normal user (or a chief) as new authorizer, the update should not be applied
    data = {
        "email_list": {"emails": ["testowneduser@example.com"]},
        "update_fields": {"authorizer": "chief1@example.com"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(user_owned)
    assert user_owned.authorized_by != "chief1@example.com"

def test_promote_users_by_emails_modify_authorizer_called_by_admin(client, db_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    # We try to change the authorizer of 2 users by email, 
    # and since admin can update any user, the update should be applied to both users
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": "admin1@example.com"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    # We verify that the authorizer of testuser1 and testuser2 has been changed to "admin1@example.com"
    # The calling user (test_admin) should be set as the "updated_by" field for both users
    assert testuser1.authorized_by == "admin1@example.com"
    assert testuser1.updated_by == user.email
    statement = select(User).where(User.email=="testuser2@example.com")
    testuser2 = db_session.exec(statement).first()
    assert testuser2.authorized_by == "admin1@example.com"
    assert testuser2.updated_by == user.email
    # Now we try to change the authorizer to a non existing user, so the update should not be applied
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": "nonexistent@example.com"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(testuser1)
    db_session.refresh(testuser2)
    # The authorizer must be an existing user, so the update should not be applied
    # Testuser1 and testuser2 should still have the previous "authorized_by", which is "admin1@example.com"
    assert testuser1.authorized_by != "nonexistent@example.com"
    assert testuser2.authorized_by != "nonexistent@example.com"
    assert testuser1.authorized_by == "admin1@example.com"
    assert testuser2.authorized_by == "admin1@example.com"
    # The authorizer (see "authorized_by" field) must be an "officer" or an "admin", 
    # so if we use a normal user (or a chief) as new authorizer, the update should not be applied
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": "chief1@example.com"}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 0
    db_session.refresh(testuser1)
    db_session.refresh(testuser2)
    # The authorizer must be an "officer" or an "admin", so the update should not be applied
    # Testuser1 and testuser2 should still have the previous "authorized_by", which is "admin1@example.com"
    assert testuser1.authorized_by != "chief1@example.com"
    assert testuser2.authorized_by != "chief1@example.com"
    assert testuser1.authorized_by == "admin1@example.com"
    assert testuser2.authorized_by == "admin1@example.com"
    # Now we try to change the authorizer, using test_admin email as new authorizer
    data = {
        "email_list": {"emails": ["testuser1@example.com", "testuser2@example.com"]},
        "update_fields": {"authorizer": user.email}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    db_session.refresh(testuser1)
    db_session.refresh(testuser2)
    assert testuser1.authorized_by == user.email
    assert testuser2.authorized_by == user.email
    assert testuser1.updated_by == user.email
    assert testuser2.updated_by == user.email

async def test_promote_users_by_emails_modify_type_called_by_admin(client, db_session, redis_session, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {"type": UserType.chief.value}
    }
    statement = select(User).where(User.email=="testuser1@example.com")
    testuser1 = db_session.exec(statement).first()
    # The users should be normal type before the update
    assert testuser1.is_chief == False
    assert testuser1.is_admin == False
    assert testuser1.is_officer == False
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
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
    chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted_score is None
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
    # Now we try to demote the same user back to normal type, to see what happens with the Redis cache when a chief user is demoted to normal type, 
    # the chief location should be removed from Redis and the user should be added to the chief demoted zset in Redis
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {"type": UserType.base.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
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
    chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted_score is not None
    # we check the timestamp of the chief demotion, it should be recent
    now_timestamp_tz = ensure_tz_aware(now_tz_naive()).timestamp()
    assert now_timestamp_tz >= chief_demoted_score
    assert chief_demoted_score >= now_timestamp_tz - 60 # The chief demotion should have been applied within the last minute
    # The chief location should be removed from Redis when the user is demoted from chief
    positions = await redis_session.geopos(chief_location_key, str(testuser1.id))
    assert all(p is None for p in positions)
    # Now we try to promote the same user back to chief type
    data = {
        "email_list": {"emails": ["testuser1@example.com"]},
        "update_fields": {"type": UserType.chief.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # We verify that testuser1 is a chief again
    db_session.refresh(testuser1)
    assert testuser1.is_chief == True
    assert testuser1.is_officer == False
    assert testuser1.is_admin == False
    assert testuser1.updated_by == user.email
    assert testuser1.updated_at is not None
    assert testuser1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # in Redis cache, the chief users just promoted should be removed from chief demoted zset
    chief_demoted_score = await redis_session.zscore(chief_demotion_key, str(testuser1.id))
    assert chief_demoted_score is None
    # Now we try to demote 2 chiefs to normal type
    statement = select(User).where(User.email == "chief1@example.com")
    chief1 = db_session.exec(statement).first()
    assert chief1 is not None
    assert chief1.is_chief == True
    assert chief1.is_officer == False
    assert chief1.is_admin == False
    statement = select(User).where(User.email == "chief2@example.com")
    chief2 = db_session.exec(statement).first()
    assert chief2 is not None
    assert chief2.is_chief == True
    assert chief2.is_officer == False
    assert chief2.is_admin == False
    # Now we try to add a position in Redis for chief1 and chief2, to check that when they are demoted, 
    # their locations will be removed from Redis and they will be added to the chief demoted zset
    chief1_location_key = get_redis_chief_locations_key(str(chief1.id))
    chief2_location_key = get_redis_chief_locations_key(str(chief2.id))
    longitude = 12.34
    latitude = 56.78
    await redis_session.geoadd(chief1_location_key, (longitude, latitude, str(chief1.id)))
    await redis_session.geoadd(chief2_location_key, (longitude, latitude, str(chief2.id)))
    positions1 = await redis_session.geopos(chief1_location_key, str(chief1.id))
    positions2 = await redis_session.geopos(chief2_location_key, str(chief2.id))
    assert positions1 is not None
    assert positions2 is not None
    assert all(p is not None for p in positions1) # chief1 should have a location in Redis before the update
    assert all(p is not None for p in positions2) # chief2 should have a location in Redis before the update
    # Now call the api, to effectively demote chief1 and chief2 to normal type
    data = {
        "email_list": {"emails": ["chief1@example.com", "chief2@example.com"]},
        "update_fields": {"type": UserType.base.value}
    }
    response = client.post("/api/users/promote-by-emails", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["updated_count"] == 2
    db_session.refresh(chief1)
    db_session.refresh(chief2)
    assert chief1.is_chief == False
    assert chief1.is_officer == False
    assert chief1.is_admin == False
    assert chief2.is_chief == False
    assert chief2.is_officer == False
    assert chief2.is_admin == False
    assert chief1.updated_by == user.email
    assert chief1.updated_at is not None
    assert chief1.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    assert chief2.updated_by == user.email
    assert chief2.updated_at is not None
    assert chief2.updated_at > now_tz_naive() - timedelta(minutes=1) # The update should have been applied recently, so the updated_at should be within the last minute
    # in Redis cache, the chief users just demoted should be added to chief demoted
    chief1_demotion_key = get_redis_chief_demotions_key(str(chief1.id))
    chief2_demotion_key = get_redis_chief_demotions_key(str(chief2.id))
    chief1_demoted_score = await redis_session.zscore(chief1_demotion_key, str(chief1.id))
    chief2_demoted_score = await redis_session.zscore(chief2_demotion_key, str(chief2.id))
    assert chief1_demoted_score is not None
    assert chief2_demoted_score is not None
    # we check the timestamp of the chief demotion, it should be recent
    now_timestamp = int(ensure_tz_aware(now_tz_naive()).timestamp())
    assert abs(chief1_demoted_score - now_timestamp) < 60
    assert abs(chief2_demoted_score - now_timestamp) < 60
    # The chief location should be removed from Redis when the user is demoted from chief
    chief1_position_results = await redis_session.geopos(chief1_location_key, str(chief1.id))
    chief2_position_results = await redis_session.geopos(chief2_location_key, str(chief2.id))
    assert all(p is None for p in chief1_position_results)
    assert all(p is None for p in chief2_position_results)
