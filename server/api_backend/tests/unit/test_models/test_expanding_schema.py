# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import ExpandingSchema, UserRole

def test_expanding_schema_success():
    data = {
        "radius": 30.0,
        "role": UserRole.volunteer.value
    }
    schema = ExpandingSchema.model_validate(data)
    assert schema.radius == data["radius"]
    assert schema.role == data["role"]
    data = {
        "radius": 1000.0,
        "role": UserRole.volunteer.value
    }
    schema = ExpandingSchema.model_validate(data)
    assert schema.radius == data["radius"]
    assert schema.role == data["role"]

def test_expanding_schema_none_role():
    data = {
        "radius": 30.0,
    }
    schema = ExpandingSchema.model_validate(data)
    assert schema.radius == data["radius"]
    assert schema.role is None  # The role should be None if not provided
    data = {
            "radius": 30.0,
            "role": None
        }
    schema = ExpandingSchema.model_validate(data)
    assert schema.radius == data["radius"]
    assert schema.role is None

def test_expanding_schema_empty_role():
    data = {
        "radius": 30.0,
        "role": ""
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)

def test_expanding_schema_invalid_role():
    data = {
        "radius": 30.0,
        "role": "invalid_role"
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)

def test_expanding_schema_invalid_radius():
    data = {
        "radius": -7,  # negative radius
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)
    data = {
        "radius": 0,  # zero radius
        "role": UserRole.volunteer.value
    }
    data = {
        "radius": 1001.0,  # too large
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)
    data = {
        "radius": None,  # None radius
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)
    data = {
        "radius": "invalid_radius",  # invalid type
        "role": UserRole.volunteer.value
    }
    with pytest.raises(ValueError):
        ExpandingSchema.model_validate(data)
