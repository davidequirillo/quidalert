# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fakeredis.aioredis import FakeRedis
from services.security import (
    now_tz_aware
)
from models.general import UserRole
from services.periodics import (
    do_locations_cleanup,
    cleanup_expired_locations_shard,
    cleanup_expired_special_locations_shard,
)
from core.dbmgr import (
    REDIS_COOLDOWN_LOCATIONS_CLEANUP_TIMEOUT,
    get_redis_shards_num,
    REDIS_LOCATION_LAST_UPDATES_KEY,
    REDIS_SPEC_LOCATION_LAST_UPDATES_KEY,
    REDIS_USER_LOCATIONS_KEY,
    REDIS_SPEC_LOCATIONS_KEY,
    REDIS_CHIEF_LOCATIONS_KEY,
    get_redis_location_last_updates_key,
    get_redis_spec_location_last_updates_key,
    get_all_redis_location_last_updates_keys,
    get_all_redis_spec_location_last_updates_keys,
    get_redis_user_locations_key,
    get_redis_spec_locations_key,
    get_redis_chief_locations_key,
)
from services.periodics import LOCATIONS_TTL_HOURS

async def test_delete_expired_locations_for_each_shard(redis_session):
    # Get all redis shard keys 
    shards = get_all_redis_location_last_updates_keys()
    shard_valid_counts = {}
    shard_expired_counts = {}
    batch_size = 5 # We use a very small batch size to test the batching logic of the cleaning function
    for shard in shards:
        shard_valid_counts[shard] = 0
        shard_expired_counts[shard] = 0
    # We create many locations (some expired and some not) to test the delete_expired_locations function
    # we begin inserting 100 locations valid (not expired)
    now = now_tz_aware()
    for i in range(0, 100):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys.
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(minutes=i)
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
        shard_valid_counts[last_updates_key] += 1
    # Then we insert 200 expired locations
    for i in range(100, 300):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys.
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + (i * 0.001)) # we set the last update time to be more than 48 hours ago, so that it is expired
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
        shard_expired_counts[last_updates_key] += 1
    # We check that the number of locations we inserted is correct
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard] + shard_expired_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} locations, got {count}"
        assert shard_expired_counts[shard] > batch_size, f"Shard {shard}: expected more than {batch_size} expired locations to test the batching logic, got {shard_expired_counts[shard]}"
        # if this assertion fails, it means that we don't have enough expired locations in this shard to test the batching logic of the cleanup function, so we need to insert more samples of expired locations, 
        # to fill at least 2 batches (more than batch_size) of expired locations for each shard, to ensure that we test the batching logic of the cleanup function correctly
    # Now we call the delete_expired_locations_shard function
    # to test the cleanup of expired locations for a specific shard (testing each shard individually).
    exp_dt = now - timedelta(hours=LOCATIONS_TTL_HOURS) # expiration threshold: 48 hours
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling cleanup_expired_locations for each shard with expiration threshold timestamp: {exp_int_ts}")
    for shard_index in range(get_redis_shards_num()):
        deleted_count = await cleanup_expired_locations_shard(shard_index, exp_int_ts, redis_session, batch_size=batch_size)
        # we check that the number of deleted locations is equal to the number of expired locations we inserted for that shard
        shard_key = REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)
        assert deleted_count == shard_expired_counts[shard_key], f"Shard {shard_key}: expected {shard_expired_counts[shard_key]} deleted locations, got {deleted_count}"
    # Now, we can check that all expired locations have been deleted and only valid locations remain
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} locations after cleanup, got {count}"
    
