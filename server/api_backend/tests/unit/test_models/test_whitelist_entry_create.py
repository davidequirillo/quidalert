# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import WhiteListEntry

def test_whitelist_entry_create_success():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_whitelist_entry_create_invalid_email():
    data = {
        "email": "invalid-email",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_whitelist_entry_create_blank_email():
    data = {
        "email": "   ",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_whitelist_entry_create_invalid_created_by_email():
    data = {
        "email": "john.doe@example.com",
        "created_by": "invalid-email"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_whitelist_entry_create_valid_id():
    data = {
        "id": 123,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.id == data["id"]
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_whitelist_entry_create_invalid_id():
    data = {
        "id": "invalid_id",
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_whitelist_entry_create_negative_id():    
    data = {
        "id": -5,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.id == data["id"]
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]

def test_whitelist_entry_create_decimal_id():    
    data = {
        "id": 3.14,
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    with pytest.raises(ValueError):
        WhiteListEntry.model_validate(data)

def test_whitelist_entry_created_at_present():
    data = {
        "email": "john.doe@example.com",
        "created_by": "admin@example.com"
    }
    entry = WhiteListEntry.model_validate(data)
    assert entry.email == data["email"]
    assert entry.created_by == data["created_by"]
    assert entry.created_at is not None
