# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import random
from datetime import timedelta
from sqlmodel import Session, select, delete
from fakeredis.aioredis import FakeRedis
from core.dbmgr import (
    REDIS_COOLDOWN_USERS_CLEANUP_TIMEOUT
)
from models.general import (
    User, Alert, AlertedUser, Message, WhiteListEntry
)
from services.periodics import (
    USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS,
    USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS,
    do_users_cleanup
)
from services.security import now_tz_naive 
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture automatically called)
    setup_alerts_data_and_teardown # required (fixture automatically called)
)

def test_clean_old_users_empty_table(db_session: Session, redis_session: FakeRedis):
    # To simulate an empty users table, we delete all users from the database
    statement = delete(User)
    db_session.exec(statement)
    db_session.commit()
    # Now we call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Since there are no users in the database, 
    # the deactivated_num and del_num should be 0
    assert deact_num == 0
    assert del_num == 0

def test_clean_old_users_no_users_in_pending_deletion(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User)).all()
    # See setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We assert that none of the users in the database is in pending deletion,
    # and all users are active
    for user in users:
        assert user.pending_delete_since is None
        assert user.is_active == True
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Since there are no users in pending deletion in the database, the deactivated_num and del_num should be 0
    assert deact_num == 0
    assert del_num == 0

def test_clean_old_users_one_user_in_recent_pending_deletion(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User).where(User.is_admin==False, User.is_officer==False)).all()
    # See setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We set the pending_delete_since of a random user to a recent datetime.
    # If pending_delete_since is set to a recent date, 
    # the periodic function doesn't inactivate the user,
    # because the user is not yet old enough to be inactivated
    user = random.choice(users)
    user.pending_delete_since = now_tz_naive() - timedelta(days=1)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    assert deact_num == 0
    assert del_num == 0

def test_clean_old_users_one_user_in_pending_deletion_since_enough_time(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User).where(User.is_admin==False, User.is_officer==False)).all()
    # See setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We set the pending_delete_since of a random user to be older than USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS,
    # so that user will be deactivated (not deleted yed) by the periodic cleanup function
    user = random.choice(users)
    user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Deactivated_num should be 1 and del_num should be 0.
    # Pending deletion state remains, and the user is deactivated, but not yet deleted
    assert deact_num == 1
    assert del_num == 0
    db_session.refresh(user)
    assert user.pending_delete_since is not None
    assert user.is_active == False
    # With deactivation, user sensible data except email (phone, address, name) is anonymized, but the user is not yet deleted from the database
    assert user.firstname == "Unknown firstname"
    assert user.surname == "Unknown surname"
    assert user.phone == "0000000000"
    assert user.street == "Unknown street"
    assert user.city == "Unknown city"
    alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
    for alert in alerts:
        assert "removed" in alert.description
        if alert.address:
            assert "Unknown" in alert.address
    messages = db_session.exec(select(Message).where(Message.user_id == user.id)).all()
    for message in messages:
        assert "removed" in message.content
    # No user is deleted yet, because the user is not yet old enough to be deleted
    statement = select(User).where(User.is_admin==False, User.is_officer==False)
    users_after_cleanup = db_session.exec(statement).all()
    assert len(users_after_cleanup) == len(users)

def test_clean_old_users_one_user_in_pending_deletion_but_already_not_active(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User).where(User.is_admin==False, User.is_officer==False)).all()
    # See setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We set the pending_delete_since of a random user to be older than USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS
    # and we simulate that the user has already been deactivated in the past,
    # so the periodic function doesn't inactivate the user again
    user = random.choice(users)
    user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
    user.is_active = False
    db_session.add(user)
    db_session.commit()
    db_session.refresh(user)
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # The user is in pending deletion since enough time in the database, 
    # but the user is already inactive, so the deactivated_num should be 0 and del_num should be 0.
    assert deact_num == 0
    assert del_num == 0

