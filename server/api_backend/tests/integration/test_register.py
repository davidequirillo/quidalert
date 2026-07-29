# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from datetime import timedelta
from sqlmodel import select
from models.general import User, UserLanguage, UserType, UserRole
from core.settings import settings
from services.security import now_tz_naive, ACTIVATION_TOKEN_TTL_HOURS

def test_register_missing_fields(client):
    payload = {"firstname": "John", "surname": "Doe"}
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    errors = response.json()["detail"]
    assert any(err["loc"][-1] == "email" for err in errors)
    assert any(err["loc"][-1] == "password" for err in errors)

def test_register_invalid_email_format(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "name-at-domain.com", # invalid email format
        "password": "Password123!"
    }  
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422
    assert "email" in str(response.json()["detail"]).lower()

def test_register_password_too_short(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "user@test.it",
        "password": "123" # too short password
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422 or response.status_code == 400

def test_register_password_too_simple(client):
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "user@test.it",
        "password": "Password123" # too simple password, without special characters
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code == 422 or response.status_code == 400

def test_register_superuser_with_wrong_password(client, db_session):
    payload = {
        "firstname": "Admin",
        "surname": "Super",
        "email": "admin@example.com",
        "password": "WrongPassword123!" # wrong password for admin
    }
    # Check the database to ensure is empty
    users = db_session.exec(select(User)).all()
    assert len(users) == 0
    # Attempt to register the superuser with the wrong password
    response = client.post("/api/register", json=payload)
    # Check that for the client everything appears "normal"
    assert response.status_code == 200 or response.status_code == 201 or response.status_code == 202
    # Check the database to ensure that no user was created with the admin email
    statement = select(User).where(User.email == "admin@example.com")
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_register_superuser_with_correct_password(client, db_session):
    payload = {
        "firstname": "Admin",
        "surname": "Super",
        "email": "admin@example.com",
        "password": settings.admin_pass
    }
    # Check the database to ensure is empty
    users = db_session.exec(select(User)).all()
    assert len(users) == 0
    # Attempt to register the superuser with the correct password
    response = client.post("/api/register", json=payload)
    assert response.status_code == 200 or response.status_code == 201 or response.status_code == 202
    # Check the database to ensure that the superadmin was created
    statement = select(User).where(User.email == "admin@example.com")
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user = results[0]
    assert user.is_superuser == True
    assert user.is_admin == True
    assert user.authorized_by is None

def test_register_duplicate_superuser(client, db_session, superuser_in_db):
    payload = {
        "firstname": "DupAdmin",
        "surname": "Super",
        "email": superuser_in_db.email,
        "password": settings.admin_pass
    }
    # Check the database to ensure the superuser exists
    users = db_session.exec(select(User).where(User.email == superuser_in_db.email)).all()
    assert len(users) == 1
    # Attempt to register another superuser with the same email
    response = client.post("/api/register", json=payload)   
    # Check that for the client everything appears "normal"
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that no duplicate user was created
    results = db_session.exec(select(User).where(User.email == superuser_in_db.email)).all()
    assert len(results) == 1

def test_register_overwrite_superuser_if_inactive_and_expired(client, db_session, superuser_in_db):
    # Check the database to ensure the superuser exists
    users = db_session.exec(select(User).where(User.email == superuser_in_db.email)).all()
    assert len(users) == 1
    # Modify the superuser to be inactive for too long
    superuser_in_db.activation_expires_at = now_tz_naive() - timedelta(hours=1) # expired token
    db_session.add(superuser_in_db)
    db_session.commit()
    assert superuser_in_db.activation_expires_at < now_tz_naive()
    # Attempt to register a new superuser with the same email
    payload = {
        "firstname": "NewAdmin",
        "surname": "Super",
        "email": superuser_in_db.email,
        "password": settings.admin_pass
    }
    response=client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the old superuser was overwritten  
    statement = select(User).where(User.email == superuser_in_db.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user = results[0]
    assert user.is_superuser == True
    assert user.is_admin == True
    assert user.authorized_by is None
    assert user.activation_code is not None
    assert user.activation_expires_at is not None
    # The new superuser should have a new activation code and expiration time, so they should be different from the old one
    assert user.activation_code != superuser_in_db.activation_code
    assert user.activation_expires_at != superuser_in_db.activation_expires_at
    assert user.activation_expires_at > now_tz_naive()
    assert user.firstname == payload["firstname"]
    assert user.surname == payload["surname"]

def test_register_not_in_whitelist(client, db_session, superuser_in_db):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "john.doe@example.com",
        "password": "MyValidPassword123!"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that no user was created with the email not in the whitelist
    statement = select(User).where(User.email == payload["email"])
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_register_in_whitelist(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": "whitelisted@example.com",
        "password": "MyValidPassword123!",
        "language": UserLanguage.it.value
    }     
    payload["email"] = whitelist_entry.email
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    assert results[0].email == whitelist_entry.email
    assert results[0].firstname == payload["firstname"]
    assert results[0].surname == payload["surname"]
    assert results[0].is_superuser == False
    assert results[0].is_admin == False
    assert results[0].authorized_by == whitelist_entry.created_by # the user should be authorized by the creator of the whitelist entry
    assert results[0].activation_code is not None
    assert results[0].activation_expires_at is not None
    assert results[0].activation_expires_at > now_tz_naive() + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS - 1)
    assert results[0].activation_expires_at <= now_tz_naive() + timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS)
    # Check that the language is set correctly to Italian as specified in the payload
    assert results[0].language == UserLanguage.it.value
    # Check that the pending_delete_since is set correctly (it should be set to now)
    assert results[0].pending_delete_since is not None
    assert results[0].pending_delete_since > now_tz_naive() - timedelta(seconds=5) # the pending_delete_since should be set to now, with a small margin of error
    assert results[0].pending_delete_since < now_tz_naive() + timedelta(seconds=5) # the pending_delete_since should be set to now, with a small margin of error

