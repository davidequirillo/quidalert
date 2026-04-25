# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from datetime import timedelta
from sqlmodel import select
from models.general import User, UserLanguage
from services.security import now_tz_naive

def test_activate_user_not_found(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We try to activate the user with an invalid email
    wrong_email = "invalid_email@example.com"
    assert user.email != wrong_email
    activation_payload = {"email": wrong_email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    # We return a generic success response to avoid leaking information about which emails are registered in the system
    assert response.status_code == status.HTTP_200_OK
    assert "not valid" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_input_not_valid(client):
    # We try to activate the user with missing fields
    payload = {"email": ""}
    response = client.get("/api/activate", params=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    payload = {"token": ""}
    response = client.get("/api/activate", params=payload)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_activate_code_empty(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We try to activate the user with an empty activation token
    activation_payload = {"email": user.email, "token": ""}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "not valid" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_wrong_code(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We try to activate the user with a wrong activation token
    wrong_token = "wrong_token"
    assert user.activation_code != wrong_token
    activation_payload = {"email": user.email, "token": wrong_token}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "not valid" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_successful(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We activate the user with the correct activation token
    activation_payload = {"email": user.email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "Activation done" in response.content.decode()
    # We check that the user is now active
    db_session.refresh(user)
    assert user.is_active == True

def test_activate_already_active(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We activate the user with the correct activation token
    activation_payload = {"email": user.email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "Activation done" in response.content.decode()
    # We check that the user is now active
    db_session.refresh(user)
    assert user.is_active == True
    # We try to activate the already active user again
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "already active" in response.content.decode()

def test_activate_code_missing_in_db(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    # We manually set the activation token to None to simulate a missing token in the database
    user.activation_code = None
    db_session.add(user)
    db_session.commit()
    # We try to activate the user with any token (even if it's correct, it won't be found in the database)
    activation_payload = {"email": user.email, "token": "any_token"}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "not valid" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_code_expired(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    assert user.activation_code is not None
    # We manually set the activation expiration time to a past time to simulate an expired token
    user.activation_expires_at = now_tz_naive() - timedelta(hours=1) # Set the expiration time to 1 hour in the past
    db_session.add(user)
    db_session.commit()
    # We try to activate the user with the expired token
    activation_payload = {"email": user.email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "Activation expired" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_code_expiration_not_set(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    assert user.activation_code is not None
    # We manually set the activation expiration time to None to simulate a token with no expiration set
    user.activation_expires_at = None
    db_session.add(user)
    db_session.commit()
    # We try to activate the user with the token that has no expiration set
    activation_payload = {"email": user.email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "Activation expired" in response.content.decode()
    # We check that the user is still not active
    db_session.refresh(user)
    assert user.is_active == False

def test_activate_code_not_expired_and_valid(client, db_session, superuser_in_db, whitelist_entry):
    assert superuser_in_db.id is not None
    # We register the user
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email, 
        "password": "testpass!ABC123",
        "language": UserLanguage.en.value
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == status.HTTP_200_OK
    statement = select(User).where(User.email == whitelist_entry.email)
    user: User = db_session.exec(statement).first()
    assert user is not None
    assert user.activation_code is not None
    # We manually set the activation expiration time to a future time to simulate a valid token
    user.activation_expires_at = now_tz_naive() + timedelta(hours=1) # Set the expiration time to 1 hour in the future
    db_session.add(user)
    db_session.commit()
    # We try to activate the user with the valid token
    activation_payload = {"email": user.email, "token": user.activation_code}
    response = client.get("/api/activate", params=activation_payload)
    assert response.status_code == status.HTTP_200_OK
    assert "Activation done" in response.content.decode()
    # We check that the user is now active
    db_session.refresh(user)
    assert user.is_active == True
