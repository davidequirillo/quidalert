# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import WhiteListEntry, UserType, UserRole

def test_create_whitelist_entry_success():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_create_whitelist_entry_invalid_email():
    data = {
        "email": "invalid-email",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_blank_email():
    data = {
        "email": "   ",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_invalid_created_by_email():
    data = {
        "email": "john.doe@example.com",
        "created_by": "invalid-email"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_valid_id():
    data = {
        "id": 123,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.id == data["id"]
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_create_whitelist_entry_invalid_id():
    data = {
        "id": "invalid_id",
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_negative_id():    
    data = {
        "id": -5,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.id == data["id"]
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_create_whitelist_entry_decimal_id():    
    data = {
        "id": 3.14,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_created_at_present():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]
    assert entry.created_at is not None

def test_create_whitelist_entry_missing_email():
    data = {
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_missing_created_by():
    data = {
        "email": "john.doe@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_default_values():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]
    assert entry.created_at is not None
    assert entry.registration_type is None
    assert entry.registration_role is None
    assert entry.user_is_registered is False

def test_create_whitelist_entry_with_registration_type_and_role():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com",
        "registration_type": UserType.chief.value,
        "registration_role": UserRole.firefighter.value
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]
    assert entry.created_at is not None
    assert entry.registration_type == data["registration_type"]
    assert entry.registration_role == data["registration_role"]
    assert entry.user_is_registered is False

def test_create_whitelist_entry_invalid_registration_type():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com",
        "registration_type": "invalid_type"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_create_whitelist_entry_invalid_registration_role():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com",
        "registration_role": "invalid_role"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)
