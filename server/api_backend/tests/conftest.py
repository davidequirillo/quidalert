# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from start import app
import pytest
from fastapi.testclient import TestClient
from sqlmodel import SQLModel, create_engine, Session, StaticPool
from models.general import User, UserRole, RefreshToken
from dependencies import get_db_session
from services.security import (
    create_access_token, 
    create_refresh_token,
    create_geoposition_token,
    create_login_token,
    generate_random_token,
    get_token_hash,
    activation_expiry, now_tz_naive)
from core.settings import settings
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
    # Override some settings for testing
    original_app_mode = settings.app_mode
    settings.app_mode = "testing"
    # Override the dependency in the app with our "fake" function
    app.dependency_overrides[get_db_session] = get_db_session_override
    # Override app state (useful for background task testing)
    # Save the original engine to restore it later
    original_db_engine = getattr(app.state, "db_engine", None)
    app.state.db_engine = engine_test
    with TestClient(app) as client:
        try:
            yield client
        finally:
            # IMPORTANT: restore the original engine after the test
            app.state.db_engine = original_db_engine
            # IMPORTANT: clean up the override after the test
            app.dependency_overrides.clear()
            # Restore original settings
            settings.app_mode = original_app_mode

def create_test_logged_user(user_type, db_session: Session):
    test_user = User.model_validate({
        "firstname": "Firstname1",
        "surname": "Surname1",
        "email": f"test_{user_type}@example.com",
        "language": "en",
        "password_hash": "fakehashedpassword!ABC123",
        "is_superuser": False,
        "is_admin": (user_type == "admin"),
        "is_chief": (user_type == "chief"),
        "is_officer": (user_type == "officer"),
        "role": UserRole.citizen.value,
        "is_active": True,
        "activation_code": "fakeacttoken",
        "activation_code_expires_at": activation_expiry(),
        "authorized_by": "superuser@example.com",
        "authorized_at": now_tz_naive(),
    })
    now = now_tz_naive()
    test_user.last_login_done_at = now
    test_user.last_refresh_at = now
    db_session.add(test_user)
    db_session.commit()
    db_session.refresh(test_user)
    raw_random_str = generate_random_token()
    raw_str_hash = get_token_hash(raw_random_str)
    refresh_token = RefreshToken(
        user_id=test_user.id,
        raw_hash=raw_str_hash,
        ip_address=None,
        device_info=None,
        updated_at=now
    )
    db_session.add(refresh_token)
    db_session.commit()
    db_session.refresh(refresh_token)
    atoken = create_access_token(str(test_user.id))
    rtoken = create_refresh_token(
        str(test_user.id), str(refresh_token.id), 
        raw_random_str, created_at=now)
    gps_token = create_geoposition_token(
        str(test_user.id), test_user.is_chief, test_user.role)
    login_token = create_login_token(str(test_user.id))
    return {
        "user": test_user,
        "access_token": atoken,
        "refresh_token": rtoken,
        "gps_token": gps_token,
        "login_token": login_token,
    }

@pytest.fixture(name="test_baseuser")
def create_test_baseuser(db_session: Session):
    return create_test_logged_user("baseuser", db_session)

@pytest.fixture(name="test_admin")
def create_test_admin(db_session: Session):
    return create_test_logged_user("admin", db_session)

@pytest.fixture(name="test_chief")
def create_test_chief(db_session: Session):
    return create_test_logged_user("chief", db_session)

@pytest.fixture(name="test_officer")
def create_test_officer(db_session: Session):
    return create_test_logged_user("officer", db_session)

