# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
from datetime import timedelta
from fakeredis import FakeRedis
from services.security import now_tz_naive, GEOPOSITION_TOKEN_TTL_MINUTES
from core.periodic_events import (
    log_cleanup_expired_locations_error,
    log_cleanup_expired_locations_completed,
    log_cleanup_expired_locations_started,
    log_cleanup_expired_demotions_error,
    log_cleanup_expired_demotions_started,
    log_cleaning_demotions_shard,
    log_cleanup_expired_demotions_completed
    )
from core.dbmgr import (
    redis, cluster, RedisHandleTypeError,
    REDIS_CHIEF_DEMOTIONS_KEY,
    REDIS_USER_LOCATIONS_KEY,
    REDIS_CHIEF_LOCATIONS_KEY,
    REDIS_LOCATION_LAST_UPDATES_KEY,
    REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY,
    REDIS_COOLDOWN_LOCATIONS_CLEANUP_TIMEOUT,
    REDIS_COOLDOWN_DEMOTIONS_CLEANUP_KEY,
    REDIS_COOLDOWN_DEMOTIONS_CLEANUP_TIMEOUT,
    REDIS_TOTAL_SHARDS)

async def do_locations_cleanup(redis_handle):
    if isinstance(redis_handle, cluster.RedisCluster):
        await cleanup_expired_locations(redis_handle)
        return
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            await cleanup_expired_locations(redis_session)
        return
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        await cleanup_expired_locations(redis_handle)
        return
    else:
        raise RedisHandleTypeError(redis_handle)

async def cleanup_expired_locations(redis_client):
    now = now_tz_naive()
    exp_dt = now - timedelta(hours=48) # expiration threshold: 48 hours
    exp_int_ts = int(exp_dt.timestamp())
    total_deleted = 0
    lock_key = REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY
    lock_timeout = REDIS_COOLDOWN_LOCATIONS_CLEANUP_TIMEOUT
    # nx=True (Set if Not Exists)
    # ex=lock_timeout (expiry, cooldown)
    lock_acquired = await redis_client.set(lock_key, "active", ex=lock_timeout, nx=True)
    if not lock_acquired:
        # if we cannot acquire the lock, it means that another periodic cleanup task is currently running 
        # (or recently ran and is in cooldown), so we skip the execution
        return 0
    log_cleanup_expired_locations_started(
        detail=f"Starting parallel cleanup across {REDIS_TOTAL_SHARDS} shards. Threshold: {exp_int_ts}"
    )
    try:
        tasks = [cleanup_expired_locations_shard(
                i, exp_int_ts, redis_client
            ) for i in range(REDIS_TOTAL_SHARDS)]
        results = await asyncio.gather(*tasks)
        total_deleted = sum(results)       
        log_cleanup_expired_locations_completed(
            detail=f"Cleanup completed: {total_deleted} locations removed across {REDIS_TOTAL_SHARDS} shards"
        )
        return total_deleted
    except Exception as e:
        log_cleanup_expired_locations_error(detail=str(e))
        return total_deleted

async def cleanup_expired_locations_shard(shard_index, exp_int_ts, redis_client):
    deleted_in_shard = 0
    last_upd_key = REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)
    uloc_key = REDIS_USER_LOCATIONS_KEY.format(i=shard_index)
    chiefloc_key = REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)
    while True:
        expired_user_ids = await redis_client.zrangebyscore(
            last_upd_key, 
            min = "-inf", 
            max = exp_int_ts, 
            start=0, 
            num=5000
        )
        if not expired_user_ids:
            break
        # Potential race condition here, but it's not a big issue for consistency (the client will just have to update the location again)
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zrem(chiefloc_key, *expired_user_ids)
            pipe.zrem(uloc_key, *expired_user_ids)
            pipe.zrem(last_upd_key, *expired_user_ids)
            await pipe.execute()
        deleted_in_shard += len(expired_user_ids)
        await asyncio.sleep(0.05) 
    return deleted_in_shard

async def do_demotions_cleanup(redis_handle):
    if isinstance(redis_handle, cluster.RedisCluster):
        await cleanup_expired_demotions(redis_handle)
        return
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            await cleanup_expired_demotions(redis_session)
        return
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        await cleanup_expired_demotions(redis_handle)
        return
    else:
        raise RedisHandleTypeError(redis_handle)

async def cleanup_expired_demotions(redis_client):
    now = now_tz_naive()
    # expiration threshold: same as geoposition token TTL, 
    # since the demotion is linked to the geoposition update and should last as long as the token validity
    # note: we add a small grace period of 5 minutes to avoid edge cases of demotions being removed just before the token expires
    exp_dt = now - timedelta(minutes=(GEOPOSITION_TOKEN_TTL_MINUTES + 5)) 
    exp_int_ts = int(exp_dt.timestamp())
    total_deleted = 0
    lock_key = REDIS_COOLDOWN_DEMOTIONS_CLEANUP_KEY
    lock_timeout = REDIS_COOLDOWN_DEMOTIONS_CLEANUP_TIMEOUT
    # nx=True (Set if Not Exists)
    # ex=lock_timeout (expiry, cooldown)
    lock_acquired = await redis_client.set(lock_key, "active", ex=lock_timeout, nx=True)
    if not lock_acquired:
        # if we cannot acquire the lock, it means that another periodic cleanup task is currently running 
        # (or recently ran and is in cooldown), so we skip the execution
        return 0
    log_cleanup_expired_demotions_started(
        detail=f"Starting parallel cleanup across {REDIS_TOTAL_SHARDS} shards. Threshold: {exp_int_ts}"
    )
    try:
        tasks = [cleanup_expired_demotions_shard(
                i, exp_int_ts, redis_client
            ) for i in range(REDIS_TOTAL_SHARDS)]
        results = await asyncio.gather(*tasks)
        total_deleted = sum(results)       
        log_cleanup_expired_demotions_completed(
            detail=f"Cleanup completed: {total_deleted} demotions removed across {REDIS_TOTAL_SHARDS} shards"
        )
        return total_deleted
    except Exception as e:
        log_cleanup_expired_demotions_error(detail=str(e))
        return total_deleted

async def cleanup_expired_demotions_shard(shard_index, exp_int_ts, redis_client):
    deleted_in_shard = 0
    demotions_key = REDIS_CHIEF_DEMOTIONS_KEY.format(i=shard_index)
    log_cleaning_demotions_shard(detail=f"Cleaning chief demotions for shard {shard_index}")
    while True:
        expired_user_ids = await redis_client.zrangebyscore(
            demotions_key, 
            min = "-inf", 
            max = exp_int_ts, 
            start=0, 
            num=5000
        )
        if not expired_user_ids:
            break
        # Potential race condition here, but it's not a big issue for consistency 
        # because if a chief is demoted again during the cleanup (and the cleanup will accidentally delete the new demotion), 
        # the client meanwhile will have received a "not chief" status by a new gps token (via refresh api or login)
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zrem(demotions_key, *expired_user_ids)
            await pipe.execute()
        deleted_in_shard += len(expired_user_ids)
        await asyncio.sleep(0.05) 
    return deleted_in_shard
