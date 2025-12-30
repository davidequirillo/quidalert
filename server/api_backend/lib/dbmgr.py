# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import create_engine, Session

def get_engine(db_url):
    engine = create_engine(db_url, echo=True) # echo=True for logging to console
    return engine

def get_session(engine):
    with Session(engine) as session:
        yield session
