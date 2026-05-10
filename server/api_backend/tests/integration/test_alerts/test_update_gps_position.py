# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fastapi import status
from models.general import GpsCoordinatesSchema, GpsTokenData
from core.exceptions import token_expired_exception, token_not_valid_exception
from services.security import (
    create_geoposition_token, GEOPOSITION_TOKEN_TTL_MINUTES,
    now_tz_naive, ensure_tz_aware,
    decode_token
)
from core.dbmgr import (
    get_redis_chief_demotions_key,
    get_redis_chief_locations_key,
    get_redis_user_locations_key,
    get_redis_location_last_updates_key
)

def test_update_gps_position_missing_token(client):
    # We don't provide any token in the request headers, so we expect an unauthorized error
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    })
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_update_gps_position_invalid_token(client):
    # We provide an invalid token in the request headers, so we expect an unauthorized error
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': 'Bearer invalidtoken'
    })
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()['detail'] == token_not_valid_exception().detail

def test_update_gps_position_expired_token(client, test_baseuser, frozen_now):
    # We create an expired GPS token for testing
    user = test_baseuser['user']
    expired_token = create_geoposition_token(
        user_id=str(user.id),
        user_is_chief=user.is_chief,
        user_role=user.role,
        expires_delta=timedelta(minutes=-1)
    )
    # We provide the expired token in the request headers, so we expect an unauthorized error
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
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
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {default_gps_token}'
    })
    assert response.status_code == token_expired_exception().status_code
    assert response.json()['detail'] == token_expired_exception().detail

