# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2025-2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from typing import Union, TypeAlias
import zlib
from sqlmodel import create_engine, Session
import redis.asyncio as redis
import redis.asyncio.cluster as cluster
from core.settings import settings
from models.general import UserRole

## DBMS engine and session management

def get_engine():
    engine = create_engine(settings.db_url, 
        pool_size=settings.db_pool_size,
        max_overflow=settings.db_max_overflow,
        pool_timeout=settings.db_pool_timeout,
        pool_recycle=settings.db_pool_recycle,
        pool_pre_ping=True,
        echo=settings.db_engine_echo)
    return engine

def get_yielded_session(engine):
    with Session(engine) as session:
        yield session

## REDIS connection management (asyncio version)

RedisHandle: TypeAlias = Union[redis.ConnectionPool, cluster.RedisCluster]
RedisConnection: TypeAlias = Union[redis.Redis, cluster.RedisCluster]

class RedisHandleTypeError(ValueError):
    def __init__(self, handle: object):
        self.message = f"Invalid Redis handle type: {type(handle)}. Expected ConnectionPool or RedisCluster."
        super().__init__(self.message)

def get_redis_handle() -> RedisHandle:
    if settings.redis_mode == "cluster":
        return get_redis_cluster_client()
    else:
        return get_redis_pool()

def get_redis_pool() -> redis.ConnectionPool:
    redis_pool: redis.ConnectionPool = redis.ConnectionPool.from_url(
        settings.redis_url, 
        max_connections=settings.redis_max_connections,
        socket_connect_timeout=5,  # seconds
        # Note: socket_timeout is very long because of some periodic tasks 
        # (that may take a long time to complete in the worst case, e.g., some cleanup tasks)
        socket_timeout=1200,  # seconds
        health_check_interval=60,  # seconds
        decode_responses=True)
    return redis_pool
    
def get_redis_cluster_client() -> cluster.RedisCluster:
    nodes_raw = settings.redis_cluster_nodes  
    startup_nodes = []
    for node in nodes_raw.split(","):
        host, port = node.split(":")
        startup_nodes.append(cluster.ClusterNode(host=host, port=int(port)))
    options = {
        "startup_nodes": startup_nodes,
        "password": settings.redis_pass,
        "max_connections": settings.redis_max_connections_per_node,
        "socket_connect_timeout": 5,  # seconds
        # Note: socket_timeout is very long because of some periodic tasks 
        # (that may take a long time to complete in the worst case, e.g., some cleanup tasks)
        "socket_timeout": 1200,  # seconds
        "health_check_interval": 60,  # seconds
        "decode_responses": True,
    }
    return cluster.RedisCluster(**options)

def get_redis_conn(handle: RedisHandle) -> RedisConnection:
    if isinstance(handle, cluster.RedisCluster):
        return handle
    elif isinstance(handle, redis.ConnectionPool):
        return redis.Redis(connection_pool=handle, decode_responses=True)
    raise RedisHandleTypeError(handle)

async def ping_redis(handle: RedisHandle):
    try:
        if isinstance(handle, cluster.RedisCluster):
            return await handle.ping() # type:ignore            
        elif isinstance(handle, redis.ConnectionPool):
            async with get_redis_conn(handle) as redis_session:
                res = await redis_session.ping() # type:ignore
            return res
        else:
            raise RedisHandleTypeError(handle)
    except Exception as e:
        print(f"Error pinging Redis: {e}")
        return False
    
async def shutdown_redis_handle(handle: RedisHandle):
    if isinstance(handle, cluster.RedisCluster):
        await handle.aclose()
    elif isinstance(handle, redis.ConnectionPool):
        await handle.disconnect()
    else:
        raise RedisHandleTypeError(handle)

## REDIS data management: logic sharding, 
# useful to distribute data across multiple keys and avoid bottlenecks.

def get_redis_shards_num() -> int:
    return settings.redis_logical_shards_num

