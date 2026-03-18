# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import redis.asyncio as redis
from datetime import timedelta
from core.settings import settings
from services.security import now_tz_naive
from core.periodic_events import (
    log_cleanup_expired_locations_error,
    log_cleanup_expired_locations_completed,
    log_cleanup_expired_locations_started)
from core.dbmgr import (
    REDIS_USER_LOCATIONS_KEY,
    REDIS_CHIEF_LOCATIONS_KEY,
    REDIS_LOCATION_LAST_UPDATES_KEY,
    REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY,
    REDIS_TOTAL_SHARDS)

async def do_locations_cleanup(redis_pool):
    if settings.redis_mode == "cluster":
        await cleanup_expired_locations(redis_pool)
    else:
        async with redis.Redis(connection_pool=redis_pool, decode_responses=True) as redis_client:
            await cleanup_expired_locations(redis_client)
    return

async def cleanup_expired_locations(redis_client):
    now = now_tz_naive()
    exp_dt = now - timedelta(hours=48) # expiration threshold: 48 hours
    exp_int_ts = int(exp_dt.timestamp())
    total_deleted = 0
    lock_key = REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY
    # nx=True (Set if Not Exists)
    # ex=172800 (expiry 48 hours - cooldown)
    lock_acquired = await redis_client.set(lock_key, "active", ex=172800, nx=True)
    if not lock_acquired:
        # if we cannot acquire the lock, it means that another periodic cleanup task is currently running 
        # (or recently ran and is in cooldown)
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
        async with redis_client.pipeline(transaction=True) as pipe:
            pipe.zrem(chiefloc_key, *expired_user_ids)
            pipe.zrem(uloc_key, *expired_user_ids)
            pipe.zrem(last_upd_key, *expired_user_ids)
            await pipe.execute()
        deleted_in_shard += len(expired_user_ids)
        await asyncio.sleep(0.05) 
    return deleted_in_shard
