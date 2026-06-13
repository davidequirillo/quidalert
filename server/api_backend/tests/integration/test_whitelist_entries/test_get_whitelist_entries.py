# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from models.general import WhiteListEntry
from core.exceptions import forbidden_exception, token_not_valid_exception

def test_get_whitelist_entries_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    data = {
        "email": "test@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_get_whitelist_entries_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_get_whitelist_entries_forbidden(client, test_chief):
    # The user is not an admin or officer
    headers = {
        "Authorization": f"Bearer {test_chief['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_get_whitelist_entries_single_email_blank(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {"email": ""}
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert next_cursor == 0
    assert len(entries) == 0
    
def test_get_whitelist_entries_single_invalid_email(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "invalid_email"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert next_cursor == 0
    assert len(entries) == 0

def test_get_whitelist_entries_single_email_not_found(client, db_session, test_admin):
    # We insert a different entry in the database to ensure that the email we search for is not found
    entry = WhiteListEntry(email="different.email@example.com", created_by=test_admin['user'].email)
    db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "nonexistent.email@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert next_cursor == 0
    assert len(entries) == 0

def test_get_whitelist_entries_single_email_success(client, db_session, test_admin):
    # We insert an entry in the database to be retrieved
    entry = WhiteListEntry(email="test.email@example.com", created_by=test_admin['user'].email)
    db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test.email@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert next_cursor == 0
    assert len(entries) == 1
    assert entries[0]["email"] == "test.email@example.com"
    assert entries[0]["created_by"] == test_admin['user'].email

def test_get_whitelist_entries_pagination(client, db_session, test_admin):
    # We insert multiple entries in the database to test pagination
    for i in range(23):
        entry = WhiteListEntry(email=f"test.email{i}@example.com", created_by=test_admin['user'].email)
        db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "limit": 10
    }
    entries = []
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor != 0
    # The next cursor should be equal to the id of the last entry in the current page
    assert next_cursor == page_entries[-1]["id"]
    entries += page_entries
    # We can use the next_cursor to get the next page of results
    data = {
        "limit": 10,
        "last_seen_id": next_cursor
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor == page_entries[-1]["id"]
    entries += page_entries
    # We can get the last page of results using the next_cursor again
    data = {
        "limit": 10,
        "last_seen_id": next_cursor
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 3
    assert next_cursor == page_entries[-1]["id"]
    entries += page_entries
    # We can try to get another page of results, but there should be no more entries
    data = {
        "limit": 10,
        "last_seen_id": next_cursor
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor == 0
    entries += page_entries
    # We assert that entries does not contain any duplicate entry (e.g. due to some bug in the pagination logic)
    entry_ids = set()
    for e in entries:
        assert e["id"] not in entry_ids
        entry_ids.add(e["id"])

def test_get_whitelist_entries_with_perfect_multiple_of_limit(client, db_session, test_admin):
    # We insert 20 entries in the database to test pagination with a perfect multiple of the limit
    for i in range(20):
        entry = WhiteListEntry(email=f"test.email{i}@example.com", created_by=test_admin['user'].email)
        db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "limit": 10
    }
    entries = []
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor == page_entries[-1]["id"]
    entries += page_entries
    # We can use the next_cursor to get the next page of results
    data = {
        "limit": 10,
        "last_seen_id": next_cursor
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 10
    assert next_cursor == page_entries[-1]["id"]
    entries += page_entries
    # We can try to get another page of results, but there should be no more entries
    data = {
        "limit": 10,
        "last_seen_id": next_cursor
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 0
    assert next_cursor == 0
    entries += page_entries
    # We assert that entries does not contain any duplicate entry (e.g. due to some bug in the pagination logic)
    entry_ids = set()   
    for e in entries:
        assert e["id"] not in entry_ids
        entry_ids.add(e["id"])
    
def test_get_whitelist_entries_default_limit(client, db_session, test_admin):
    # We insert 80 entries in the database to test that the default limit is applied
    for i in range(80):
        entry = WhiteListEntry(email=f"test.email{i}@example.com", created_by=test_admin['user'].email)
        db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {}
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 80  # Default limit is 100, but we only have 80 entries
    assert next_cursor == page_entries[-1]["id"]
    data = {
        "limit": 23  # Invalid limit, should be reset to default
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    page_entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(page_entries) == 80  # Default limit is 100, but we only have 80 entries
    assert next_cursor == page_entries[-1]["id"]

def test_get_whitelist_entries_by_officer(client, db_session, test_officer):
    # We insert entries created by different officers and admins to test that the officer can see only their own entries (in bulk)
    entry1 = WhiteListEntry(email="owned1@example.com", created_by=test_officer['user'].email)
    entry2 = WhiteListEntry(email="owned2@example.com", created_by=test_officer['user'].email)
    entry3 = WhiteListEntry(email="owned3@example.com", created_by=test_officer['user'].email)
    entry4 = WhiteListEntry(email="not.owned1@example.com", created_by="admin@example.com")
    entry5 = WhiteListEntry(email="not.owned2@example.com", created_by="admin@example.com")
    db_session.add(entry1)
    db_session.add(entry2)
    db_session.add(entry3)
    db_session.add(entry4)
    db_session.add(entry5)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    data = {}
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(entries) == 3
    assert next_cursor == entries[-1]["id"]
    for e in entries:
        assert e["created_by"] == test_officer['user'].email
    # We try to set "authorizer" parameters too. 
    # The officer should be able to see only their own entries (in bulk)
    # So, the result will be 0 entries
    data = {
        "authorizer": "admin@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(entries) == 0
    assert next_cursor == 0
    # But, curiosity, if the authorizer parameter is set to the officer email, the officer should be able to see their own entries
    data = {
        "authorizer": test_officer['user'].email
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(entries) == 3
    assert next_cursor == entries[-1]["id"]
    for e in entries:
        assert e["created_by"] == test_officer['user'].email

def test_get_whitelist_entries_by_admin(client, db_session, test_admin):
    # We insert entries created by different officers and admins to test that the admin can see all entries
    entry1 = WhiteListEntry(email="user1byadmin@example.com", created_by=test_admin['user'].email)
    entry2 = WhiteListEntry(email="user2byadmin@example.com", created_by=test_admin['user'].email)
    entry3 = WhiteListEntry(email="user3byofficer@example.com", created_by="officer@example.com")
    entry4 = WhiteListEntry(email="user4byofficer@example.com", created_by="officer@example.com")
    entry5 = WhiteListEntry(email="user5byofficer@example.com", created_by="officer@example.com")
    db_session.add(entry1)
    db_session.add(entry2)
    db_session.add(entry3)
    db_session.add(entry4)
    db_session.add(entry5)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {}
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(entries) == 5
    assert next_cursor == entries[-1]["id"]
    for e in entries:
        assert e["created_by"] in [test_admin['user'].email, "officer@example.com"]
    # We can also filter by authorizer to see only entries created by a specific authorizer (admin can do this operation)
    # For example, admin can view all entries created by a specific officer (or by another admin)
    data = {
        "authorizer": "officer@example.com"
    }
    response = client.get("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    entries = response_data["entries"]
    next_cursor = response_data["next_cursor"]
    assert len(entries) == 3
    assert next_cursor == entries[-1]["id"]
    for e in entries:
        assert e["created_by"] == "officer@example.com"
