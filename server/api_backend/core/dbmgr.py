# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

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

# Simple sharding (for clustering) by first character of the uuid, to distribute the load of location updates and geospatial queries across multiple keys and avoid bottlenecks. 
# With 16 shards, we can have 16 different keys for user locations, 
# which can help with performance when there are many users updating their locations frequently.
def get_redis_user_locations_key(uuid: str) -> str:
    shard_tag = f"{{shard:{uuid[0]}}}"
    return f"{shard_tag}:locations:users"

def get_redis_chief_locations_key(uuid: str) -> str:
    shard_tag = f"{{shard:{uuid[0]}}}"
    return f"{shard_tag}:locations:chiefs"

def get_redis_location_last_updates_key(uuid: str) -> str:
    shard_tag = f"{{shard:{uuid[0]}}}"
    return f"{shard_tag}:locations:last_updates"

def _get_all_shard_keys(suffix: str) -> list[str]:
    """
    Generates a list of keys for all 16 shards (0-f)
    
    This architecture uses logical sharding to ensure 100% compatibility between 
    Single Redis and Redis Cluster modes.

    This is useful for operations that need to access all user locations or all last update timestamps, such as cleanup tasks.
    
    - In CLUSTER mode: The {shard:x} hash tag ensures each shard is mapped to a 
      specific slot, allowing parallel distribution across multiple nodes.
    - In SINGLE mode: All shards coexist in the same instance. The logic remains 
      identical, ensuring the code works without modifications regardless of scale.
    """
    keys = []
    for i in range(16):
        shard_id = f"{i:x}" # Python construct to convert integer to hexadecimal (10 -> 'a', 11 -> 'b', ..., 15 -> 'f')
        # The {{shard:{shard_id}}} syntax creates the Redis Hash Tag
        keys.append(f"{{shard:{shard_id}}}:{suffix}")
    return keys

def get_all_redis_user_locations_keys() -> list[str]:
    return _get_all_shard_keys("locations:users")

def get_all_redis_chief_locations_keys() -> list[str]:
    return _get_all_shard_keys("locations:chiefs")

def get_all_redis_location_last_updates_keys() -> list[str]:
    return _get_all_shard_keys("locations:last_updates")
