#!/usr/bin/env python3

# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import os
from dotenv import load_dotenv
import uvicorn
import api
import config

app = api.app

if (__name__ ==  "__main__") and (config.APP_MODE != "production"):
    load_dotenv()
    
    h = os.environ["HOST"]
    p = int(os.environ["PORT"])
    lev = os.environ["SERVER_LOG_LEVEL"]
    w = int(os.environ["WORKERS"])
    r = os.environ.get("RELOAD", "False").lower() in ("true", "1", "yes")
    
    fn = os.path.basename(__file__)
    sname = os.path.splitext(fn)[0]
    print(f"Starting api server in development mode on {h}:{p}...")
    uvicorn.run(f"{sname}:app", host=h, port=p, 
        log_level=lev, reload=r, workers=w)