def test_register_in_whitelist_with_email_uppercase(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    # We also check that the whitelist entry exists with the correct email (lowercase)
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    assert whitelist_entry.email.lower() == whitelist_entry.email
    payload = {
        "firstname": "John",
        "surname": "Doe",
        # This email is in uppercase, but it should still be accepted as valid and converted to lowercase
        "email": whitelist_entry.email.upper(),
        "password": "MyValidPassword123!"
    }
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist (case-insensitive)
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    assert results[0].email == whitelist_entry.email # it should be lowercase
    assert results[0].firstname == payload["firstname"]
    assert results[0].surname == payload["surname"]
    assert results[0].language == UserLanguage.en.value # default language should be English if not specified in the payload

def test_register_duplicate_user(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email,
        "password": "MyValidPassword123!"
    }
    # 1st registration attempt with the email in the whitelist
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # 2nd registration attempt with the same email
    response = client.post("/api/register", json=payload)
    # Check that for the client everything appears "normal"
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that no duplicate user was created with the same email
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    assert results[0].email == whitelist_entry.email

def test_register_overwrite_user_if_inactive_and_expired(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email,
        "password": "MyValidPassword123!"
    }
    # 1st registration attempt with the email in the whitelist
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user_in_db = results[0]
    assert user_in_db.email == whitelist_entry.email
    assert user_in_db.firstname == payload["firstname"]
    assert user_in_db.surname == payload["surname"]
    assert user_in_db.is_superuser == False
    assert user_in_db.is_admin == False
    # Modify the user to be inactive for too long
    user_in_db.activation_expires_at = now_tz_naive() - timedelta(hours=1) # expired token
    db_session.add(user_in_db)
    db_session.commit()
    assert user_in_db.activation_expires_at < now_tz_naive()
    # 2nd registration attempt with the same email
    payload["firstname"] = "NewJohn"
    payload["surname"] = "NewDoe"
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the old user was overwritten  
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user = results[0]
    assert user.is_superuser == False
    assert user.is_admin == False
    assert user.authorized_by == user_in_db.authorized_by # the user should keep the same authorized_by as before
    assert user.activation_code is not None
    assert user.activation_expires_at is not None
    assert user.activation_code != user_in_db.activation_code
    assert user.activation_expires_at != user_in_db.activation_expires_at
    assert user.activation_expires_at > now_tz_naive()
    assert user.firstname == payload["firstname"] # the new user should have the new firstname and surname from the new payload
    assert user.surname == payload["surname"] # the new user should have the new firstname and surname from the new payload

def test_register_overwrite_user_if_inactive_blocked_and_unreliable(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email,
        "password": "MyValidPassword123!"
    }
    # 1st registration attempt with the email in the whitelist
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user_in_db = results[0]
    assert user_in_db.email == whitelist_entry.email
    assert user_in_db.firstname == payload["firstname"]
    assert user_in_db.surname == payload["surname"]
    assert user_in_db.is_superuser == False
    assert user_in_db.is_admin == False
    # A new user is created with these default values
    assert user_in_db.is_blocked == False
    assert user_in_db.is_reliable == True
    assert user_in_db.reliability_score == 100
    # Modify the user to be inactive, blocked and unreliable
    user_in_db.activation_expires_at = now_tz_naive() - timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS + 1) # expired token
    user_in_db.is_blocked = True
    user_in_db.is_reliable = False
    user_in_db.reliability_score = 0
    user_in_db.last_reliability_score_at = now_tz_naive() - timedelta(hours=ACTIVATION_TOKEN_TTL_HOURS + 1)
    db_session.add(user_in_db)
    db_session.commit()
    db_session.refresh(user_in_db)
    # Now, we try to do a 2nd registration attempt, with the same email,
    # with the malicious intent to reset the is_blocked, is_reliable and reliability_score fields to default values.
    # But the system should not allow this, and should remember the old values of these fields
    payload["firstname"] = "NewJohn"
    payload["surname"] = "NewDoe"
    payload["email"] = whitelist_entry.email
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the old user has been overwritten  
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user = results[0]
    assert user.is_superuser == False
    assert user.is_admin == False
    assert user.firstname == payload["firstname"]
    assert user.surname == payload["surname"]
    # Blocked and unreliable fields should remain as they were before the 2nd registration attempt
    assert user.is_blocked == True
    assert user.is_reliable == False
    assert user.reliability_score == 0
    assert user.last_reliability_score_at is not None
    assert user.last_reliability_score_at == user_in_db.last_reliability_score_at

