# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from fakeredis.aioredis import FakeRedis
from services.security import (
    now_tz_aware
)
from services.periodics import (
    do_demotions_cleanup,
    cleanup_expired_demotions_shard,
)
from core.dbmgr import (
    REDIS_COOLDOWN_DEMOTIONS_CLEANUP_TIMEOUT,
    REDIS_TOTAL_SHARDS,
    REDIS_CHIEF_DEMOTIONS_KEY,
    get_redis_chief_demotions_key,
    get_all_redis_chief_demotions_keys,
)
from services.periodics import CHIEF_DEMOTIONS_TTL_MINUTES

async def test_delete_expired_demotions_for_each_shard(redis_session):
    # get all redis shard keys for chief demotions
    shards = get_all_redis_chief_demotions_keys()
    shard_valid_counts = {}
    shard_expired_counts = {}
    batch_size = 5 # We use a very small batch size to test the batching logic of the cleaning function
    for shard in shards:
        shard_valid_counts[shard] = 0
        shard_expired_counts[shard] = 0
    # We create many chief demotions (some expired and some not) to test the delete_expired_demotions function
    # we begin inserting 100 demotions valid (not expired)
    now = now_tz_aware()
    for i in range(0, 100):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(hours=i)
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
        shard_valid_counts[chief_demotions_key] += 1
    # Then we insert 200 expired demotions
    for i in range(100, 300):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + (i * 0.1))
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
        shard_expired_counts[chief_demotions_key] += 1
    # We check that the number of demotions we inserted is correct
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard] + shard_expired_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} demotions, got {count}"
        assert shard_expired_counts[shard] > batch_size, f"Shard {shard}: expected more than {batch_size} expired demotions to test the batching logic, got {shard_expired_counts[shard]}"
        # if this assertion fails, it means that we don't have enough expired demotions in this shard to test the batching logic of the cleanup function, so we need to insert more samples of expired demotions, 
        # to fill at least 2 batches (more than batch_size) of expired demotions for each shard, to ensure that we test the batching logic of the cleanup function correctly
    # Now we call the delete_expired_demotions function
    exp_dt = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES)
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling cleanup_expired_demotions for each shard with expiration threshold timestamp: {exp_int_ts}")
    for shard_index in range(REDIS_TOTAL_SHARDS):
        deleted_count = await cleanup_expired_demotions_shard(shard_index, exp_int_ts, redis_session, batch_size=batch_size)
        # we check that the number of deleted demotions is equal to the number of expired demotions we inserted for that shard
        shard_key = REDIS_CHIEF_DEMOTIONS_KEY.format(i=shard_index)
        assert deleted_count == shard_expired_counts[shard_key], f"Shard {shard_key}: expected {shard_expired_counts[shard_key]} deleted demotions, got {deleted_count}"
    # Now, we can check that all expired demotions have been deleted and only valid demotions remain
    for shard in shards:
        count = await redis_session.zcard(shard)
        expected_count = shard_valid_counts[shard]
        assert count == expected_count, f"Shard {shard}: expected {expected_count} demotions after cleanup, got {count}"

async def test_delete_expired_demotions(redis_session):
    # This test is similar to the previous one, but it tests the delete_expired_demotions function that processes all shards in one call
    # We create many demotions (some expired and some not) to test the delete_expired_demotions function
    # we begin inserting 100 demotions valid (not expired)
    now = now_tz_aware()
    for i in range(0, 100):
        user_id_str = f"user_{i}"
        demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(hours=i)
        await redis_session.zadd(demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # Then we insert 200 expired demotions
    for i in range(100, 300):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + (i * 0.1))
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # We check that the number of demotions we inserted is correct
    shards = get_all_redis_chief_demotions_keys()
    total_demotions = 0
    for shard in shards:
        count = await redis_session.zcard(shard)
        total_demotions += count
    assert total_demotions == 300, f"Expected 300 demotions before cleanup, got {total_demotions}"
    # Now we call the delete_expired_demotions function
    exp_dt = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES)
    exp_int_ts = int(exp_dt.timestamp())
    print(f"Calling delete_expired_demotions with expiration threshold timestamp: {exp_int_ts}")
    # Checking instance type of redis_session to ensure it's a FakeRedis instance for testing purposes
    assert isinstance(redis_session, FakeRedis), "Expected redis_session to be an instance of FakeRedis"
    deleted_count = await do_demotions_cleanup(redis_session)
    # we check that the number of deleted demotions is equal to the number of expired demotions we inserted
    assert deleted_count == 200, f"Expected 200 deleted demotions, got {deleted_count}"
    # Now, we can check that all expired demotions have been deleted and only valid demotions remain
    total_demotions_after = 0
    shards = get_all_redis_chief_demotions_keys()
    for shard_index in range(REDIS_TOTAL_SHARDS):
        chief_demotions_key = REDIS_CHIEF_DEMOTIONS_KEY.format(i=shard_index)
        demotions_count = await redis_session.zcard(chief_demotions_key)
        total_demotions_after += demotions_count
    assert total_demotions_after == 100, f"Expected 100 demotions after cleanup, got {total_demotions_after}"

