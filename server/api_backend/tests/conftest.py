# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from start import app
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session, StaticPool
from dependencies import get_db_session

import logging

logging.getLogger("sqlalchemy.engine").setLevel(logging.WARNING)
logging.getLogger("uvicorn.access").setLevel(logging.WARNING)

# Engine for testing, using in-memory SQLite database
sqlite_url = "sqlite:///:memory:"
engine_test = create_engine(
    sqlite_url, 
    connect_args={"check_same_thread": False},
    poolclass=StaticPool,
    echo=False
)

@pytest.fixture(name="db_session")
def db_session_fixture():
    # Create all tables in the test database
    SQLModel.metadata.create_all(engine_test)
    # Yield a session to be used in tests
    with Session(engine_test) as session:
        yield session
    # Drop all tables after the tests are done
    SQLModel.metadata.drop_all(engine_test)

@pytest.fixture(name="client")
def client_fixture(db_session: Session):
    # Definition of the "fake" function
    # It doesn't matter what the original does, FastAPI will use THIS one instead of the original:
    def get_db_session_override():
        yield db_session
    # 1. Override the dependency in the app with our "fake" function
    app.dependency_overrides[get_db_session] = get_db_session_override
    # 2. Override for app state of the App (useful for background task testing)
    # Save the original engine to restore it later
    original_db_engine = getattr(app.state, "db_engine", None)
    app.state.db_engine = engine_test
    with TestClient(app) as client:
        yield client
    # IMPORTANT: restore the original engine after the test
    app.state.db_engine = original_db_engine
    # IMPORTANT: clean up the override after the test
    app.dependency_overrides.clear()
