# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import UserInCompleteProfile

def test_create_user_success():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "birthdate": "2000-01-01",
        "phone": "+39 1234567890"
    }
    user = UserInCompleteProfile.model_validate(data)
    assert user.firstname == data["firstname"]
    assert user.street == data["street"]

def test_create_user_invalid_birthdate():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "birthdate": "01-01-2001",
        "phone": "1234567890"
    }
    with pytest.raises(ValueError):
        UserInCompleteProfile.model_validate(data)

def test_create_user_blank_or_none_birthdate():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "phone": "1234567890"
    }
    with pytest.raises(ValueError):
        UserInCompleteProfile.model_validate(data)
    data["birthdate"] = ""
    with pytest.raises(ValueError):        
        UserInCompleteProfile.model_validate(data)
        assert True

def test_create_user_blank_or_none_phone():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "birthdate": "2000-01-01"
    }
    with pytest.raises(ValueError):
        UserInCompleteProfile.model_validate(data)
    data["phone"] = ""
    with pytest.raises(ValueError):        
        UserInCompleteProfile.model_validate(data)

def test_create_user_invalid_phone():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "birthdate": "2000-01-01",
        "phone": "invalid-phone"
    }
    with pytest.raises(ValueError):
        UserInCompleteProfile.model_validate(data)

def test_create_user_phone_too_short():
    data = {
        "firstname": "John",
        "surname": "Doe",
        "street": "123 Main St",
        "postal_code": "12345",
        "city": "Sample City",
        "province": "Sample Province",
        "country": "Sample Country",
        "birthdate": "2000-01-01",
        "phone": "+123"
    }
    with pytest.raises(ValueError):
        UserInCompleteProfile.model_validate(data)