async def test_delete_expired_locations(redis_session):
    # We test the do_locations_cleanup function that processes all shards in one call.
    # We create many locations (some expired and some not) to test the delete_expired_locations function
    # we begin inserting 100 locations valid (not expired)
    now = now_tz_aware()
    for i in range(0, 100):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys.
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(minutes=i)
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # Then we insert 200 expired locations
    for i in range(100, 300):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys.
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + (i * 0.001))
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # We check that the number of locations we inserted is correct
    shards = get_all_redis_location_last_updates_keys()
    total_location_updates = 0
    for shard in shards:
        count = await redis_session.zcard(shard)
        total_location_updates += count
    assert total_location_updates == 300, f"Expected 300 locations before cleanup, got {total_location_updates}"
    # Now we call the do_locations_cleanup function
    exp_dt = now - timedelta(hours=LOCATIONS_TTL_HOURS)
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling cleanup_expired_locations with expiration threshold timestamp: {exp_int_ts}")
    # Checking instance type of redis_session to ensure it's a FakeRedis instance for testing purposes
    assert isinstance(redis_session, FakeRedis), "Expected redis_session to be an instance of FakeRedis"
    deleted_count, _ = await do_locations_cleanup(redis_session)
    # We check that the number of deleted locations is equal to the number of expired locations we inserted
    assert deleted_count == 200, f"Expected 200 deleted locations, got {deleted_count}"
    # Now, we can check that all expired locations have been deleted and only valid locations remain
    total_location_updates_after = 0
    shards = get_all_redis_location_last_updates_keys()
    for shard_index in range(get_redis_shards_num()):
        last_updates_key = REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)
        user_locations_key = REDIS_USER_LOCATIONS_KEY.format(i=shard_index)
        chief_locations_key = REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)
        last_updates_count = await redis_session.zcard(last_updates_key)
        user_locations_count = await redis_session.zcard(user_locations_key)
        chief_locations_count = await redis_session.zcard(chief_locations_key)
        total_location_updates_after += last_updates_count
        # We check that the number of last updates, user locations and chief locations are all the same for each shard, to ensure that there are no orphaned expired location data
        # Note: remember that user locations and chief locations have the same number in this test
        # It's not a realistic scenario, but it allows us to easily test the cleanup function
        assert last_updates_count == user_locations_count
        assert last_updates_count == chief_locations_count
    assert total_location_updates_after == 100, f"Expected 100 locations after cleanup, got {total_location_updates_after}"

async def test_cleanup_expired_locations_lock_already_acquired(redis_session):
    # We insert some expired locations to ensure that there is something to clean up
    now = now_tz_aware()
    for i in range(10):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + 1) # we set the last update time to be more than 48 hours ago, so that it is expired
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # Now we call the do_locations_cleanup function to acquire the lock and start the cleanup process
    deleted_count, _ = await do_locations_cleanup(redis_session)
    assert deleted_count == 10, f"Expected 10 deleted locations, got {deleted_count}"
    # Now, we re-insert some expired locations and we call the do_locations_cleanup function again while the lock is still active,
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + 1) # we set the last update time to be more than 48 hours ago, so that it is expired
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # we call the do_locations_cleanup function again while the lock is still active, to test that it correctly skips the execution
    deleted_count, _ = await do_locations_cleanup(redis_session)
    assert deleted_count == 0, f"Expected 0 deleted locations since lock is active, got {deleted_count}"
    # we can also check that the expired locations we just inserted are still there, since the cleanup should have been skipped
    total_count = 0
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        last_updates_count = await redis_session.zcard(last_updates_key)
        user_locations_count = await redis_session.zcard(user_locations_key)
        chief_locations_count = await redis_session.zcard(chief_locations_key)
        assert last_updates_count > 0, f"Expected expired location for user {user_id_str} to still be present since lock is active, but it was deleted"
        assert user_locations_count > 0, f"Expected expired location for user {user_id_str} to still be present since lock is active, but it was deleted"
        assert chief_locations_count > 0, f"Expected expired location for user {user_id_str} to still be present since lock is active, but it was deleted"
        total_count += last_updates_count
    assert total_count > 0, f"Expected at least some expired locations to still be present since lock is active, but all were deleted"
    assert total_count == 8, f"Expected 8 expired locations to still be present since lock is active, got {total_count}"

