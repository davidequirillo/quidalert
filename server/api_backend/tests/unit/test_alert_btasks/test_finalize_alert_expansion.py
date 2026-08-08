# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from services.alert_btasks import (
    finalize_alert_expansion
)
from models.general import AlertType
from tests.fixtures.alerts import (
    create_test_alert, # required (fixture test_alert)
    create_test_request_info, # required (fixture test_request_info)
)

def test_finalize_alert_expansion_with_zero_users(db_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    assert test_alert.user_id is not None
    # We check that the alert is in pending status (default status)
    assert test_alert.is_pending == True
    # We simulate that the alert has a spread count of 1,  
    # meaning it has been propagated to nearby users 1 time
    test_alert.spread_count = 1
    db_session.add(test_alert)
    db_session.commit()
    # We simulate that the alert has been spread to 0 users
    users_num = 0
    # Now we call the function to finalize the alert expansion
    finalize_alert_expansion(test_alert.id, users_num, test_request_info, db_session)
    db_session.refresh(test_alert)
    # After the function call, the alert should be set as not pending anymore, 
    # and the spread count should remain the same since no users were notified
    assert test_alert.is_pending == False
    assert test_alert.spread_count == 1

def test_finalize_alert_expansion_with_users(db_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    assert test_alert.user_id is not None
    assert test_alert.type == AlertType.local.value
    # We check that the alert is in pending status (default status)
    assert test_alert.is_pending == True
    # We simulate that the alert has a spread count of 1, 
    # meaning it has been propagated to nearby users 1 time
    test_alert.spread_count = 1
    db_session.add(test_alert)
    db_session.commit()
    # We simulate that the alert has been spread to 5 users
    users_num = 5
    # Now we call the function to finalize the alert expansion
    finalize_alert_expansion(test_alert.id, users_num, test_request_info, db_session)
    db_session.refresh(test_alert)
    # After the function call, the alert should be set as not pending anymore, 
    # and the spread count should be incremented by 1 since some users were notified.
    # Additionally, the alert type should remain unchanged
    assert test_alert.is_pending == False
    assert test_alert.spread_count == 2
    assert test_alert.type == AlertType.local.value  # The alert type should remain unchanged since it was not empty

def test_finalize_alert_expansion_with_empty_alert_type(db_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    assert test_alert.user_id is not None
    # We check that the alert is in pending status (default status)
    assert test_alert.is_pending == True
    # We simulate that the alert has been spread count to 1, 
    # meaning it has been propagated to nearby users 1 time
    test_alert.spread_count = 1
    db_session.add(test_alert)
    db_session.commit()
    # We simulate that the alert has been spread to 3 users
    users_num = 3
    # We set the alert type to empty to simulate an empty alert type scenario
    test_alert.type = AlertType.empty.value
    db_session.add(test_alert)
    db_session.commit()
    # Now we call the function to finalize the alert expansion
    finalize_alert_expansion(test_alert.id, users_num, test_request_info, db_session)
    db_session.refresh(test_alert)
    # After the function call, the alert should be set as not pending anymore, 
    # and the spread count should be incremented by 1 since some users were notified
    # Additionally, the alert type should be updated to "managed" since it was previously "empty"
    assert test_alert.is_pending == False
    assert test_alert.spread_count == 2
    assert test_alert.type == AlertType.managed.value