# Note: ideally the Redis cluster size (number of Redis nodes) should be equal to get_redis_shards_num(),
# but it works fine even in a cluster with fewer nodes (or even in Redis single mode), 
# as the shards will be distributed across the available nodes.
REDIS_MUTEX_CHIEF_UPDATE_KEY = "{shard:0}:mutexes:chief_update"
REDIS_COOLDOWN_LOCATIONS_CLEANUP_KEY = "{shard:0}:cooldowns:locations_cleanup"
REDIS_COOLDOWN_LOCATIONS_CLEANUP_TIMEOUT = 3600  # 1 hour in seconds
REDIS_COOLDOWN_DEMOTIONS_CLEANUP_KEY = "{shard:0}:cooldowns:demotions_cleanup"
REDIS_COOLDOWN_DEMOTIONS_CLEANUP_TIMEOUT = 3600 * 24 * 30  # 1 month in seconds
REDIS_COOLDOWN_USERS_CLEANUP_KEY = "{shard:0}:cooldowns:users_cleanup"
REDIS_COOLDOWN_USERS_CLEANUP_TIMEOUT = 3600 * 24  # 1 day in seconds
REDIS_COOLDOWN_ALERTS_CLEANUP_KEY = "{shard:0}:cooldowns:alerts_cleanup"
REDIS_COOLDOWN_ALERTS_CLEANUP_TIMEOUT = 3600 * 24  # 1 day in seconds
REDIS_USER_LOCATIONS_KEY = "{{shard:{i}}}:locations:users"
REDIS_CHIEF_LOCATIONS_KEY = "{{shard:{i}}}:locations:chiefs"
REDIS_LOCATION_LAST_UPDATES_KEY = "{{shard:{i}}}:locations:last_updates"
REDIS_CHIEF_DEMOTIONS_KEY = "{{shard:{i}}}:demotions:chiefs"
# Location keys for specialists (users with a specific role)
REDIS_SPEC_LOCATIONS_KEY = "{{shard:{i}}}:locations:roles:{role}"
REDIS_SPEC_LOCATION_LAST_UPDATES_KEY = "{{shard:{i}}}:locations:last_updates:roles:{role}"

# Simple sharding (for clustering), to distribute the load of location updates and geospatial queries across multiple keys and avoid bottlenecks. 
# With 16 shards, we can have 16 different keys for user locations, 
# which can help with performance when there are many users updating their locations frequently.
# - In CLUSTER mode: The {shard:i} hash tag ensures each shard is mapped to a 
#   specific slot, allowing parallel distribution across multiple nodes.
# - In SINGLE mode: All shards coexist in the same instance. The logic remains 
#   identical, ensuring the code works without modifications regardless of scale.

def get_redis_user_locations_key(uuid: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_USER_LOCATIONS_KEY.format(i=shard_index)

def get_redis_chief_locations_key(uuid: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)

def get_redis_location_last_updates_key(uuid: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)

def get_redis_chief_demotions_key(uuid: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_CHIEF_DEMOTIONS_KEY.format(i=shard_index)

def get_all_redis_user_locations_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_USER_LOCATIONS_KEY.format(i=k) for k in range(shards_num)]

def get_all_redis_chief_locations_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_CHIEF_LOCATIONS_KEY.format(i=k) for k in range(shards_num)]

def get_all_redis_location_last_updates_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_LOCATION_LAST_UPDATES_KEY.format(i=k) for k in range(shards_num)]

def get_all_redis_chief_demotions_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_CHIEF_DEMOTIONS_KEY.format(i=k) for k in range(shards_num)]

# Functions for specialist locations and last updates keys, sharded by user UUID and role
# Specialist locations are for users with a specific role (e.g., firefighters, medics, etc.), 
# and we want to manage their locations separately in Redis.

def get_redis_spec_locations_key(uuid: str, role: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_SPEC_LOCATIONS_KEY.format(i=shard_index, role=role)

def get_redis_spec_location_last_updates_key(uuid: str, role: str) -> str:
    shards_num = settings.redis_logical_shards_num
    data_bytes = uuid.encode('utf-8')
    hash_value = zlib.crc32(data_bytes) # hash value is a 32-bit unsigned integer
    shard_index = hash_value % shards_num
    return REDIS_SPEC_LOCATION_LAST_UPDATES_KEY.format(i=shard_index, role=role)

def get_all_redis_spec_locations_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    keys = []
    for k in range(shards_num):
        for role in [r.value for r in UserRole]:
            keys.append(REDIS_SPEC_LOCATIONS_KEY.format(i=k, role=role))
    return keys

def get_all_redis_spec_location_last_updates_keys() -> list[str]:
    shards_num = settings.redis_logical_shards_num
    keys = []
    for k in range(shards_num):
        for role in [r.value for r in UserRole]:
            keys.append(REDIS_SPEC_LOCATION_LAST_UPDATES_KEY.format(i=k, role=role))
    return keys

def get_all_redis_spec_locations_keys_for_a_role(role: str) -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_SPEC_LOCATIONS_KEY.format(i=k, role=role) for k in range(shards_num)]

def get_all_redis_spec_location_last_updates_keys_for_a_role(role: str) -> list[str]:
    shards_num = settings.redis_logical_shards_num
    return [REDIS_SPEC_LOCATION_LAST_UPDATES_KEY.format(i=k, role=role) for k in range(shards_num)]
