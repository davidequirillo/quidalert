# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from datetime import timedelta
from haversine import haversine, Unit
from fakeredis.aioredis import FakeRedis
from services.security import (
    now_tz_aware
)
from core.dbmgr import (
    get_redis_chief_locations_key,
    get_redis_user_locations_key
)
from tests.fixtures.alerts import (
    create_test_alert, 
    create_test_request_info
)