def test_clean_old_users_some_users_in_pending_deletion(db_session: Session, redis_session: FakeRedis):
    # We select user ids of users that posted alert or alert messages,
    # so at the end of the test we can check that the anonymization 
    # of alerts and messages related to the deactivated users has been performed correctly
    user_ids = []
    statement = select(Message.user_id)
    message_user_ids = db_session.exec(statement).all()
    user_ids.extend(message_user_ids)
    statement = select(Alert.user_id)
    alert_user_ids = db_session.exec(statement).all()
    user_ids.extend(alert_user_ids)
    user_ids = list(set(user_ids))
    users_to_deact_stmt = select(User).where(User.id.in_(user_ids)) # type: ignore
    users_to_deact = db_session.exec(users_to_deact_stmt).all()
    # There are for sure some users that posted alert messages in the database (see setup_alert_data fixture)
    assert len(users_to_deact) >= 10
    # Now we simulate these users to be in pending deletion status since enough time
    # and we assert that they are active, so they will be deactivated by the cleanup function
    for user in users_to_deact:
        user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
        assert user.is_active == True
        db_session.add(user)
    db_session.commit()
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Deactivated_num should be equal to the number of users in pending deletion since enough time, and del_num should be 0,
    # because the system doesn't delete them at this stage (only deactivate them)
    assert deact_num == len(users_to_deact)
    assert del_num == 0
    # We check that the users in pending deletion since enough time have been deactivated and anonymized, but not yet deleted from the database
    for user in users_to_deact:
        db_session.refresh(user)
        assert user.pending_delete_since is not None
        assert user.is_active == False
        assert user.firstname == "Unknown firstname"
        assert user.surname == "Unknown surname"
        assert user.phone == "0000000000"
        assert user.street == "Unknown street"
        assert user.city == "Unknown city"
        # We verify the anonymization of alerts and messages related to user
        alerts = db_session.exec(select(Alert).where(Alert.user_id == user.id)).all()
        for alert in alerts:
            assert "removed" in alert.description
            if alert.address:
                assert "Unknown" in alert.address
        messages = db_session.exec(select(Message).where(Message.user_id == user.id)).all()
        for message in messages:
            assert "removed" in message.content

def test_clean_old_users_one_user_to_destroy(db_session: Session, redis_session: FakeRedis):
    statement = select(User).where(User.is_admin == False, User.is_officer == False)
    users = db_session.exec(statement).all()
    # See setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We select a random user from the resulting list 
    user = random.choice(users)
    user_email = user.email
    user_id = user.id
    # We simulate that there is a whitelist entry related to the user, so that we can check that it is deleted when the user is destroyed
    # (the setup users fixture doesn't create any whitelist entries related to test users, so we create one here)
    whitelist_entry = WhiteListEntry(email=user_email, created_at=now_tz_naive(), created_by="superuser@example.com")
    db_session.add(whitelist_entry)
    db_session.commit()
    # We check that the whitelist entry has been added to the database
    whitelist_entry_after_add = db_session.exec(select(WhiteListEntry).where(WhiteListEntry.email == user_email)).first()
    assert whitelist_entry_after_add is not None
    # We set the pending_delete_since of the selected user to be older than USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS
    # and we simulate that the user has been deactivated after enough pending deletion time, 
    # so that the user is eligible for destruction
    user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS + 1)
    user.is_active = False
    db_session.add(user)
    db_session.commit()   
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Deactivated_num should be 0 and del_num should be 1, 
    # so the user has been destroyed from the database because it was too old
    assert deact_num == 0
    assert del_num == 1
    # We check that the user has been destroyed from the database
    user_after_cleanup = db_session.exec(select(User).where(User.id == user_id)).first()
    assert user_after_cleanup is None
    # We check that the related alerts, alerted users, messages related to the destroyed user have been destroyed from the database
    alerts_after_cleanup = db_session.exec(select(Alert).where(Alert.user_id == user_id)).all()
    assert len(alerts_after_cleanup) == 0
    alerted_users_after_cleanup = db_session.exec(select(AlertedUser).where(AlertedUser.user_id == user_id)).all()
    assert len(alerted_users_after_cleanup) == 0
    messages_after_cleanup = db_session.exec(select(Message).where(Message.user_id == user_id)).all()
    assert len(messages_after_cleanup) == 0
    # We check that the whitelist entry related to the destroyed user has been destroyed from the database
    whitelist_entry_after_cleanup = db_session.exec(select(WhiteListEntry).where(WhiteListEntry.email == user_email)).all()
    assert len(whitelist_entry_after_cleanup) == 0
    # The number of users in the database should be one less than before, because one user has been destroyed from the database
    users_after_cleanup = db_session.exec(select(User).where(User.is_admin == False, User.is_officer == False)).all()
    assert len(users_after_cleanup) == len(users) - 1

