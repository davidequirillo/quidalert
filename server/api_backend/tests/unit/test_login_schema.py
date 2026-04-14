# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import LoginSchema

def test_login_schema_create_success():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid"
    }
    request = LoginSchema.model_validate(data)
    assert request.email == data["email"]
    assert request.password == data["password"]

def test_login_schema_empty_credentials():
    data = {
        "email": "",
        "password": ""
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_missing_credentials():
    data = {
        "email": None,
        "password": None
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_invalid_or_blank_email():
    data = {
        "email": "invalid-email",
        "password": "PasswordSimpleButValid"
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)
    data = {
        "email": None,
        "password": "PasswordSimpleButValid"
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)
    data = {
        "email": "",
        "password": "PasswordSimpleButValid"
    }    
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_missing_password():
    data = {
        "email": "testuser@example.com",
        "password": None
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_password_empty():
    data = {
        "email": "testuser@example.com",
        "password": ""
    }
    # Password can be an empty string
    LoginSchema.model_validate(data)
    assert data["password"] == ""

def test_login_schema_create_login_code_invalid_length():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "login_code": "12345"  # Invalid length (should be 6)
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)
    data["login_code"] = "1234567"  # Invalid length (should be 6)
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_login_code_not_valid():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "login_code": "abcdef"  # Not a valid 6-digit number
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_login_code_valid():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "login_code": "123456"  # Valid 6-digit number
    }
    request = LoginSchema.model_validate(data)
    assert request.login_code == data["login_code"]

def test_login_schema_create_login_token_invalid_length():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "login_token": "tokenstr" * 100  # Invalid length (should be 0-256)
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)
    
def test_login_schema_create_login_token_valid():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "login_token": "tokenstr" * 10  # Valid length (should be 0-256)
    }
    request = LoginSchema.model_validate(data)
    assert request.login_token == data["login_token"]

def test_login_schema_create_device_model_invalid_length():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "device_model": "d" * 257  # Invalid length (should be 0-256)
    }
    with pytest.raises(ValueError):
        LoginSchema.model_validate(data)

def test_login_schema_create_device_model_valid():
    data = {
        "email": "testuser@example.com",
        "password": "PasswordSimpleButValid",
        "device_model": "d" * 256  # Valid length (should be 0-256)
    }
    request = LoginSchema.model_validate(data)
    assert request.device_model == data["device_model"]
