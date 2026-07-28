# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import (
    EmailListWithPrivileges, 
    UserRole, 
    UserType
)

def test_emails_with_priv_schema_valid():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
        "type": UserType.officer.value,
        "role": UserRole.volunteer.value
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert emails_with_priv.type == data["type"]
    assert emails_with_priv.role == data["role"]

def test_emails_with_priv_schema_invalid_type():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
        "type": "invalid_type",
        "role": UserRole.volunteer.value,
    }
    with pytest.raises(ValueError):
        EmailListWithPrivileges.model_validate(data)

def test_emails_with_priv_schema_invalid_role():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
        "type": UserType.admin.value,
        "role": "invalid_role"
    }
    with pytest.raises(ValueError):
        EmailListWithPrivileges.model_validate(data)

def test_emails_with_priv_schema_defaults():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert emails_with_priv.role is None
    assert emails_with_priv.type is None

def test_emails_with_priv_schema_none_email_list():
    data = {
        "emails": None,
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        EmailListWithPrivileges.model_validate(data)

def test_emails_with_priv_schema_empty_email_list():
    data = {
        "emails": [],
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert len(emails_with_priv.emails) == 0

def test_emails_with_priv_schema_blank_email():
    data = {
        "emails": ["", ""],
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert len(emails_with_priv.emails) == 2
    for email in emails_with_priv.emails:
        assert email == ""

def test_emails_with_priv_schema_none_email():
    data = {
        "emails": [None, "user2@example.com"],
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        EmailListWithPrivileges.model_validate(data)

def test_emails_with_priv_schema_type_none():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
        "type": None,
        "role": UserRole.volunteer.value
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert emails_with_priv.type is None
    assert emails_with_priv.role == data["role"]

def test_emails_with_priv_schema_role_none():
    data = {
        "emails": ["user1@example.com", "user2@example.com"],
        "type": UserType.admin.value,
        "role": None
    }
    emails_with_priv = EmailListWithPrivileges.model_validate(data)
    assert emails_with_priv.role is None
    assert emails_with_priv.type == data["type"]
