# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta, datetime
from fastapi import status
from core.exceptions import (
    token_expired_exception, 
    token_not_valid_exception
)
from services.security import (
    create_geoposition_token, GEOPOSITION_TOKEN_TTL_MINUTES,
    now_tz_aware, ensure_tz_aware,
    decode_token
)
from core.dbmgr import (
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key,
)

def test_last_known_gps_position_missing_token(client):
    # We don't provide any token in the request headers, so we expect an unauthorized error
    response = client.get('/api/locations/last-known-gps-position')
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_last_known_gps_position_invalid_token(client):
    # We provide an invalid token in the request headers, so we expect an unauthorized error
    headers={
        'Authorization': 'Bearer invalidtoken'
    }
    response = client.get('/api/locations/last-known-gps-position', headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()['detail'] == token_not_valid_exception().detail

def test_last_known_gps_position_expired_token(client, test_baseuser, frozen_now):
    # We create an expired GPS token for testing
    user = test_baseuser['user']
    expired_token = create_geoposition_token(
        user_id=str(user.id),
        user_is_chief=user.is_chief,
        user_role=user.role,
        expires_delta=timedelta(minutes=-1)
    )
    # We provide the expired token in the request headers, so we expect an unauthorized error
    response = client.get('/api/locations/last-known-gps-position', headers={
        'Authorization': f'Bearer {expired_token}'
    })
    assert response.status_code == token_expired_exception().status_code
    assert response.json()['detail'] == token_expired_exception().detail
    default_gps_token = create_geoposition_token(
        user_id=str(user.id),
        user_is_chief=user.is_chief,
        user_role=user.role
    )
    assert default_gps_token != expired_token, "The default GPS token should not be the same as the expired token"
    # Now we try to move the time forward 
    # to make the default GPS token expired as well, and we expect the same error
    frozen_now.tick(delta=timedelta(minutes=GEOPOSITION_TOKEN_TTL_MINUTES + 1))
    response = client.get('/api/locations/last-known-gps-position', headers={
        'Authorization': f'Bearer {default_gps_token}'
    })
    assert response.status_code == token_expired_exception().status_code
    assert response.json()['detail'] == token_expired_exception().detail

async def test_last_known_gps_position_success_as_normal_user(client, redis_session, test_baseuser):
    now = now_tz_aware()
    user = test_baseuser['user']
    assert user.is_chief == False
    gps_token = test_baseuser['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 0, "The GPS token should indicate that the user is not a chief"
    # We simulate a location update for the normal user in Redis before fetching it
    location_key = get_redis_user_locations_key(str(user.id))
    last_upd_key = get_redis_location_last_updates_key(str(user.id))
    await redis_session.geoadd(location_key, (9.0, 45.0, str(user.id)))
    await redis_session.zadd(last_upd_key, {str(user.id): int(now_tz_aware().timestamp())})
    # We now make a request to fetch the last known GPS position for the normal user
    response = client.get('/api/locations/last-known-gps-position', headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "latitude" in response_data, "Response should contain latitude"
    assert "longitude" in response_data, "Response should contain longitude"
    assert "last_update" in response_data, "Response should contain timestamp"
    assert float(response_data["latitude"]) > (45.0 - 0.0001), "Latitude should match the expected value"
    assert float(response_data["latitude"]) < (45.0 + 0.0001), "Latitude should match the expected value"
    assert float(response_data["longitude"]) > (9.0 - 0.0001), "Longitude should match the expected value"
    assert float(response_data["longitude"]) < (9.0 + 0.0001), "Longitude should match the expected value"
    timestamp_dt = ensure_tz_aware(datetime.fromisoformat(response_data["last_update"]))
    assert now >= timestamp_dt - timedelta(seconds=5)
    assert now <= timestamp_dt + timedelta(seconds=5)

async def test_last_known_gps_position_success_as_chief(client, redis_session, test_chief):
    chief = test_chief['user']
    assert chief.is_chief == True
    gps_token = test_chief['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 1, "The GPS token should indicate that the user is a chief"
    # We simulate a location update for the chief in Redis before fetching it
    location_key = get_redis_chief_locations_key(str(chief.id))
    last_upd_key = get_redis_location_last_updates_key(str(chief.id))
    await redis_session.geoadd(location_key, (9.0, 45.0, str(chief.id)))
    await redis_session.zadd(last_upd_key, {str(chief.id): int(now_tz_aware().timestamp())})
    # We now make a request to fetch the last known GPS position for the chief
    response = client.get('/api/locations/last-known-gps-position', headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert "latitude" in response_data, "Response should contain latitude"
    assert "longitude" in response_data, "Response should contain longitude"
    assert "last_update" in response_data, "Response should contain timestamp"
    assert float(response_data["latitude"]) > (45.0 - 0.0001), "Latitude should match the expected value"
    assert float(response_data["latitude"]) < (45.0 + 0.0001), "Latitude should match the expected value"
    assert float(response_data["longitude"]) > (9.0 - 0.0001), "Longitude should match the expected value"
    assert float(response_data["longitude"]) < (9.0 + 0.0001), "Longitude should match the expected value"
    timestamp_dt = ensure_tz_aware(datetime.fromisoformat(response_data["last_update"]))
    assert now_tz_aware() >= timestamp_dt - timedelta(seconds=5)
    assert now_tz_aware() <= timestamp_dt + timedelta(seconds=5)
    
async def test_last_known_gps_position_not_found(client, redis_session, test_baseuser):
    user = test_baseuser['user']
    gps_token = test_baseuser['gps_token']
    location_key = get_redis_user_locations_key(str(user.id))
    last_upd_key = get_redis_location_last_updates_key(str(user.id))
    # Ensure Redis does not have any location for this user
    await redis_session.zrem(last_upd_key, str(user.id))
    await redis_session.zrem(location_key, str(user.id))
    response = client.get('/api/locations/last-known-gps-position', headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data is None, "Response should be None when no GPS position is found"
