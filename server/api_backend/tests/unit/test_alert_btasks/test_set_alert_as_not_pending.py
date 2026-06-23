# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from services.alert_btasks import (
    set_alert_as_not_pending_anymore,
)
from tests.fixtures.alerts import (
    setup_users_data_and_teardown, # required (fixture setup_users_data_and_teardown)
    create_test_alert, # required (fixture test_alert)
    create_test_request_info, # required (fixture test_request_info)
)

def test_set_alert_as_not_pending_success(db_session, test_alert, test_request_info):
    assert test_alert is not None
    assert test_alert.id is not None
    assert test_alert.user_id is not None
    # We check that the alert is in pending status (default status)
    assert test_alert.is_pending == True
    db_engine = db_session.get_bind()
    set_alert_as_not_pending_anymore(test_alert.id, test_request_info, db_engine)
    db_session.refresh(test_alert) # Refresh the test_alert object to get the updated state from the database
    # After the function call, the alert should be set as not pending anymore
    assert test_alert.is_pending == False
