# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import GpsCoordinatesSchema

def test_gps_coordinates_schema_success():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19
    }
    request = GpsCoordinatesSchema.model_validate(data)
    assert request.latitude == data["latitude"]
    assert request.longitude == data["longitude"]

def test_gps_coordinates_schema_empty_coordinates():
    data = {
        "latitude": None,
        "longitude": 9.19
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)
    data = {
        "latitude": 70.4642,
        "longitude": None
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_coordinates():
    data = {
        "latitude": 100.0, # invalid latitude, should be between -90 and 90
        "longitude": 9.19
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)
    data = {
        "latitude": 45.4642,
        "longitude": 200.0 # invalid longitude, should be between -180 and 180
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_boundary_coordinates():
    data = {
        "latitude": -90.0, # Boundary latitude, should be valid
        "longitude": -180.0 # Boundary longitude, should be valid
    }
    request = GpsCoordinatesSchema.model_validate(data)
    assert request.latitude == data["latitude"]
    assert request.longitude == data["longitude"]
    data = {
        "latitude": 90.0, # Boundary latitude, should be valid
        "longitude": 180.0 # Boundary longitude, should be valid
    }
    request = GpsCoordinatesSchema.model_validate(data)
    assert request.latitude == data["latitude"]
    assert request.longitude == data["longitude"]

def test_gps_coordinates_schema_default_values():
    data = {
            "latitude": 45.4642,
            "longitude": 9.19
        }
    request = GpsCoordinatesSchema.model_validate(data)
    assert request.latitude == data["latitude"]
    assert request.longitude == data["longitude"]
    assert request.accuracy is None
    assert request.location_id is None
    assert request.is_moving is None
    assert request.speed is None

def test_gps_coordinates_schema_all_fields():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "accuracy": 5.0,
        "location_id": "loc123",
        "is_moving": True,
        "speed": 10.5
    }
    request = GpsCoordinatesSchema.model_validate(data)
    assert request.latitude == data["latitude"]
    assert request.longitude == data["longitude"]
    assert request.accuracy == data["accuracy"]
    assert request.location_id == data["location_id"]
    assert request.is_moving == data["is_moving"]
    assert request.speed == data["speed"]

def test_gps_coordinates_schema_invalid_accuracy():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "accuracy": "blah blah" # it should be a float
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_speed():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "speed": "fast" # it should be a float
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_location_id():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "location_id": 123 # it should be a string
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_is_moving():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "is_moving": "invalid" # it should be a boolean
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_latitude():
    data = {
        "latitude": "north", # it should be a float
        "longitude": 9.19
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_invalid_longitude():
    data = {
        "latitude": 45.4642,
        "longitude": "east" # it should be a float
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_missing_latitude():
    data = {
        "longitude": 9.19
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_missing_longitude():
    data = {
        "latitude": 45.4642
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)

def test_gps_coordinates_schema_location_id_too_long():
    data = {
        "latitude": 45.4642,
        "longitude": 9.19,
        "location_id": "a" * 257 # assuming the max length is 256
    }
    with pytest.raises(ValueError):
        GpsCoordinatesSchema.model_validate(data)
