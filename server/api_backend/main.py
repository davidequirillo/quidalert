#!/usr/bin/env python3

# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2025-2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import api

app = api.app

# This file is not meant to be executed directly, 
# but it is used by the Dockerfile to start the FastAPI application.
if (__name__ ==  "__main__"):
    pass
