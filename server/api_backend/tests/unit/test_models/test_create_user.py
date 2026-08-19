# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import UserIn, User, UserLanguage, UserRole

## Test UserIn model

def test_create_user_success():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    user = UserIn.model_validate(data)
    assert user.firstname == data["firstname"]
    assert user.email == data["email"]
    assert user.language == UserLanguage.en # default language

def test_create_user_firstname_blank():
    data = {
        "firstname": "",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_surname_blank():
    data = {
        "firstname": "John",
        "surname": "",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_firstname_too_short():
    data = {
        "firstname": "J",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_surname_too_short():
    data = {
        "firstname": "John",
        "surname": "D",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_firstname_too_long():
    data = {
        "firstname": "J" * 256,
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_surname_too_long():
    data = {
        "firstname": "John",
        "surname": "D" * 256,
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_invalid_email():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "invalid-email",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_email_with_external_whitespace():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": " john.doe@example.com ",
        "password": "MyValidPassword123!"
    }
    user = UserIn.model_validate(data)
    assert user.email == data["email"].strip().lower()

def test_create_user_email_with_internal_whitespace():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "jo hn.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_email_with_uppercase():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "JOHN.DOE@EXAMPLE.COM",
        "password": "MyValidPassword123!"
    }
    user = UserIn.model_validate(data)
    assert user.email.lower() == data["email"].lower() # the email should always be normalized to lowercase

def test_create_user_blank_password():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": ""
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_short_password():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "short"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_password_too_simple():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "tooSimple123456"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_wrong_language_attribute():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!",
        "language": "wrong_language_code"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_valid_language_attribute():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!",
        "language": "it"
    }
    user = UserIn.model_validate(data)
    assert user.language == data["language"]

## Test User model

def test_create_user_check_default_timestamp_fields():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password_hash": "hashed_password"
    }
    user = User.model_validate(data)
    assert user.created_at is not None
    assert user.last_reset_done_at is not None
    assert user.pending_delete_since is None

def test_create_user_check_default_boolean_fields():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password_hash": "hashed_password"
    }
    user = User.model_validate(data)
    assert user.is_active is False # The default value for is_active should be False
    assert user.is_superuser is False
    assert user.is_admin is False
    assert user.is_officer is False
    assert user.is_chief is False
    assert user.role is None # The default value for role should be None
    assert user.is_reliable is True
    assert user.is_blocked is False

def test_create_user_with_custom_role():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password_hash": "hashed_password",
        "role": UserRole.military.value
    }
    user = User.model_validate(data)
    assert user.firstname == data["firstname"]
    assert user.surname == data["surname"]
    assert user.email == data["email"]
    assert user.role == UserRole.military.value

def test_create_user_with_invalid_role():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password_hash": "hashed_password",
        "role": "invalid_role"
    }
    with pytest.raises(ValueError):
        User.model_validate(data)
        assert True