async def test_cleanup_expired_locations_lock_released(redis_session, frozen_now):
    # This test is similar to the previous one, 
    # but the time between the first call to do_locations_cleanup and the second call is longer than the lock cooldown,
    # so the lock should have been released, and the do_locations_cleanup function should be able to acquire the lock and execute a new cleanup.
    # We insert some expired locations to ensure that there is something to clean up
    now = now_tz_aware()
    for i in range(10):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + 1) # we set the last update time to be more than 48 hours ago, so that it is expired
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # Now we call the do_locations_cleanup function to acquire the lock and start the cleanup process
    deleted_count, _ = await do_locations_cleanup(redis_session)
    assert deleted_count == 10, f"Expected 10 deleted locations, got {deleted_count}"
    # Now, we re-insert some expired locations and we call the do_locations_cleanup function again after the lock cooldown has expired, to test that it correctly acquires the lock and executes the cleanup
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + 1) # we set the last update time to be more than 48 hours ago, so that it is expired
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # We wait for the lock cooldown to expire before calling again the do_locations_cleanup function, to ensure that the lock has been released and can be acquired again
    # We simulate the passage of time by advancing the frozen time by more than the lock cooldown duration
    frozen_now.tick(delta=timedelta(seconds=REDIS_COOLDOWN_LOCATIONS_CLEANUP_TIMEOUT + 1))
    deleted_count, _ = await do_locations_cleanup(redis_session)
    assert deleted_count == 8, f"Expected 8 deleted locations after lock cooldown expired, got {deleted_count}"
    # We can also check that all expired locations have been deleted
    total_count = 0
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        last_updates_count = await redis_session.zcard(last_updates_key)
        user_locations_count = await redis_session.zcard(user_locations_key)
        chief_locations_count = await redis_session.zcard(chief_locations_key)
        assert last_updates_count == 0, f"Expected expired location for user {user_id_str} to be deleted after lock cooldown expired, but it is still present"
        assert user_locations_count == 0, f"Expected expired location for user {user_id_str} to be deleted after lock cooldown expired, but it is still present"
        assert chief_locations_count == 0, f"Expected expired location for user {user_id_str} to be deleted after lock cooldown expired, but it is still present"
        total_count += last_updates_count
    assert total_count == 0, f"Expected all expired locations to be deleted after lock cooldown expired, but some are still present, total count: {total_count}"

