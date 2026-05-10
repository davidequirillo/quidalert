# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from fastapi import status
from sqlmodel import delete, select
from core.exceptions import token_not_valid_exception, forbidden_exception, not_found_exception
from models.general import Alert, User, UserLanguage, UserRole

@pytest.fixture(autouse=True)
def setup_and_teardown(db_session):
    # Setup: create 3 users in the database
    user1 = User(
        email="testuser1@example.com", 
        password_hash="hashed_password", 
        firstname="Test1", surname="User1", 
        is_active=True, 
        role=UserRole.citizen.value, 
        language=UserLanguage.en.value
    )
    db_session.add(user1)
    user2 = User(
        email="testuser2@example.com", 
        password_hash="hashed_password", 
        firstname="Test2", surname="User2", 
        is_active=True, 
        role=UserRole.citizen.value, 
        language=UserLanguage.en.value
    )
    db_session.add(user2)
    user3 = User(
        email="testuser3@example.com", 
        password_hash="hashed_password", 
        firstname="Test3", surname="User3", 
        is_active=True, 
        role=UserRole.citizen.value, 
        language=UserLanguage.en.value
    )
    db_session.add(user3)
    db_session.commit()
    # Insert some alerts for user1
    alert1 = Alert(user_id=user1.id, description="Test alert 1", latitude=0.0, longitude=0.0)
    alert2 = Alert(user_id=user1.id, description="Test alert 2", latitude=0.0, longitude=0.0)
    db_session.add(alert1)
    db_session.add(alert2)
    db_session.commit()
    yield
    # Clean up the database after each test
    db_session.exec(delete(Alert))
    db_session.exec(delete(User))
    db_session.commit()

def test_get_user_token_missing(client, db_session):
    statement = select(User).where(User.email == "testuser1@example.com")
    testuser = db_session.exec(statement).first()
    response = client.get(f"/api/user/{testuser.id}")
    assert response.status_code == 401

def test_get_user_invalid_token(client, db_session):
    statement = select(User).where(User.email == "testuser1@example.com")
    testuser = db_session.exec(statement).first()
    headers = {"Authorization": "Bearer invalidtoken"}
    response = client.get(f"/api/user/{testuser.id}", headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()['detail'] == token_not_valid_exception().detail

def test_get_user_forbidden(client, db_session, test_baseuser):
    statement = select(User).where(User.email == "testuser1@example.com")
    testuser = db_session.exec(statement).first()
    user: User = test_baseuser['user']
    assert user is not None
    access_token = test_baseuser['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"/api/user/{testuser.id}", headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()['detail'] == forbidden_exception().detail

def test_get_user_success(client, db_session, test_admin):
    statement = select(User).where(User.email == "testuser1@example.com")
    testuser = db_session.exec(statement).first()
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    response = client.get(f"/api/user/{testuser.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    response_user = response_data["user"]
    response_alerts = response_data["alerts"]
    assert response_user["id"] == str(testuser.id)
    assert response_user["email"] == testuser.email
    assert response_user["firstname"] == testuser.firstname
    assert response_user["surname"] == testuser.surname
    assert response_user["is_active"] == testuser.is_active
    assert response_user["role"] == testuser.role
    assert response_user["language"] == testuser.language
    assert "password_hash" not in response_user
    assert "password" not in response_user
    assert isinstance(response_alerts, list)
    assert len(response_alerts) == 2
    assert response_alerts[0]["description"] in ["Test alert 1", "Test alert 2"]
    assert response_alerts[1]["description"] in ["Test alert 1", "Test alert 2"]
    assert response_alerts[0]["user_id"] == str(testuser.id)
    assert response_alerts[1]["user_id"] == str(testuser.id)
    # If the user hasn't created any alert... (testuser2 has no alerts)
    statement = select(User).where(User.email == "testuser2@example.com")
    testuser = db_session.exec(statement).first()
    response = client.get(f"/api/user/{testuser.id}", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    response_user = response_data["user"]
    response_alerts = response_data["alerts"]
    assert response_user["id"] == str(testuser.id)
    assert response_user["email"] == testuser.email
    assert response_user["firstname"] == testuser.firstname
    assert response_user["surname"] == testuser.surname
    assert response_user["is_active"] == testuser.is_active
    assert response_user["role"] == testuser.role
    assert response_user["language"] == testuser.language
    assert "password_hash" not in response_user
    assert "password" not in response_user
    assert isinstance(response_alerts, list)
    assert len(response_alerts) == 0

def test_get_user_not_found(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    non_existent_user_id = "00000000-0000-0000-0000-000000000000"
    response = client.get(f"/api/user/{non_existent_user_id}", headers=headers)
    assert response.status_code == not_found_exception(detail="User not found").status_code
    assert response.json()['detail'] == not_found_exception(detail="User not found").detail

def test_get_user_invalid_user_id(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    invalid_user_id = "invalid-uuid"
    response = client.get(f"/api/user/{invalid_user_id}", headers=headers)
    assert response.status_code == not_found_exception(detail="User id not valid").status_code
    assert response.json()['detail'] == not_found_exception(detail="User id not valid").detail

def test_get_user_blank_user_id(client, test_admin):
    user: User = test_admin['user']
    assert user is not None
    access_token = test_admin['access_token']
    headers = {"Authorization": f"Bearer {access_token}"}
    blank_user_id = ""
    response = client.get(f"/api/user/{blank_user_id}", headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND
