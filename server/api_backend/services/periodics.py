# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import asyncio
from datetime import timedelta
from sqlmodel import Session, select, update, delete
from fakeredis.aioredis import FakeRedis
from models.general import (
    WhiteListEntry,
    User, UserLanguage,
    Alert, AlertType,
    Message
)
from services.security import (
    now_tz_aware,
    GEOPOSITION_TOKEN_TTL_MINUTES)
from core.periodic_events import (
    log_cleanup_expired_locations_error,
    log_cleanup_expired_locations_completed,
    log_cleanup_expired_locations_started,
    log_cleanup_expired_demotions_error,
    log_cleanup_expired_demotions_started,
    log_cleanup_chief_demotions_shard,
    log_cleanup_expired_locations_shard,
    log_cleanup_expired_demotions_completed,
    log_cleanup_expired_locations_in_cooldown,
    log_cleanup_expired_demotions_in_cooldown,
    log_cleanup_dismissed_users_started,
    log_cleanup_dismissed_users_error,
    log_cleanup_dismissed_users_completed,
    log_cleanup_old_alerts_started,
    log_cleanup_old_alerts_error,
    log_cleanup_old_alerts_completed
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

LOCATIONS_TTL_HOURS = 48

# Chief demotion expiration threshold: same as geoposition token TTL, 
# since the demotion is linked to the geoposition update and should last as long as the token validity
# note: we add a small grace period of 5 minutes to avoid edge cases of demotions being removed just before the token expires
CHIEF_DEMOTIONS_TTL_MINUTES = GEOPOSITION_TOKEN_TTL_MINUTES + 5

# Expiration thresholds for alerts (for automatic close and delete after a certain time)
ALERT_TTSO_DAYS = 30 # Time to stay open: 30 days
ALERT_TTL_DAYS = 30 * 18 # Time to live: approximately 18 months

# User pending deletion thresholds: 30 days (1 month) for deactivation, 2 years for complete deletion from the database
USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS = 30
USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS = 30 * 24 # 2 years approximately

async def do_locations_cleanup(redis_handle):
    if isinstance(redis_handle, cluster.RedisCluster):
        deleted_count = await cleanup_expired_locations(redis_handle)
        return deleted_count
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            deleted_count = await cleanup_expired_locations(redis_session)
        return deleted_count
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        deleted_count = await cleanup_expired_locations(redis_handle)
        return deleted_count
    else:
        raise RedisHandleTypeError(redis_handle)

async def cleanup_expired_locations(redis_client):
    now = now_tz_aware()
    exp_dt = now - timedelta(hours=LOCATIONS_TTL_HOURS) # expiration threshold: 48 hours
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
        log_cleanup_expired_locations_in_cooldown(
            detail=f"Skipping cleanup, waiting for cooldown"
        )
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

async def cleanup_expired_locations_shard(shard_index, exp_int_ts, redis_client, batch_size=1000):
    deleted_in_shard = 0
    last_upd_key = REDIS_LOCATION_LAST_UPDATES_KEY.format(i=shard_index)
    uloc_key = REDIS_USER_LOCATIONS_KEY.format(i=shard_index)
    chiefloc_key = REDIS_CHIEF_LOCATIONS_KEY.format(i=shard_index)
    log_cleanup_expired_locations_shard(detail=f"Cleaning expired locations for shard {shard_index}")
    while True:
        expired_user_ids = await redis_client.zrange(
            last_upd_key, 
            start = "-inf", 
            end = exp_int_ts, # inclusive range
            byscore=True,
            offset=0,
            num=batch_size
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
        await asyncio.sleep(0.1) # we add a small sleep (in seconds) between each batch to avoid overwhelming the Redis server
    return deleted_in_shard

async def do_demotions_cleanup(redis_handle):
    if isinstance(redis_handle, cluster.RedisCluster):
        deleted_count = await cleanup_expired_demotions(redis_handle)
        return deleted_count
    elif isinstance(redis_handle, redis.ConnectionPool):
        async with redis.Redis(connection_pool=redis_handle, decode_responses=True) as redis_session:
            deleted_count = await cleanup_expired_demotions(redis_session)
        return deleted_count
    elif isinstance(redis_handle, FakeRedis): # for testing purposes with fakeredis
        deleted_count = await cleanup_expired_demotions(redis_handle)
        return deleted_count
    else:
        raise RedisHandleTypeError(redis_handle)

async def cleanup_expired_demotions(redis_client):
    now =  now_tz_aware()
    exp_dt = now - timedelta(minutes=CHIEF_DEMOTIONS_TTL_MINUTES) 
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
        log_cleanup_expired_demotions_in_cooldown(
            detail=f"Skipping cleanup, waiting for cooldown"
        )
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

async def cleanup_expired_demotions_shard(shard_index, exp_int_ts, redis_client, batch_size=1000):
    deleted_in_shard = 0
    demotions_key = REDIS_CHIEF_DEMOTIONS_KEY.format(i=shard_index)
    log_cleanup_chief_demotions_shard(detail=f"Cleaning chief demotions for shard {shard_index}")
    while True:
        expired_user_ids = await redis_client.zrange(
            demotions_key, 
            start = "-inf", 
            end = exp_int_ts, # inclusive range
            byscore=True, 
            offset=0, 
            num=batch_size
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
        await asyncio.sleep(0.1) # we add a small sleep (in seconds) between each batch to avoid overwhelming the Redis server
    return deleted_in_shard

def do_users_cleanup(db_engine):
    """
    This function is called periodically to clean up accounts that have been pending deletion for too long.
    It checks the 'pending_delete_since' field of users and deletes those who have been pending deletion for more than a certain threshold.
    If the period is less than 30 days, nothing happens, and the user can re-login if he changes his mind and wants to keep the account active.
    If the period is 30 days or more (max 2 years), the user is not destroyed from the database, but is deactivated, and his personal data is wiped completely (except the email address), so he becomes "unknown", anonymous, virtually a "deleted" user.
    If the period is longer than 2 years, the deactivated user is destroyed completely from the database with all his related data (alerts, messages, and whitelists entries)
    """
    now = now_tz_aware()
    deactivation_timedelta = timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS)
    destruction_timedelta = timedelta(days=USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS)
    log_cleanup_dismissed_users_started()
    with Session(db_engine) as db_session:
        try:
            users_to_deact_stmt = (select(User)
                .where(User.pending_delete_since != None)
                .where(User.pending_delete_since < (now - deactivation_timedelta)) # type: ignore
                .where(User.is_active == True))
            users_to_destroy_stmt = (select(User.id, User.email)
                .where(User.pending_delete_since != None)
                .where(User.pending_delete_since < (now - destruction_timedelta)) # type: ignore
                .where(User.is_active == False))
            users_to_deact = db_session.exec(users_to_deact_stmt).all()
            users_to_destroy = db_session.exec(users_to_destroy_stmt).all()
            users_to_destroy_ids = [row[0] for row in users_to_destroy]
            users_to_destroy_emails = [row[1] for row in users_to_destroy]
        except Exception as e:
            log_cleanup_dismissed_users_error(detail=str(e))
            return 0, 0
        deleted_count = 0
        deactivated_count = 0
        # We deactivate users in a loop, because we need to anonymize their personal data and update related alerts and messages
        for user in users_to_deact:
            with db_session.begin_nested():
                try:
                    deactivate_user(user, db_session)
                    db_session.flush() # flush the changes to the database before committing
                    deactivated_count += 1
                except Exception as e:
                    log_cleanup_dismissed_users_error(detail=f"Error deactivating user {user.id}: {str(e)}")
        db_session.commit()
        # We delete users in bulk, leaving to the dbms the responsibility of handling foreign key constraints and cascading deletions defined (see models/general.py)
        if users_to_destroy_ids:
            try:
                delete_stmt = delete(User).where(User.id.in_(users_to_destroy_ids)) # type: ignore
                db_session.exec(delete_stmt)
                delete_stmt = delete(WhiteListEntry).where(WhiteListEntry.email.in_(users_to_destroy_emails)) # type: ignore
                db_session.exec(delete_stmt)
                db_session.commit()
                deleted_count = len(users_to_destroy_ids)
            except Exception as e:
                log_cleanup_dismissed_users_error(detail=str(e))
                db_session.rollback()
    log_cleanup_dismissed_users_completed(detail=f"Cleanup completed: {deleted_count} users destroyed, {deactivated_count} users deactivated")
    return deactivated_count, deleted_count

def deactivate_user(user, db_session):
    user.is_active = False
    # Remove personal data (except email)
    user.firstname = "Unknown firstname"
    user.surname = "Unknown surname"
    user.street = "Unknown street"
    user.city = "Unknown city"
    user.province = "Unknown province"
    user.postal_code = "00000"
    user.country = "Unknown country"
    user.phone = "0000000000"
    user.birthdate = None
    user.notes = None
    user.is_superuser = False
    user.is_admin = False
    user.is_officer = False
    user.is_chief = False
    user.language = UserLanguage.en.value
    user.role = None
    user.is_reliable = True
    user.is_blocked = False
    user.reliability_score = 100
    user.last_reliability_score_at = None
    user.last_login_done_at = None
    db_session.add(user)
    # Now we anonymize all alert messages related to this user
    anonymous_msg = "This message has been removed due to account deactivation."
    db_session.exec(update(Message).where(Message.user_id == user.id).values(content=anonymous_msg))
    # We also reset all alert descriptions related to this user
    anonymous_desc = "This alert description has been removed due to account deactivation."
    anonymous_addr = "Unknown address"
    db_session.exec(update(Alert).where(Alert.user_id == user.id).values(description=anonymous_desc, address=anonymous_addr))

def do_alerts_cleanup(db_engine):
    """
    This function is called periodically to clean up old alerts.
    """
    now = now_tz_aware()
    log_cleanup_old_alerts_started(detail=f"Starting cleanup of alerts older than {ALERT_TTL_DAYS} days")
    with Session(db_engine) as db_session:
        try:
            # We close all local open alerts in bulk (that are older than some days)
            statement = (update(Alert)
                .where(Alert.is_closed == False) # type: ignore
                .where(Alert.created_at < (now - timedelta(days=ALERT_TTSO_DAYS))) # type: ignore
                .where(Alert.type == AlertType.local) # type: ignore
                .values(is_closed=True))
            closed_count = db_session.exec(statement).rowcount
            # We delete very old alerts in bulk, leaving to the dbms the responsibility of handling foreign key constraints and cascading deletions defined (see models/general.py)
            statement = delete(Alert).where(Alert.created_at < (now - timedelta(days=ALERT_TTL_DAYS))) # type: ignore
            deleted_count = db_session.exec(statement).rowcount
            db_session.commit()
        except Exception as e:
            log_cleanup_old_alerts_error(detail=str(e))
            return 0, 0
    log_cleanup_old_alerts_completed(detail=f"Cleanup completed: {closed_count} alerts closed, {deleted_count} alerts destroyed")
    return closed_count, deleted_count
