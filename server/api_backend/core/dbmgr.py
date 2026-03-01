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
    redis_pool = redis.ConnectionPool.from_url(
    settings.redis_url, 
    max_connections=settings.redis_max_connections, 
    decode_responses=True
    )
    return redis_pool

def get_redis_conn(pool):
    return redis.Redis(connection_pool=pool, decode_responses=True)
