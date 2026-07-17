# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from core.exceptions import token_not_valid_exception
from models.general import User

def test_update_profile_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    data = {
        "firstname": "NewFirstName",
        "surname": "NewSurname", 
        "street": "New Street",
        "postal_code": "12345",
        "city": "New City",
        "province": "New Province",
        "country": "New Country",
        "birthdate": "1990-01-01",
        "phone": "1234567890"
    }
    response = client.put("/api/profile", headers=headers, json=data)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_profile_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    data = {
        "firstname": "NewFirstName",
        "surname": "NewSurname",
        "street": "New Street",
        "postal_code": "12345",
        "city": "New City",
        "province": "New Province",
        "country": "New Country",
        "birthdate": "1990-01-01",
        "phone": "1234567890"
    }
    response = client.put("/api/profile", headers=headers, json=data)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_update_profile_incomplete_fields(client, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    headers = {"Authorization": f"Bearer {test_baseuser['access_token']}"}
    response = client.put("/api/profile", headers=headers, json={
        "firstname": "NewFirstName",
        # "surname" missing,
        "street": "New Street",
        "postal_code": "12345",
        "city": "New City",
        "province": "New Province",
        "country": "New Country",
        "birthdate": "1990-01-01",
        "phone": "1234567890"
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_update_profile_successful(client, db_session, test_baseuser):
    user: User = test_baseuser['user']
    assert user.id is not None
    headers={"Authorization": f"Bearer {test_baseuser['access_token']}"}
    response = client.put("/api/profile", headers=headers, json={
        "firstname": "NewFirstName",
        "surname": "NewSurname",
        "street": "New Street",
        "postal_code": "12345",
        "city": "New City",
        "province": "New Province",
        "country": "New Country",
        "birthdate": "1990-01-01",
        "phone": "1234567890"
    })
    assert response.status_code == status.HTTP_200_OK
    db_session.refresh(user)
    assert user.firstname == "NewFirstName"
    assert user.surname == "NewSurname"
    assert user.street == "New Street"
    assert user.postal_code == "12345"
    assert user.city == "New City"
    assert user.province == "New Province"
    assert user.country == "New Country"
    assert str(user.birthdate) == "1990-01-01"
    assert user.phone == "1234567890"
    statement = select(User).where(User.id == user.id)
    result = db_session.exec(statement).first()
    assert result is not None
    assert result.firstname == "NewFirstName"
    assert result.surname == "NewSurname"
    assert result.street == "New Street"
    assert result.postal_code == "12345"
    assert result.city == "New City"
    assert result.province == "New Province"
    assert result.country == "New Country"
    assert str(result.birthdate) == "1990-01-01"
    assert result.phone == "1234567890"
