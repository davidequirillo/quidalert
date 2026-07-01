# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import AlertIn, AlertOut, AlertType

def test_create_alert_empty_data():
    # It fails because a non empty description is required
    data = {}
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_with_empty_description():
    # Description must be a non empty string
    data = {
        "description": None,
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    
    data = {
        "description": "",
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    # Another example with only spaces
    data = {
        "description": "   ",
    }     
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    data = {
        "description": "   ",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    data = {
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_with_only_description():
    # It's ok, we can create alerts with only a description, 
    # so we expect the model to be created successfully and the other fields to have their default values
    data = {
        "description": "This is a test alert",
    }
    alert = AlertIn.model_validate(data)
    assert alert.description == data["description"]
    assert alert.type == AlertType.local.value
    assert alert.latitude == 0.0
    assert alert.longitude == 0.0
    assert alert.address is None
    assert alert.radius == 1.0

def test_create_alert_description_too_long():
    data = {
        "description": "A" * 513,
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

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
    # Default longitude is 0.0
    alert = AlertIn.model_validate(data)
    assert alert.longitude == 0.0

def test_create_alert_latitude_not_present():
    data = {
        "description": "This is a test alert",
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    # Default latitude is 0.0
    alert = AlertIn.model_validate(data)
    assert alert.latitude == 0.0

def test_create_alert_coordinates_not_present():
    data = {
        "description": "This is a test alert",
        "address": "Alert Street, 85"
    }
    # It's ok, we can create alerts without coordinates, so we expect the model to be created successfully and the latitude and longitude to be 0.0 (default values)
    alert = AlertIn.model_validate(data)
    assert alert.latitude == 0.0
    assert alert.longitude == 0.0

def test_create_alert_with_wrong_radius():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
        "radius": -5 # invalid radius
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    # Another example
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
        "radius": 0.0 # must be greater than zero
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
    # Another example
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
        "radius": 1000.00 # it's too large
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_with_wrong_type():
    data = {
        "type": "Wrong type",
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_with_correct_type():
    data = {
        "type": AlertType.local.value,
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
    }
    alert = AlertIn.model_validate(data)
    assert alert.type == AlertType.local.value
    # Another example
    data = {
        "type": AlertType.general.value,
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85",
    }

def test_create_alert_with_address_too_long():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "A" * 257 # address too long
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_create_alert_out_with_defaults():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
    }
    alert = AlertOut.model_validate(data)
    assert alert.description == data["description"]
    assert alert.latitude == data["latitude"]
    assert alert.longitude == data["longitude"]
    assert alert.address is None
    assert alert.radius == 1.0
    assert alert.type == AlertType.local.value
    assert alert.spread_count == 0
    assert alert.is_closed == False
    assert alert.is_pending == True

def test_create_alert_out_with_wrong_spread_count():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "spread_count": -1 # invalid spread count
    }
    with pytest.raises(ValueError):
        AlertOut.model_validate(data)
    # Another example
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 120.17,
        "spread_count": 10 # it's too large
    }
    with pytest.raises(ValueError):
        AlertOut.model_validate(data)
