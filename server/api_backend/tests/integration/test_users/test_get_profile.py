# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from core.exceptions import token_not_valid_exception
from models.general import User

def test_get_profile_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_profile_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    response = client.get("/api/profile", headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_profile_successful(client, test_baseuser):
    user: User = test_baseuser['user']
    response = client.get("/api/profile", headers={"Authorization": f"Bearer {test_baseuser['access_token']}"})
    assert response.status_code == status.HTTP_200_OK
    data = response.json()
    assert data["id"] == str(user.id)
    assert data["email"] == user.email
    assert data["firstname"] == user.firstname
    assert data["surname"] == user.surname
    assert data["role"] == user.role
    assert data["language"] == user.language
    assert "password" not in data
    assert "password_hash" not in data
    assert "activation_code" not in data
    assert "reset_code_hash" not in data
    assert "login_code_hash" not in data
