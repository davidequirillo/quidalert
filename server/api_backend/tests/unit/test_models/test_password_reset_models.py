# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import PasswordResetRequest, PasswordResetConfirm

def test_password_reset_request_create_success():
    data = {
        "email": "testuser@example.com"
    }
    request = PasswordResetRequest.model_validate(data)
    assert request.email == data["email"]

def test_password_reset_request_create_invalid_or_blank_email():
    data = {
        "email": "invalid-email"
    }
    with pytest.raises(ValueError):
        PasswordResetRequest.model_validate(data)
    data = {
        "email": None
    }
    with pytest.raises(ValueError):
        PasswordResetRequest.model_validate(data)
    
def test_password_reset_confirm_create_success():
    data = {
        "email": "testuser@example.com",
        "code": "0123456789",
        "new_password": "Password!12345"
    }
    confirm = PasswordResetConfirm.model_validate(data)
    assert confirm.email == data["email"]
    assert confirm.code == data["code"]
    assert confirm.new_password == data["new_password"]

def test_password_reset_confirm_create_invalid_code():
    data = {
        "email": "testuser@example.com",
        "code": "invalid-code",
        "new_password": "Password!12345"
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)
    data = {
        "email": "testuser@example.com",
        "code": "abcdefghij", # valid length but not numeric
        "new_password": "Password!12345"
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)

def test_password_reset_confirm_create_code_too_short():
    data = {
        "email": "testuser@example.com",
        "code": "123456789", # 9 characters instead of 10
        "new_password": "Password!12345"
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)

def test_password_reset_confirm_create_code_too_long():
    data = {
        "email": "testuser@example.com",
        "code": "12345678901", # 11 characters instead of 10
        "new_password": "Password!12345"
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)

def test_password_reset_confirm_create_invalid_password():
    data = {
        "email": "testuser@example.com",
        "code": "0123456789",
        "new_password": "password_too_simple"
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)

def test_password_reset_confirm_create_blank_password():
    data = {
        "email": "testuser@example.com",
        "code": "0123456789",
        "new_password": ""
    }
    with pytest.raises(ValueError):
        PasswordResetConfirm.model_validate(data)