async def test_cleanup_expired_demotions_lock_already_acquired(redis_session):
    # We insert some expired chief demotions to ensure that there is something to clean up
    now = now_tz_aware()
    for i in range(10):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 1)
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # Now we call the do_demotions_cleanup function to acquire the lock and start the cleanup process
    deleted_count = await do_demotions_cleanup(redis_session)
    assert deleted_count == 10, f"Expected 10 deleted demotions, got {deleted_count}"
    # Now, we re-insert some expired demotions and we call the do_demotions_cleanup function again while the lock is still active,
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 1)
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # we call the do_demotions_cleanup function again while the lock is still active, to test that it correctly skips the execution
    deleted_count = await do_demotions_cleanup(redis_session)
    assert deleted_count == 0, f"Expected 0 deleted demotions since lock is active, got {deleted_count}"
    # we can also check that the expired demotions we just inserted are still there, since the cleanup should have been skipped
    total_count = 0
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demotions_count = await redis_session.zcard(chief_demotions_key)
        total_count += demotions_count
        assert demotions_count > 0, f"Expected expired demotion for user {user_id_str} to still be present since lock is active, but it was deleted"
    assert total_count > 0, f"Expected at least some expired demotions to still be present since lock is active, but all were deleted"
    assert total_count == 8, f"Expected 8 expired demotions to still be present since lock is active, got {total_count}"

async def test_cleanup_expired_demotions_lock_released(redis_session, frozen_now):
    # This test is similar to the previous one, 
    # but the time between the first call to do_demotions_cleanup and the second call is longer than the lock cooldown,
    # so the lock should have been released, and the do_demotions_cleanup function should be able to acquire the lock and execute a new cleanup.
    # We insert some expired demotions to ensure that there is something to clean up
    now = now_tz_aware()
    for i in range(10):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 1)
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # Now we call the do_demotions_cleanup function to acquire the lock and start the cleanup process
    deleted_count = await do_demotions_cleanup(redis_session)
    assert deleted_count == 10, f"Expected 10 deleted demotions, got {deleted_count}"
    # Now, we re-insert some expired demotions and we call the do_demotions_cleanup function again after the lock cooldown has expired, to test that it correctly acquires the lock and executes the cleanup
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demoted_at = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES + 1)
        await redis_session.zadd(chief_demotions_key, {user_id_str: int(demoted_at.timestamp())})
    # We wait for the lock cooldown to expire before calling again the do_demotions_cleanup function, to ensure that the lock has been released and can be acquired again
    # We simulate the passage of time by advancing the frozen time by more than the lock cooldown duration
    frozen_now.tick(delta=timedelta(seconds=REDIS_COOLDOWN_DEMOTIONS_CLEANUP_TIMEOUT + 1))
    deleted_count = await do_demotions_cleanup(redis_session)
    assert deleted_count == 8, f"Expected 8 deleted demotions after lock cooldown expired, got {deleted_count}"
    # We can also check that all expired demotions have been deleted
    total_count = 0
    for i in range(10, 18):
        user_id_str = f"user_{i}"
        chief_demotions_key = get_redis_chief_demotions_key(user_id_str)
        demotions_count = await redis_session.zcard(chief_demotions_key)
        assert demotions_count == 0, f"Expected expired demotion for user {user_id_str} to be deleted after lock cooldown expired, but it is still present"
        total_count += demotions_count
    assert total_count == 0, f"Expected all expired demotions to be deleted after lock cooldown expired, but some are still present, total count: {total_count}"