def test_clean_old_users_some_users_to_destroy(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User)).all()
    # see setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We select user ids of users that posted alert or alert messages,
    # so at the end of the test we can check that the cascading deletion (see models/general.py) 
    # of alerts, alerted users, messages related to the destroyed users has been performed correctly
    user_ids = []
    statement = select(Message.user_id)
    message_user_ids = db_session.exec(statement).all()
    user_ids.extend(message_user_ids)
    statement = select(Alert.user_id)
    alert_user_ids = db_session.exec(statement).all()
    user_ids.extend(alert_user_ids)
    user_ids = list(set(user_ids))
    users_to_destroy_stmt = select(User).where(User.id.in_(user_ids)).where(User.is_admin == False, User.is_officer == False) # type: ignore
    users_to_destroy = db_session.exec(users_to_destroy_stmt).all()
    users_to_destroy_ids = [user.id for user in users_to_destroy]
    users_to_destroy_emails = [user.email for user in users_to_destroy]
    # There are for sure some users that posted alert messages in the database (see setup_alert_data fixture)
    assert len(users_to_destroy) >= 10
    # We insert a whitelist entry for each user to destroy, so that we can check that they are deleted when the users are destroyed
    for email in users_to_destroy_emails:
        whitelist_entry = WhiteListEntry(email=email, created_at=now_tz_naive(), created_by="superuser@example.com")
        db_session.add(whitelist_entry)
    db_session.commit()
    # We check that the whitelist entries have been added to the database
    whitelist_entries_after_add = db_session.exec(select(WhiteListEntry).where(WhiteListEntry.email.in_(users_to_destroy_emails))).all() # type: ignore
    assert len(whitelist_entries_after_add) == len(users_to_destroy_emails)
    # Now we make these users to be in pending deletion status since too much time, 
    # and we simulate that they have already been deactivated after enough pending deletion time
    # so that they are eligible for destruction
    for user in users_to_destroy:
        user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS + 1)
        user.is_active = False
        db_session.add(user)
    db_session.commit()
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Deactivated_num should be 0 and del_num should be equal to the number of users in pending deletion since too much time
    assert deact_num == 0
    assert del_num == len(users_to_destroy)
    # We check that the users in pending deletion since too much time have been destroyed from the database
    # and also the alerts, alerted users, messages, and whitelist entries related to the destroyed users have been destroyed from the database
    statement = select(User).where(User.id.in_(users_to_destroy_ids)) # type: ignore
    users_after_cleanup = db_session.exec(statement).all()
    assert len(users_after_cleanup) == 0
    statement = select(Alert).where(Alert.user_id.in_(users_to_destroy_ids)) # type: ignore
    alerts_after_cleanup = db_session.exec(statement).all()
    assert len(alerts_after_cleanup) == 0
    statement = select(AlertedUser).where(AlertedUser.user_id.in_(users_to_destroy_ids)) # type: ignore
    alerted_users_after_cleanup = db_session.exec(statement).all()
    assert len(alerted_users_after_cleanup) == 0
    statement = select(Message).where(Message.user_id.in_(users_to_destroy_ids)) # type: ignore
    messages_after_cleanup = db_session.exec(statement).all()
    assert len(messages_after_cleanup) == 0
    statement = select(WhiteListEntry).where(WhiteListEntry.email.in_(users_to_destroy_emails)) # type: ignore
    whitelist_entries_after_cleanup = db_session.exec(statement).all()
    assert len(whitelist_entries_after_cleanup) == 0
    # We check that the number of users in the database is equal to the number of users before the cleanup minus the number of destroyed users
    users_after_cleanup = db_session.exec(select(User)).all()
    assert len(users_after_cleanup) == len(users) - len(users_to_destroy)

