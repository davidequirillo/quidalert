# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from sqlmodel import select
from models.general import User, WhiteListEntry
from core.settings import settings

def test_register_missing_fields(client):
    payload = {"firstname": "John", "surname": "Doe"}
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == "email" for err in errors)
    assert any(err["loc"][-1] == "password" for err in errors)

def test_register_invalid_email_format(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "name-at-domain.com", # invalid email format
        "password": "Password123!"
    }  
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    assert "email" in str(response.json()["detail"]).lower()

def test_register_password_too_short(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "user@test.it",
        "password": "123" # too short password
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422 or response.status_code == 400

def test_register_password_too_simple(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "user@test.it",
        "password": "Password123" # too simple password, without special characters
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422 or response.status_code == 400

def test_register_duplicate_silent(client, db_session):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "admin@example.com",
        "password": settings.admin_pass
    }   
    # 1. First registration (should succeed)
    client.post("/api/register", json=payload)   
    # 2. Second registration (same email)
    response = client.post("/api/register", json=payload)
    # Check that for the client everything appears "normal"
    assert response.status_code in [200, 201, 202]
    # 3. Check the database to ensure that no duplicate user was created
    statement = select(User).where(User.email == "admin@example.com")
    results = db_session.exec(statement).all()
    assert len(results) == 1

def test_register_not_in_whitelist_silent(client, db_session):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "admin@example.com",
        "password": settings.admin_pass
    }   
    # 1. First registration (should succeed)
    client.post("/api/register", json=payload)   
    # 2. Second registration (another email, not in the whitelist)
    payload["email"] = "not_in_whitelist@example.com"
    response = client.post("/api/register", json=payload)
    # Check that for the client everything appears "normal"
    assert response.status_code in [200, 201, 202]
    # 3. Check the database to ensure that no user was created with the email not in the whitelist
    statement = select(User).where(User.email == "not_in_whitelist@example.com")
    results = db_session.exec(statement).all()
    assert len(results) == 0

@pytest.fixture(name="whitelist_entry")
def existing_whitelist_entry(db_session):
    entry = WhiteListEntry(email="whitelisted@example.com", created_by="admin@example.com")
    db_session.add(entry)
    db_session.commit()
    return entry
    
def test_register_in_whitelist(client, db_session, whitelist_entry):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "admin@example.com",
        "password": settings.admin_pass
    }   
    # 1. First registration (should succeed)
    client.post("/api/register", json=payload)   
    # 2. Second registration (another email, valid, in the whitelist)
    payload["email"] = whitelist_entry.email
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # 3. Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
