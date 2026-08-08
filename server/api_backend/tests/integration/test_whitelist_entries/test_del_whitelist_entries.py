# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from models.general import WhiteListEntry
from core.exceptions import forbidden_exception, token_not_valid_exception

def test_del_whitelist_entries_method_not_allowed(client, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries", params=data, headers=headers)
    assert response.status_code == status.HTTP_405_METHOD_NOT_ALLOWED

def test_del_whitelist_entries_invalid_endpoint(client, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    # The endpoint should return 404 Not Found if the URL is not correct
    response = client.delete("/api/whitelist-entries-invalid", params=data, headers=headers)
    assert response.status_code == status.HTTP_404_NOT_FOUND

def test_del_whitelist_entries_mode_not_valid(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/invalid", params=data, headers=headers)
    # The endpoint should return 200 OK even if the mode is not valid, because it will just not find any entry to delete
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["deleted_count"] == 0

def test_del_whitelist_entries_single_email_blank(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {"email": ""}
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    # The endpoint should return 200 OK even if no email is provided, because it will just not find any entry to delete
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["deleted_count"] == 0
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0
    data = {} # No email key at all
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    # The endpoint should return 200 OK even if no email is provided, 
    # because it will just not find any entry to delete
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["deleted_count"] == 0
    
def test_del_whitelist_entries_single_invalid_email(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "invalid_email"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    # The endpoint should return 200 OK even if the email is invalid, because it will just not find any entry to delete
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["deleted_count"] == 0
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_del_whitelist_entries_not_authorized_token_missing(client):
    # Access token missing
    headers = {
        # No Authorization header
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_del_whitelist_entries_not_authorized_token_invalid(client):
    # Access token not valid
    headers = {
        "Authorization": "Bearer invalid_token"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == token_not_valid_exception().status_code
    assert response.json()["detail"] == token_not_valid_exception().detail

def test_del_whitelist_entries_forbidden(client, test_chief):
    # The user is not an admin or officer
    headers = {
        "Authorization": f"Bearer {test_chief['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail

def test_del_whitelist_entries_single_email_by_admin(client, db_session, test_admin):
    # Create a whitelist entry to be deleted
    # Note: the admin can delete any entry, even if created by other admins or officers
    entry = WhiteListEntry(email="test@example.com", created_by="a.different.admin@example.com")
    db_session.add(entry)
    db_session.commit()
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 1
    assert response_data["deleted_count"] == 1
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_del_whitelist_entries_single_email_not_owned_by_officer(client, db_session, test_officer):
    # Create a whitelist entry to be deleted, but owned by a different officer
    entry = WhiteListEntry(email="test@example.com", created_by="a.different.officer@example.com")
    db_session.add(entry)
    db_session.commit()
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
    # Obviously the entry should not be deleted cause the officer is not allowed to delete entries created by other officers
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1

def test_del_whitelist_entries_single_email_by_officer(client, db_session, test_officer):
    # Create a whitelist entry to be deleted (owned by the officer)
    entry = WhiteListEntry(email="test@example.com", created_by=test_officer['user'].email)
    db_session.add(entry)
    db_session.commit()
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    data = {
        "email": "test@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Officers can delete their own entries, so the entry should be deleted
    assert response_data["total_count"] == 1
    assert response_data["deleted_count"] == 1
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_del_whitelist_entries_single_email_not_existing(client, db_session, test_admin):
    # We insert a whitelist entry to be sure that the database is not empty
    entry = WhiteListEntry(email="test@example.com", created_by="a.different.admin@example.com")
    db_session.add(entry)
    db_session.commit()
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "nonexistent@example.com"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 0
    assert response_data["deleted_count"] == 0
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 1

def test_del_whitelist_entries_mode_mine_by_officer(client, db_session, test_officer):
    # Create two entries owned by the officer and one entry owned by another officer
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_officer['user'].email)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_officer['user'].email)
    entry3 = WhiteListEntry(email="test3@example.com", created_by="a.different.officer@example.com")
    db_session.add_all([entry1, entry2, entry3])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 3
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/mine", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 2
    assert response_data["deleted_count"] == 2
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    # Only the entry owned by the other officer should remain
    assert len(results) == 1
    assert results[0].email == "test3@example.com"

def test_del_whitelist_entries_mode_mine_by_admin(client, db_session, test_admin):
    # Create two entries owned by the admin and one entry owned by another admin
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_admin['user'].email)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_admin['user'].email)
    entry3 = WhiteListEntry(email="test3@example.com", created_by="a.different.admin@example.com")
    db_session.add_all([entry1, entry2, entry3])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 3
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/mine", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 2
    assert response_data["deleted_count"] == 2
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    # Only the entry owned by the other admin should remain
    assert len(results) == 1
    assert results[0].email == "test3@example.com"

def test_del_whitelist_entries_mode_all_by_admin(client, db_session, test_admin):
    # Create three entries owned by the admin and two entries owned by another admin
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_admin['user'].email)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_admin['user'].email)
    entry3 = WhiteListEntry(email="test3@example.com", created_by=test_admin['user'].email)
    entry4 = WhiteListEntry(email="test4@example.com", created_by="a.different.admin@example.com")
    entry5 = WhiteListEntry(email="test5@example.com", created_by="a.different.admin@example.com")
    db_session.add_all([entry1, entry2, entry3, entry4, entry5])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 5
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/all", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["total_count"] == 5
    assert response_data["deleted_count"] == 5
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    # All entries should be deleted
    assert len(results) == 0

def test_del_whitelist_entries_mode_all_by_officer(client, db_session, test_officer):
    # Create three entries owned by the officer and two entries owned by another officer
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_officer['user'].email)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_officer['user'].email)
    entry3 = WhiteListEntry(email="test3@example.com", created_by=test_officer['user'].email)
    entry4 = WhiteListEntry(email="test4@example.com", created_by="a.different.officer@example.com")
    entry5 = WhiteListEntry(email="test5@example.com", created_by="a.different.officer@example.com")
    db_session.add_all([entry1, entry2, entry3, entry4, entry5])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 5
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/all", headers=headers)
    # Officers are not allowed to delete all entries, so the endpoint should return 403 Forbidden
    assert response.status_code == forbidden_exception().status_code
    assert response.json()["detail"] == forbidden_exception().detail