async def test_delete_expired_special_locations_for_each_shard(redis_session):
    # This test is similar to the test_delete_expired_locations_shard test, 
    # but it tests the cleanup of expired special locations for a specific shard (testing each shard individually).
    # For each role, we insert 100 valid special locations (not expired) and 200 expired special locations
    # --------------------------
    # Get all redis shard keys for special locations.
    shards = get_all_redis_spec_location_last_updates_keys()
    shard_valid_counts = {}
    shard_expired_counts = {}
    batch_size = 5 # We use a very small batch size to test the batching logic of the cleaning function
    for shard in shards:
        shard_valid_counts[shard] = 0
        shard_expired_counts[shard] = 0
    now = now_tz_aware()
    for role in [r.value for r in UserRole]:
        # We insert 100 valid special locations for this role
        for i in range(0, 100):
            user_id_str = f"specialist_{i}"
            spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id_str, role)
            spec_locations_key = get_redis_spec_locations_key(user_id_str, role)
            # We add some dummy location data for the specialist user
            await redis_session.geoadd(spec_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
            last_update = now - timedelta(minutes=i)
            await redis_session.zadd(spec_last_updates_key, {user_id_str: int(last_update.timestamp())})
            shard_valid_counts[spec_last_updates_key] += 1
        # Then we insert 200 expired locations for this role
        for i in range(100, 300):
            user_id_str = f"specialist_{i}"
            spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id_str, role)
            spec_locations_key = get_redis_spec_locations_key(user_id_str, role)
            # We add some dummy location data for the specialist user
            await redis_session.geoadd(spec_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
            last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + (i * 0.001)) # we set the last update time to be more than 48 hours ago, so that it is expired
            await redis_session.zadd(spec_last_updates_key, {user_id_str: int(last_update.timestamp())})
            shard_expired_counts[spec_last_updates_key] += 1
    # We check that the number of locations we inserted is correct
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard] + shard_expired_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} locations, got {count}"
        assert shard_expired_counts[shard] > batch_size, f"Shard {shard}: expected more than {batch_size} expired locations to test the batching logic, got {shard_expired_counts[shard]}"
        # If this assertion fails, it means that we don't have enough expired locations in this shard to test the batching logic of the cleanup function, so we need to insert more samples of expired locations, 
        # to fill at least 2 batches (more than batch_size) of expired locations for each shard, to ensure that we test the batching logic of the cleanup function correctly
    # Now we call the delete_expired_special_locations function
    exp_dt = now - timedelta(hours=LOCATIONS_TTL_HOURS) # expiration threshold: 48 hours
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling cleanup_expired_special_locations for each shard with expiration threshold timestamp: {exp_int_ts}")
    for shard_index in range(get_redis_shards_num()):
        deleted_count_from_function = await cleanup_expired_special_locations_shard(shard_index, exp_int_ts, redis_session, batch_size=batch_size)
        # We check that the number of deleted special locations from the periodic function 
        # is equal to the number of expired special locations we inserted for that shard (shard_index).
        # Note: deleted_count_from_function is the number of deleted special locations for all roles combined, for that single shard (shard_index). 
        deleted_count_for_all_roles = 0
        for role in [r.value for r in UserRole]:
            shard_key = REDIS_SPEC_LOCATION_LAST_UPDATES_KEY.format(i=shard_index, role=role)
            deleted_count_for_role = shard_expired_counts[shard_key]
            deleted_count_for_all_roles += deleted_count_for_role
        assert deleted_count_for_all_roles == deleted_count_from_function
    # Now, we can check that all expired locations have been deleted and only valid locations remain
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} special locations after cleanup, got {count}"