def test_clean_old_users_one_user_to_deactivate_and_one_to_destroy(db_session: Session, redis_session: FakeRedis):
    users = db_session.exec(select(User).where(User.is_admin == False, User.is_officer == False)).all()
    # see setup_users_data fixture from tests/fixtures/alerts.py, which creates some users in the database for testing
    assert len(users) > 0
    # We select two random users from the resulting list
    # One user will be deactivated (because it is in pending deletion since enough time, but not yet old enough to be destroyed)
    # The other user will be destroyed (because it is in pending deletion since too much time, and already deactivated)
    user_to_deactivate = random.choice(users)
    user_to_destroy = random.choice([user for user in users if user.id != user_to_deactivate.id])
    user_to_deactivate.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
    user_to_destroy.pending_delete_since = now_tz_naive() - timedelta(days=USER_DESTRUCTION_AFTER_PENDING_DELETE_DAYS + 1)
    user_to_deactivate.is_active = True
    user_to_destroy.is_active = False
    db_session.add(user_to_deactivate)
    db_session.add(user_to_destroy)
    db_session.commit()
    db_session.refresh(user_to_deactivate)
    db_session.refresh(user_to_destroy)
    user_to_destroy_id = user_to_destroy.id
    user_to_destroy_email = user_to_destroy.email
    # We call the do_users_cleanup function (periodic task)
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    # Deactivated_num should be 1 and del_num should be 1
    assert deact_num == 1
    assert del_num == 1
    # We check that the user to deactivate has been deactivated and anonymized (except email), but not yet destroyed from the database
    # and all the alerts and messages related to the deactivated user have been anonymized
    db_session.refresh(user_to_deactivate)
    assert user_to_deactivate.pending_delete_since is not None
    assert user_to_deactivate.is_active == False
    assert user_to_deactivate.firstname == "Unknown firstname"
    assert user_to_deactivate.surname == "Unknown surname"
    assert user_to_deactivate.phone == "0000000000"
    assert user_to_deactivate.street == "Unknown street"
    statement = select(Alert).where(Alert.user_id == user_to_deactivate.id)
    alerts_after_cleanup = db_session.exec(statement).all()
    for alert in alerts_after_cleanup:
        assert "removed" in alert.description
        if alert.address:
            assert "Unknown" in alert.address
    statement = select(Message).where(Message.user_id == user_to_deactivate.id)
    messages_after_cleanup = db_session.exec(statement).all()
    for message in messages_after_cleanup:
        assert "removed" in message.content
    # We check that the user to destroy has been destroyed from the database,
    # and all the alerts, alerted users, messages, and whitelist entries related to the destroyed user have been destroyed from the database
    user_to_destroy_after_cleanup = db_session.exec(select(User).where(User.id == user_to_destroy_id)).first()
    assert user_to_destroy_after_cleanup is None
    statement = select(Alert).where(Alert.user_id == user_to_destroy_id)
    alerts_after_cleanup = db_session.exec(statement).all()
    assert len(alerts_after_cleanup) == 0
    statement = select(AlertedUser).where(AlertedUser.user_id == user_to_destroy_id)
    alerted_users_after_cleanup = db_session.exec(statement).all()
    assert len(alerted_users_after_cleanup) == 0
    statement = select(Message).where(Message.user_id == user_to_destroy_id)
    messages_after_cleanup = db_session.exec(statement).all()
    assert len(messages_after_cleanup) == 0
    statement = select(WhiteListEntry).where(WhiteListEntry.email == user_to_destroy_email)
    whitelist_entries_after_cleanup = db_session.exec(statement).all()
    assert len(whitelist_entries_after_cleanup) == 0

def test_clean_old_users_lock_already_acquired(db_session: Session, redis_session: FakeRedis, frozen_now):
    # We simulate that some users in the database are in pending deletion since enough time,
    # so that they will be deactivated by the cleanup function
    users = db_session.exec(select(User).where(User.is_admin == False, User.is_officer == False)).all()
    assert len(users) > 0
    for user in users:
        user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
        db_session.add(user)
    db_session.commit()
    # Now we call the do_users_cleanup function (periodic task) for the first time, 
    # and it should acquire the lock and perform the cleanup
    db_engine = db_session.get_bind()
    deact_num, _ = do_users_cleanup(db_engine, redis_session)
    assert deact_num > 0
    # Now we reset the active status of the same users to re-activate them (to make them eligible for deactivation)
    # and we set pending delete status of the same users to True
    for user in users:
        user.pending_delete_since = now_tz_naive() - timedelta(days=USER_DEACTIVATION_AFTER_PENDING_DELETE_DAYS + 1)
        user.is_active = True
        db_session.add(user)
    db_session.commit()
    # Now we call the do_users_cleanup function (periodic task) for the second time,
    # and it should not acquire the lock, because the lock is in cooldown (already acquired by the first call), 
    # so the cleanup is not executed
    db_engine = db_session.get_bind()
    deact_num, del_num = do_users_cleanup(db_engine, redis_session)
    assert deact_num == 0
    assert del_num == 0
    # Now, we try to simulate the time passing, so that the lock is released and the cleanup can be executed again
    frozen_now.tick(delta=timedelta(seconds=REDIS_COOLDOWN_USERS_CLEANUP_TIMEOUT + 1))
    # Now we call the do_users_cleanup function (periodic task) for the third time,
    # and it should acquire the lock, because the lock is no longer in cooldown,
    # so the cleanup is executed again
    db_engine = db_session.get_bind()
    deact_num, _ = do_users_cleanup(db_engine, redis_session)
    assert deact_num > 0
