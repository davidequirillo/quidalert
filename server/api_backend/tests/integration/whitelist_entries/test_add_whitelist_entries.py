# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from models.general import WhiteListEntry, User
from core.exceptions import forbidden_exception, token_not_valid_exception

def test_add_whitelist_entries_no_data(client, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {}
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_add_whitelist_entries_invalid_data(client, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "invalid_field": "invalid value"
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = {
        "emails": "invalid format (should be a list)"
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_add_whitelist_entries_empty_emails_list(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": []
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["added_count"] == 0
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_add_whitelist_entries_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_add_whitelist_entries_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_add_whitelist_entries_forbidden(client, test_baseuser):
    # The user is not an admin or officer
    headers = {
        "Authorization": f"Bearer {test_baseuser['access_token']}"
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_add_whitelist_entries_forbidden_chief(client, test_chief):
    # The user is a chief but not an admin or officer
    headers = {
        "Authorization": f"Bearer {test_chief['access_token']}"
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_add_whitelist_entries_success(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 2
    assert response_data["added_count"] == 2
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 2

def test_add_whitelist_entries_with_existing_email(client, db_session, test_admin):
    admin: User = test_admin["user"]
    # Add an entry to the database first
    entry = WhiteListEntry.model_validate({
        "email": "test1@example.com",
        "created_by": admin.email
    })
    db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": ["test1@example.com", "test2@example.com"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 2
    assert response_data["added_count"] == 1
    assert response_data["existing_count"] == 1
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 2

def test_add_whitelist_entries_with_none_email(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": ["", None, "   ", "invalid_email"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT

def test_add_whitelist_entries_with_invalid_emails(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": ["", " ", "   ", "invalid_email"]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 4
    assert response_data["added_count"] == 0
    assert response_data["existing_count"] == 0
    # Note: blank emails are skipped without being added to failed_emails
    assert response_data["skipped_count"] == 3
    assert response_data["failed_count"] == 1
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_add_whitelist_entries_with_mixed_valid_and_invalid_emails(client, db_session, test_officer):
    officer: User = test_officer["user"]
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    data = {
        "emails": [
            "valid1@example.com", 
            "VALID2@example.com", 
            "", 
            " ", 
            "   ", 
            "invalid_email",
            "invalid_email2@example" # missing TLD
        ]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 7
    assert response_data["added_count"] == 2
    assert response_data["existing_count"] == 0
    assert response_data["skipped_count"] == 3
    assert response_data["failed_count"] == 2
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 2
    assert results[0].email == "valid1@example.com"
    assert results[0].created_by == officer.email
    assert results[1].email == "valid2@example.com" # should be normalized to lowercase
    assert results[1].created_by == officer.email

def test_add_whitelist_entries_with_duplicate_emails_in_request(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "emails": [
            "duplicate@example.com", # this one should be added
            "DUPLICATE@example.com",
            "DUPlicAtE@example.com"
        ]
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 3
    assert response_data["added_count"] == 1
    assert response_data["existing_count"] == 2
    assert response_data["skipped_count"] == 0
    assert response_data["failed_count"] == 0
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1

def test_add_whitelist_entries_with_large_number_of_emails(client, db_session, test_admin):
    admin: User = test_admin["user"]
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    existing_entry1 = WhiteListEntry.model_validate({
        "email": "existing1@example.com",
        "created_by": admin.email
    })
    existing_entry2 = WhiteListEntry.model_validate({
        "email": "existing2@example.com",
        "created_by": admin.email
    })
    db_session.add(existing_entry1)
    db_session.add(existing_entry2)
    db_session.commit()
    correct_emails = [f"user{i}@example.com" for i in range(1, 2100)]
    skipped_emails = ["", " ", "   "] # 3 blank emails that should be skipped
    wrong_emails = ["invalid_email1", "invalid_email2", "invalid_email3@example"] # 3 invalid emails
    duplicate_emails = [
        "user4@example.com",
        "USER4@example.com",
        "User4@example.com",
        "user5@example.com"
        ]
    existing_emails = ["existing1@example.com", "existing2@example.com"]
    data = {
        "emails": correct_emails + wrong_emails + duplicate_emails + existing_emails + skipped_emails
    }
    response = client.post("/api/whitelist-entries", json=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == len(data["emails"])
    assert response_data["added_count"] == len(data["emails"]) - len(wrong_emails) - len(duplicate_emails) - len(existing_emails) - len(skipped_emails)
    assert response_data["existing_count"] == len(existing_emails) + len(duplicate_emails)
    assert response_data["skipped_count"] == len(skipped_emails)
    assert response_data["failed_count"] == len(wrong_emails)
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == response_data["added_count"] + len(existing_emails)
