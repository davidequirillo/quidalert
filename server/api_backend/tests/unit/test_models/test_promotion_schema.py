# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import (
    PromotionSchema, 
    UserRole, 
    UserStatus, 
    UserType
)

def test_promotion_schema_valid():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value
    }
    promotion_schema = PromotionSchema.model_validate(data)
    assert promotion_schema.type == data["type"]
    assert promotion_schema.role == data["role"]
    assert promotion_schema.status == data["status"]

def test_promotion_schema_invalid_type():
    data = {
        "type": "invalid_type",
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_invalid_role():
    data = {
        "type": UserType.admin.value,
        "role": "invalid_role",
        "status": UserStatus.ok.value
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_valid_role():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value
    }
    promotion_schema = PromotionSchema.model_validate(data)
    assert promotion_schema.role == data["role"]

def test_promotion_schema_role_none():
    data = {
        "type": UserType.admin.value,
        "role": None,
        "status": UserStatus.ok.value
    }
    promotion_schema = PromotionSchema.model_validate(data)
    assert promotion_schema.role is None

def test_promotion_schema_role_empty_string():
    data = {
        "type": UserType.admin.value,
        "role": "",
        "status": UserStatus.ok.value
    }
    # An empty string is not valid
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_role_citizen():
    # Citizen role is not part of UserRole enum, but it is valid as a string
    # Useful to force a user to have no role (base role) in the promotion endpoint
    data = {
        "type": UserType.admin.value,
        "role": "citizen",
        "status": UserStatus.ok.value
    }
    promotion_schema = PromotionSchema.model_validate(data)
    assert promotion_schema.role == "citizen"

def test_promotion_schema_invalid_status():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": "invalid_status"
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_missing_fields():
    data = {
        # Missing type, role and status
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_invalid_authorizer():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value,
        "authorizer": "invalid_email"
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_empty_authorizer():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value,
        "authorizer": ""
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_empty_whitespace_authorizer():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value,
        "authorizer": "   "
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)

def test_promotion_schema_with_notes_too_long():
    data = {
        "type": UserType.admin.value,
        "role": UserRole.volunteer.value,
        "status": UserStatus.ok.value,
        "notes": "a" * 257 # Max is 256 characters
    }
    with pytest.raises(ValueError):
        PromotionSchema.model_validate(data)