def test_update_gps_position_invalid_coordinates(client, test_baseuser):
    # We create a valid GPS token for testing
    user = test_baseuser['user']
    assert user.is_chief is not None
    assert user.role is not None
    gps_token = test_baseuser['gps_token']
    # We don't provide coordinates
    response = client.post('/api/update-gps-position', json={
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # We provide the valid token but invalid coordinates in the request body, so we expect a validation error
    response = client.post('/api/update-gps-position', json={
        'latitude': "a",  # Invalid latitude
        'longitude': "b"  # Invalid longitude
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Another case of invalid coordinates (latitude out of range)
    response = client.post('/api/update-gps-position', json={
        'latitude': 100.0,  # Invalid latitude
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Another case of invalid coordinates (longitude out of range)
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 200.0  # Invalid longitude
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Another example: latitude not present
    response = client.post('/api/update-gps-position', json={
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    # Another example: longitude not present
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

async def test_update_gps_position_success_as_normal_user(client, redis_session, test_baseuser):
    user = test_baseuser['user']
    assert user.is_chief == False
    gps_token = test_baseuser['gps_token']
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # Now we check Redis cache to see if the location was updated correctly
    user_Loc_key = get_redis_user_locations_key(str(user.id))
    chief_Loc_key = get_redis_chief_locations_key(str(user.id))
    last_upd_key = get_redis_location_last_updates_key(str(user.id))
    chief_dem_key = get_redis_chief_demotions_key(str(user.id))
    # The user should be in the user locations sorted set, but not in the chief locations sorted set
    user_location_results = await redis_session.geopos(user_Loc_key, str(user.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(user.id))
    last_update = await redis_session.zscore(last_upd_key, str(user.id))
    chief_demotion = await redis_session.zscore(chief_dem_key, str(user.id))
    assert all(p is None for p in chief_location_results), "Chief location should not be present in Redis for a normal user"
    assert all(p is not None for p in user_location_results), "User location should be present in Redis"
    assert last_update is not None, "Last update timestamp should be present in Redis"
    assert chief_demotion is None, "Chief demotion should not be present in Redis for a normal user"
    # We check the last update format, it should be a valid integer timestamp
    try:
        last_update_int = int(last_update)
    except ValueError:
        assert False, "Last update timestamp should be a valid integer"
    # We check that the last update timestamp is recent (within the last minute)
    now_int_ts = int(ensure_tz_aware(now_tz_naive()).timestamp())
    assert now_int_ts - last_update_int < 60, "Last update timestamp should be recent (within the last minute)"

async def test_update_gps_position_success_as_chief(client, redis_session, test_chief):
    chief = test_chief['user']
    assert chief.is_chief == True
    gps_token = test_chief['gps_token']
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # Now we check Redis cache to see if the location was updated correctly
    chief_Loc_key = get_redis_chief_locations_key(str(chief.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(chief.id))
    assert all(p is not None for p in chief_location_results), "Chief location should be present in Redis for a chief user"
    # We assert that the chief is not present in the user locations sorted set
    user_Loc_key = get_redis_user_locations_key(str(chief.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(chief.id))
    assert all(p is None for p in user_location_results), "User location should not be present in Redis for a chief user"
    last_upd_key = get_redis_location_last_updates_key(str(chief.id))
    last_update = await redis_session.zscore(last_upd_key, str(chief.id))
    # We check the last update format, it should be a valid integer timestamp
    try:
        last_update_int = int(last_update)
    except ValueError:
        assert False, "Last update timestamp should be a valid integer"
    # We check that the last update timestamp is recent (within the last minute)
    now_int_ts = int(ensure_tz_aware(now_tz_naive()).timestamp())
    assert now_int_ts - last_update_int < 60, "Last update timestamp should be recent (within the last minute)"

async def test_update_gps_position_as_demoted_chief(client, db_session, redis_session, test_chief):
    demoted_chief = test_chief['user']
    # Initially, the user is a chief
    assert demoted_chief.is_chief == True
    # We simulate the demotion of the chief in the database
    demoted_chief.is_chief = False
    db_session.add(demoted_chief)
    db_session.commit()
    db_session.refresh(demoted_chief)
    # We simulate the demotion of the chief in Redis by adding an entry in the chief demotions sorted set with the current timestamp as score
    chief_dem_key = get_redis_chief_demotions_key(str(demoted_chief.id))
    chief_dem_at = int(ensure_tz_aware(now_tz_naive()).timestamp())
    await redis_session.zadd(chief_dem_key, {str(demoted_chief.id): chief_dem_at})
    # We simulate the demoted chief has a chief location stored in Redis
    chiefloc_key = get_redis_chief_locations_key(str(demoted_chief.id))
    await redis_session.geoadd(chiefloc_key, (9.0, 45.0, str(demoted_chief.id)))
    # But the gps token tells us that the user is still a chief, because the token was issued before the demotion  
    gps_token = test_chief['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 1, "The GPS token should indicate that the user is a chief"
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # In Redis, the demoted chief should be treated as a normal user, so they should be present in the user locations sorted set, but not in the chief locations sorted set
    user_Loc_key = get_redis_user_locations_key(str(demoted_chief.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(demoted_chief.id))
    chief_Loc_key = get_redis_chief_locations_key(str(demoted_chief.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(demoted_chief.id))
    assert all(p is not None for p in user_location_results), "User location should be present in Redis for a demoted chief"
    assert all(p is None for p in chief_location_results), "Chief location should not be present in Redis for a demoted chief"
    # We assert that the demoted chief is present in the chief demotions sorted set
    chief_demotion = await redis_session.zscore(chief_dem_key, str(demoted_chief.id))
    assert chief_demotion is not None, "Chief demotion should be present in Redis for a demoted chief"
    # We check the chief demotion timestamp format, it should be a valid integer timestamp
    try:
        chief_demotion_int = int(chief_demotion)
    except ValueError:
        assert False, "Chief demotion timestamp should be a valid integer"
    now_int_ts = int(ensure_tz_aware(now_tz_naive()).timestamp())
    assert now_int_ts - chief_demotion_int < 60, "Chief demotion timestamp should be recent (within the last minute)"

async def test_update_gps_position_as_demoted_chief_then_repromoted(client, db_session, redis_session, test_chief):
    demoted_chief = test_chief['user']
    # Initially, the user is a chief
    assert demoted_chief.is_chief == True
    # We simulate the demotion of the chief in the database
    demoted_chief.is_chief = False
    db_session.add(demoted_chief)
    db_session.commit()
    db_session.refresh(demoted_chief)
    # We simulate the demotion of the chief in Redis by adding an entry in the chief demotions sorted set with the current timestamp as score
    chief_dem_key = get_redis_chief_demotions_key(str(demoted_chief.id))
    chief_dem_at = int(ensure_tz_aware(now_tz_naive()).timestamp())
    await redis_session.zadd(chief_dem_key, {str(demoted_chief.id): chief_dem_at})
    # Now we simulate the repromotion of the chief by removing the entry from the chief demotions sorted set and adding a new entry in the chief locations sorted set
    chiefloc_key = get_redis_chief_locations_key(str(demoted_chief.id))
    await redis_session.geoadd(chiefloc_key, (9.0, 45.0, str(demoted_chief.id)))
    await redis_session.zrem(chief_dem_key, str(demoted_chief.id))
    # The GPS token still indicates that the user is a chief, because it was issued before both the demotion and repromotion  
    gps_token = test_chief['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 1, "The GPS token should indicate that the user is a chief"
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # In Redis, the repromoted chief should be treated as a chief again, so they should be present in the chief locations sorted set, but not in the user locations sorted set
    chief_Loc_key = get_redis_chief_locations_key(str(demoted_chief.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(demoted_chief.id))
    user_Loc_key = get_redis_user_locations_key(str(demoted_chief.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(demoted_chief.id))
    assert all(p is not None for p in chief_location_results), "Chief location should be present in Redis for a repromoted chief"
    assert all(p is None for p in user_location_results), "User location should not be present in Redis for a repromoted chief"

async def test_update_gps_position_promoted_user_as_chief(client, db_session, redis_session, test_baseuser):
    promoted_user = test_baseuser['user']
    # Initially, the user is not a chief
    assert promoted_user.is_chief == False
    # We simulate the promotion of the user to chief in the database
    promoted_user.is_chief = True
    db_session.add(promoted_user)
    db_session.commit()
    db_session.refresh(promoted_user)
    # The GPS token still indicates that the user is not a chief, because it was issued before the promotion  
    gps_token = test_baseuser['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 0, "The GPS token should indicate that the user is not a chief"
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # Note: in this case, in Redis, the promoted user should be treated as a normal user, because the GPS token indicates they are not a chief, so they should be present in the user locations sorted set, but not in the chief locations sorted set
    user_Loc_key = get_redis_user_locations_key(str(promoted_user.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(promoted_user.id))
    chief_Loc_key = get_redis_chief_locations_key(str(promoted_user.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(promoted_user.id))
    assert all(p is not None for p in user_location_results), "User location should be present in Redis for a promoted user"
    assert all(p is None for p in chief_location_results), "Chief location should not be present in Redis for a promoted user with an old GPS token"
    # If the user does an auth refresh, they should get a new gps token, so we simulate that by creating a new GPS token with the updated chief status
    refresh_token = test_baseuser['refresh_token']
    response = client.post('/api/auth/refresh', json={
        'refresh_token': refresh_token
    })
    assert response.status_code == status.HTTP_200_OK
    new_gps_token = response.json()['gps_token']
    assert new_gps_token != gps_token, "The new GPS token should be different from the old one after refresh"
    new_gps_token_data = decode_token(new_gps_token)
    new_user_is_chief = new_gps_token_data["user_is_chief"]
    assert new_user_is_chief == 1, "The new GPS token should indicate that the user is a chief after promotion and refresh"
    # Now we provide the new GPS token in the request body, so we expect a successful update and the user should be treated as a chief in Redis
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {new_gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(promoted_user.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(promoted_user.id))
    assert all(p is not None for p in chief_location_results), "Chief location should be present in Redis for a promoted user with a new GPS token"
    assert all(p is None for p in user_location_results), "User location should not be present in Redis for a promoted user with a new GPS token"

async def test_update_gps_position_promote_user_as_chief_then_demote_again(client, db_session, redis_session, test_baseuser):
    promoted_user = test_baseuser['user']
    # Initially, the user is not a chief
    assert promoted_user.is_chief == False
    # We simulate the promotion of the user to chief in the database
    promoted_user.is_chief = True
    db_session.add(promoted_user)
    db_session.commit()
    db_session.refresh(promoted_user)
    # Now we simulate the demotion of the user back to normal user in the database
    promoted_user.is_chief = False
    db_session.add(promoted_user)
    db_session.commit()
    db_session.refresh(promoted_user)
    # In Redis, we simulate the demotion of the user by adding an entry in the chief demotions sorted set with the current timestamp as score, and removing any entry from the chief locations sorted set
    chief_dem_key = get_redis_chief_demotions_key(str(promoted_user.id))
    chief_dem_at = int(ensure_tz_aware(now_tz_naive()).timestamp())
    await redis_session.zadd(chief_dem_key, {str(promoted_user.id): chief_dem_at})
    # The GPS token still indicates that the user is not a chief, because it was issued before both the promotion and demotion  
    gps_token = test_baseuser['gps_token']
    gps_token_data = decode_token(gps_token)
    user_is_chief = gps_token_data["user_is_chief"]
    assert user_is_chief == 0, "The GPS token should indicate that the user is not a chief"
    # We provide the valid token and valid coordinates in the request body, so we expect a successful update
    response = client.post('/api/update-gps-position', json={
        'latitude': 45.0,
        'longitude': 9.0
    }, headers={
        'Authorization': f'Bearer {gps_token}'
    })
    assert response.status_code == status.HTTP_200_OK
    # In Redis, the demoted user should be treated as a normal user, so they should be present in the user locations sorted set, but not in the chief locations sorted set
    user_Loc_key = get_redis_user_locations_key(str(promoted_user.id))
    user_location_results = await redis_session.geopos(user_Loc_key, str(promoted_user.id))
    chief_Loc_key = get_redis_chief_locations_key(str(promoted_user.id))
    chief_location_results = await redis_session.geopos(chief_Loc_key, str(promoted_user.id))
    assert all(p is not None for p in user_location_results), "User location should be present in Redis for a demoted promoted user"
    assert all(p is None for p in chief_location_results), "Chief location should not be present in Redis for a demoted promoted user"
    # There is also the demoted raw in the chief demotions sorted set, because the user was promoted as chief, and then demoted again
    chief_dem_key = get_redis_chief_demotions_key(str(promoted_user.id))
    chief_demotion = await redis_session.zscore(chief_dem_key, str(promoted_user.id))
    assert chief_demotion is not None, "Chief demotion should be present in Redis for a promoted and then demoted user"
    # We check the chief demotion timestamp format, it should be a valid integer timestamp
    try:
        chief_demotion_int = int(chief_demotion)
    except ValueError:
        assert False, "Chief demotion timestamp should be a valid integer"
    now_int_ts = int(ensure_tz_aware(now_tz_naive()).timestamp())
    assert now_int_ts - chief_demotion_int < 60, "Chief demotion timestamp should be recent (within the last minute) for a promoted and then demoted user"
      