def test_register_overwrite_but_not_whitelisted_anymore(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email,
        "password": "MyValidPassword123!"
    }
    # 1st registration attempt with the email in the whitelist
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user_in_db = results[0]
    assert user_in_db.email == whitelist_entry.email
    assert user_in_db.firstname == payload["firstname"]
    assert user_in_db.surname == payload["surname"]
    assert user_in_db.is_superuser == False
    assert user_in_db.is_admin == False
    # Now, we remove the whitelist entry for this email
    db_session.delete(whitelist_entry)
    db_session.commit()
    # 2nd registration attempt with the same email, but now it is not in the whitelist anymore,
    # because the whitelist entry was deleted. The system should not allow this, and should not overwrite the existing user.
    payload["firstname"] = "NewJohn"
    payload["surname"] = "NewDoe"
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the existing user was not overwritten
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user_in_db = results[0]
    assert user_in_db.firstname == "John" # the old firstname
    assert user_in_db.surname == "Doe" # the old surname, so it was not overwritten

def test_register_privileges_fetched_from_whitelist(client, db_session, superuser_in_db, whitelist_entry):
    # Check the database to ensure the superuser already exists
    users = db_session.exec(select(User)).all()
    assert len(users) == 1
    assert users[0].is_superuser == True
    assert superuser_in_db.is_superuser == True
    assert users[0].id == superuser_in_db.id
    # Now, we simulate a whitelist entry with specific privileges for that email, 
    # for example, if in whitelist we have: type=chief and role=volunteer, 
    # the new user should inherit these privileges from the whitelist entry.
    assert whitelist_entry.user_is_registered == False
    whitelist_entry.registration_type = UserType.chief
    whitelist_entry.registration_role = UserRole.volunteer
    db_session.add(whitelist_entry)
    db_session.commit()
    db_session.refresh(whitelist_entry)
    payload = {
        "firstname": "John",
        "surname": "Doe",
        "email": whitelist_entry.email,
        "password": "MyValidPassword123!"
    }
    # We call the registration API with the email in the whitelist
    response = client.post("/api/register", json=payload)
    assert response.status_code in [200, 201, 202]
    # Check the database to ensure that the user was created with the email in the whitelist
    statement = select(User).where(User.email == whitelist_entry.email)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    user_in_db = results[0]
    assert user_in_db.email == whitelist_entry.email
    assert user_in_db.firstname == payload["firstname"]
    assert user_in_db.surname == payload["surname"]
    assert user_in_db.is_superuser == False
    assert user_in_db.is_admin == False
    # The user should be authorized by the creator of the whitelist entry
    assert user_in_db.authorized_by == whitelist_entry.created_by
    # The privileges of the new user should be set according to the whitelist entry
    assert user_in_db.is_chief == True
    assert user_in_db.role == UserRole.volunteer
    db_session.refresh(whitelist_entry)
    # The field "user_is_registered" in the whitelist entry should be set to True, 
    # because the user has registered with that email. 
    # Finally, registration_type and registration_role should be reset to None, 
    # for security reasons.
    assert whitelist_entry.user_is_registered == True
    assert whitelist_entry.registration_type == None
    assert whitelist_entry.registration_role == None
