# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import AlertIn

def test_alert_create_success():
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

def test_alert_create_description_too_long():
    data = {
        "description": "A" * 512,
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_alert_create_blank_description():
    data = {
        "description": "   ",
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    alert = AlertIn.model_validate(data)
    assert alert.description.strip() == ""

def test_alert_create_description_not_present():
    data = {
        "latitude": 45.123456,
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    alert = AlertIn.model_validate(data)
    assert alert.description == ""

def test_alert_create_invalid_latitude():
    data = {
        "description": "This is a test alert",
        "latitude": 100.0, # invalid latitude
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_alert_create_invalid_longitude():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "longitude": 200.0, # invalid longitude
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)

def test_alert_create_longitude_not_present():
    data = {
        "description": "This is a test alert",
        "latitude": 45.123456,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
        assert True

def test_alert_create_latitude_not_present():
    data = {
        "description": "This is a test alert",
        "longitude": 120.17,
        "address": "Alert Street, 85"
    }
    with pytest.raises(ValueError):
        AlertIn.model_validate(data)
