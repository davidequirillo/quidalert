#!/usr/bin/env python3

# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from dotenv import load_dotenv
import config 
import sys
import os
import uvicorn
import api
from lib import dbmgr

class AppConfig:
    is_development = False
    server_name = ""
    server_port = 0
    app_log_level = ""

load_dotenv()
app = api.app

if __name__ ==  "__main__":
    AppConfig.is_development = True
    AppConfig.server_name = os.environ["HOST"]
    AppConfig.server_port = int(os.environ["PORT"])
    AppConfig.app_log_level = os.environ["APP_LOG_LEVEL"]
else:
    AppConfig.is_development = False
    AppConfig.server_name = config.SERVER_NAME
    AppConfig.server_port = config.SERVER_PORT
    AppConfig.app_log_level = config.APP_LOG_LEVEL

dbmgr.init()

if AppConfig.is_development:
    h = AppConfig.server_name
    p = AppConfig.server_port
    lev = AppConfig.app_log_level
    w = int(os.environ["WORKERS"])

    fn = os.path.basename(__file__)
    sname = os.path.splitext(fn)[0]
    print(f"Starting api server in development mode on {h}:{p}...")
    uvicorn.run(f"{sname}:app", host=h, port=p, 
        log_level=lev, reload=True, workers=w)

sys.exit(0)
