# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import UserIn, User, UserLanguage

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

def test_create_user_firstname_or_surname_blank():
    data = {
        "firstname": "",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["firstname"] = "John"
    data["surname"] = ""
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["firstname"] = "John"
    data["surname"] = ""
    with pytest.raises(ValueError):
        UserIn.model_validate(data)

def test_create_user_firstname_or_surname_too_short():
    data = {
        "firstname": "J",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["firstname"] = "John"
    data["surname"] = "D"
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
        assert True

def test_create_user_firstname_or_surname_too_long():
    data = {
        "firstname": "J" * 256,
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["firstname"] = "John"
    data["surname"] = "D" * 256
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
        assert True

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

def test_create_user_blank_or_invalid_password():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": ""
    }
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["password"] = "short"
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
    data["password"] = "simplePassword123"
    with pytest.raises(ValueError):
        UserIn.model_validate(data)
        assert True

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

# Test User model
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
