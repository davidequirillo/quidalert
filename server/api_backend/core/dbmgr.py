# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import zlib
from sqlmodel import create_engine, Session
import redis.asyncio as redis
from core.settings import settings

def get_engine():
    engine = create_engine(settings.db_url, 
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_recycle=settings.db_pool_recycle,
        # this is needed to avoid "psql connection has gone away" errors after some time of inactivity
        pool_pre_ping=True,
        echo=settings.db_engine_echo)
    return engine

def get_session(engine):
    with Session(engine) as session:
        yield session

def get_redis_pool():
    if settings.redis_mode == "cluster":
        redis_host = settings.redis_url.split("://")[1].split(":")[0]
        redis_port = settings.redis_url.split("://")[1].split(":")[1].split("/")[0]
        options = {
            "host": redis_host,
            "port": int(redis_port),
            "max_connections": settings.redis_max_connections_cluster,
            "decode_responses": True
        }
        redis.RedisCluster(**options)
    else:
        redis_pool = redis.ConnectionPool.from_url(
        settings.redis_url, 
        max_connections=settings.redis_max_connections, 
        decode_responses=True)
        return redis_pool

def get_redis_conn(pool):
    if settings.redis_mode == "cluster":
        return pool
    else:
        return redis.Redis(connection_pool=pool, decode_responses=True)

REDIS_TOTAL_SHARDS = 16
REDIS_MUTEX_CHIEF_UPDATE_KEY = "{shard:0}:mutexes:chief_update"
REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY = "{shard:0}:cooldowns:locations_cleanup"
REDIS_USER_LOCATIONS_KEY = "{{shard:{i}}}:locations:users"
REDIS_CHIEF_LOCATIONS_KEY = "{{shard:{i}}}:locations:chiefs"
REDIS_LOCATION_LAST_UPDATES_KEY = "{{shard:{i}}}:locations:last_updates"

# Simple sharding (for clustering), to distribute the load of location updates and geospatial queries across multiple keys and avoid bottlenecks. 
# With 16 shards, we can have 16 different keys for user locations, 
# which can help with performance when there are many users updating their locations frequently.
# - In CLUSTER mode: The {shard:i} hash tag ensures each shard is mapped to a 
#   specific slot, allowing parallel distribution across multiple nodes.
# - In SINGLE mode: All shards coexist in the same instance. The logic remains 
#   identical, ensuring the code works without modifications regardless of scale.
def get_redis_user_locations_key(uuid: str) -> str:
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % REDIS_TOTAL_SHARDS
    return REDIS_USER_LOCATIONS_KEY.format(i=shard_index)

def get_redis_chief_locations_key(uuid: str) -> str:
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % REDIS_TOTAL_SHARDS
    return REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)

def get_redis_location_last_updates_key(uuid: str) -> str:
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % REDIS_TOTAL_SHARDS
    return REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)

def get_all_redis_user_locations_keys() -> list[str]:
    return [REDIS_USER_LOCATIONS_KEY.format(i=k) for k in range(REDIS_TOTAL_SHARDS)]

def get_all_redis_chief_locations_keys() -> list[str]:
    return [REDIS_CHIEF_LOCATIONS_KEY.format(i=k) for k in range(REDIS_TOTAL_SHARDS)]

def get_all_redis_location_last_updates_keys() -> list[str]:
    return [REDIS_LOCATION_LAST_UPDATES_KEY.format(i=k) for k in range(REDIS_TOTAL_SHARDS)]
