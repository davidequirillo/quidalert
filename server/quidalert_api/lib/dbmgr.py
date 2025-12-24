# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from sqlmodel import create_engine, Session

engine = None

# Initialize the database pool/connection
def init(host, port, db_name, user, password):
    global engine    
    db_url = f"postgresql://{user}:{password}@{host}:{port}/{db_name}"
    engine = create_engine(db_url, echo=True) # echo=True for logging to console
    return engine

# Obtain a session for database operations
def get_session():
    with Session(engine) as session:
        yield session
