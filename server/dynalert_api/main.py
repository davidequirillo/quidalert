#!/usr/bin/env python3

# Dynalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from etc import dev_config
import config 
import sys
import os
import uvicorn
import api

class AppConfig:
    is_development = False
    server_name = ""
    server_port = 0
    app_log_level = ""

app = api.app

if __name__ ==  "__main__":
    AppConfig.is_development = True
    AppConfig.server_name = dev_config.HOST
    AppConfig.server_port = dev_config.PORT
    AppConfig.app_log_level = dev_config.APP_LOG_LEVEL
else:
    AppConfig.is_development = False
    AppConfig.server_name = config.SERVER_NAME
    AppConfig.server_port = config.SERVER_PORT
    AppConfig.app_log_level = config.APP_LOG_LEVEL

if AppConfig.is_development:
    fn = os.path.basename(__file__)
    sname = os.path.splitext(fn)[0]
    print(f"Starting api server in development mode on {dev_config.HOST}:{dev_config.PORT}...")
    uvicorn.run(f"{sname}:app", 
        host=dev_config.HOST, port=dev_config.PORT, 
        log_level=dev_config.SERVER_LOG_LEVEL, reload=True,
        workers=dev_config.WORKERS)

sys.exit(0)