async def test_delete_expired_normal_and_special_locations(redis_session):
    # We test the do_locations_cleanup function that processes all shards in one call.
    # It cleans up both normal locations and special locations (special locations are created/updated by users with a role assigned).
    # We create many locations (some expired and some not) to test the do_locations_cleanup function
    # we begin inserting 100 normal locations valid (not expired)
    now = now_tz_aware()
    for i in range(0, 100):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to user locations and chief locations keys.
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(minutes=i)
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # Then we insert 200 expired locations
    for i in range(100, 300):
        user_id_str = f"user_{i}"
        last_updates_key = get_redis_location_last_updates_key(user_id_str)
        user_locations_key = get_redis_user_locations_key(user_id_str)
        chief_locations_key = get_redis_chief_locations_key(user_id_str)
        # We add some dummy location data to the user locations and chief locations keys
        # It's not a realistic scenario, but it allows us to test the cleanup function.
        await redis_session.geoadd(user_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        await redis_session.geoadd(chief_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
        last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + (i * 0.001))
        await redis_session.zadd(last_updates_key, {user_id_str: int(last_update.timestamp())})
    # We check that the number of locations we inserted is correct
    shards = get_all_redis_location_last_updates_keys()
    total_location_updates = 0
    for shard in shards:
        count = await redis_session.zcard(shard)
        total_location_updates += count
    assert total_location_updates == 300, f"Expected 300 locations before cleanup, got {total_location_updates}"
    # For each role, we also insert some special locations (some expired and some not) to test the delete_expired_locations function
    for role in [r.value for r in UserRole]:
        # We insert 100 valid special locations for this role
        for i in range(0, 100):
            user_id_str = f"specialist_{i}"
            spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id_str, role)
            spec_locations_key = get_redis_spec_locations_key(user_id_str, role)
            # We add some dummy location data for the specialist user
            await redis_session.geoadd(spec_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
            last_update = now - timedelta(minutes=i)
            await redis_session.zadd(spec_last_updates_key, {user_id_str: int(last_update.timestamp())})
        # Then we insert 200 expired special locations for this role
        for i in range(100, 300):
            user_id_str = f"specialist_{i}"
            spec_last_updates_key = get_redis_spec_location_last_updates_key(user_id_str, role)
            spec_locations_key = get_redis_spec_locations_key(user_id_str, role)
            # We add some dummy location data for the specialist user
            await redis_session.geoadd(spec_locations_key, (12.34 + i*0.01, 56.78 + i*0.01, user_id_str))
            last_update = now - timedelta(hours=LOCATIONS_TTL_HOURS + (i * 0.001)) # we set the last update time to be more than 48 hours ago, so that it is expired
            await redis_session.zadd(spec_last_updates_key, {user_id_str: int(last_update.timestamp())})
    # We check that the number of locations we inserted is correct
    shards = get_all_redis_spec_location_last_updates_keys()
    total_location_updates = 0
    for shard in shards:
        count = await redis_session.zcard(shard)
        total_location_updates += count
    assert total_location_updates == 300 * len(UserRole), f"Expected {300 * len(UserRole)} locations before cleanup, got {total_location_updates}"
    # Now we call the delete_expired_locations function
    exp_dt = now - timedelta(hours=LOCATIONS_TTL_HOURS)
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling cleanup_expired_locations with expiration threshold timestamp: {exp_int_ts}")
    # Checking instance type of redis_session to ensure it's a FakeRedis instance for testing purposes
    assert isinstance(redis_session, FakeRedis), "Expected redis_session to be an instance of FakeRedis"
    del_norm_loc_count, del_spec_loc_count = await do_locations_cleanup(redis_session)
    # We check that the number of deleted locations is equal to the number of expired locations we inserted
    assert del_norm_loc_count == 200, f"Expected 200 deleted locations, got {del_norm_loc_count}"
    assert del_spec_loc_count == 200 * len(UserRole), f"Expected {200 * len(UserRole)} deleted special locations, got {del_spec_loc_count}"
    # Now, we can check that only valid normal locations remain
    total_location_updates_after = 0
    shards = get_all_redis_location_last_updates_keys()
    for shard_index in range(get_redis_shards_num()):
        last_updates_key = REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)
        user_locations_key = REDIS_USER_LOCATIONS_KEY.format(i=shard_index)
        chief_locations_key = REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)
        last_updates_count = await redis_session.zcard(last_updates_key)
        user_locations_count = await redis_session.zcard(user_locations_key)
        chief_locations_count = await redis_session.zcard(chief_locations_key)
        total_location_updates_after += last_updates_count
        # We check that the number of last updates, user locations and chief locations are all the same for each shard, to ensure that there are no orphaned expired location data
        # Note: remember that user locations and chief locations have the same number in this test
        # It's not a realistic scenario, but it allows us to easily test the cleanup function.
        assert last_updates_count == user_locations_count
        assert last_updates_count == chief_locations_count
    assert total_location_updates_after == 100, f"Expected 100 locations after cleanup, got {total_location_updates_after}"
    # Now, we can check that only valid special locations remain
    total_location_updates_after = 0
    shards = get_all_redis_location_last_updates_keys()
    for role in [r.value for r in UserRole]:
        for shard_index in range(get_redis_shards_num()):
            spec_last_updates_key = REDIS_SPEC_LOCATION_LAST_UPDATES_KEY.format(i=shard_index, role=role)
            spec_locations_key = REDIS_SPEC_LOCATIONS_KEY.format(i=shard_index, role=role)
            spec_last_updates_count = await redis_session.zcard(spec_last_updates_key)
            spec_locations_count = await redis_session.zcard(spec_locations_key)
            total_location_updates_after += spec_last_updates_count
            # We check that the number of last updates and special locations are the same for each shard and role, to ensure that there are no orphaned expired special location data
            assert spec_last_updates_count == spec_locations_count
    assert total_location_updates_after == 100 * len(UserRole), f"Expected {100 * len(UserRole)} locations after cleanup, got {total_location_updates_after}"
