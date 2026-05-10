# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import AlertIn

def test_create_alert_success():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    alert = AlertIn.model_validate(data)
    assert alert.description == data["description"]
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.address == data["address"]

def test_create_alert_description_too_long():
    data = {
        "description": "A" * 512,
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_blank_description():
    data = {
        "description": "   ",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    alert = AlertIn.model_validate(data)
    assert alert.description is not None
    assert alert.description.strip() == ""

def test_create_alert_description_not_present():
    data = {
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    alert = AlertIn.model_validate(data)
    assert alert.description is not None
    assert alert.description == ""

def test_create_alert_invalid_latitude():
    data = {
        "description": "This is a test alert",
        "latitude": 100.0, # invalid latitude
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_invalid_longitude():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 200.0, # invalid longitude
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_longitude_not_present():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
        assert True

def test_create_alert_latitude_not_present():
    data = {
        "description": "This is a test alert",
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_coordinates_not_present():
    data = {
        "description": "This is a test alert",
        "address": "Alert Street, 85"
    }
    # It's ok, we can create general alerts without coordinates, so we expect the model to be created successfully and the coordinates to be None
    # The description is present
    alert = AlertIn.model_validate(data)
    assert alert.latitude is None
    assert alert.longitude is None

def test_create_alert_coordinates_not_present_and_description_blank():
    data = {
        "description": "   ",
        "address": "Alert Street, 85"
    }
    # We expect a validation error because either description or coordinates must be provided
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_coordinates_not_present_and_description_not_present():
    data = {
        "address": "Alert Street, 85"
    }
    # We expect a validation error because either description or coordinates must be provided
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_with_only_coordinates():
    data = {
        "latitude": 45.123456,
        "longitude": 120.17
    }
    # It's ok, we can create alerts with only coordinates, 
    # so we expect the model to be created successfully and the description to be empty (default value="")
    alert = AlertIn.model_validate(data)
    assert alert.description is not None
    assert alert.description == ""

def test_create_alert_with_only_coordinates_and_description_None():
    # In this case the description is explicitly set to None
    data = {
        "description": None,
        "latitude": 45.123456,
        "longitude": 120.17
    }
    # We expect an exception because the description is None (it should be a string)
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
