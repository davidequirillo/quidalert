# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
import redis.asyncio as redis
from sqlmodel import Session, select
from models.general import Alert, User
from core.tasks_events import log_alert_notify_nearby_users

def notify_nearby_users(
        alert: Alert, user: User, request_info: dict,
        db_engine, redis_pool):
    if alert.is_closed:
        return
    async def get_nearby_chief_and_users():
        async with redis.Redis(connection_pool=redis_pool, decode_responses=True) as redis_client:
            pass
            # todo: get nearby users from redis, then notify them (e.g. via websocket or push notification)
    asyncio.run(get_nearby_chief_and_users())  
    with Session(db_engine) as session:
        pass
        # statement = select(User).where..............)
        # user = session.exec(statement).first(
        # ....
        #
    log_alert_notify_nearby_users(str(alert.id), request_info)