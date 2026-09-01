# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

from fastapi import status
from sqlmodel import select
from models.general import WhiteListEntry
from core.exceptions import (
    forbidden_exception, 
    invalid_request_exception, 
    token_not_valid_exception,
    not_found_exception
)

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
    assert response.status_code == invalid_request_exception().status_code
    assert "Invalid mode" in response.json()["detail"]

def test_del_whitelist_entries_single_email_blank(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {"email": ""}
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == not_found_exception().status_code
    assert "Email not provided" in response.json()["detail"]
    
def test_del_whitelist_entries_single_invalid_email(client, db_session, test_admin):
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "invalid_email"
    }
    response = client.delete("/api/whitelist-entries/single", params=data, headers=headers)
    assert response.status_code == not_found_exception().status_code
    assert "entry not found" in response.json()["detail"].lower()

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

def test_del_whitelist_entries_forbidden_request(client, test_chief):
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
    # Create a whitelist entry to be deleted.
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
    assert response_data["deleted_count"] == 1
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    assert len(results) == 0

def test_del_whitelist_entries_single_email_not_owned_by_officer(client, db_session, test_officer):
    # Create a whitelist entry to be deleted, but owned by a different officer.
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
    assert "entry not created by you" in response.json()["detail"].lower()
    # Obviously the entry should not be deleted cause the exception was raised
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
    assert response.status_code == not_found_exception().status_code
    assert "entry not found" in response.json()["detail"].lower()

def test_del_whitelist_entries_all_by_admin(client, db_session, test_admin):
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
    response = client.delete("/api/whitelist-entries/all", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Check that the response indicates the correct number of deleted entries
    # Only the entries owned by the admin should be deleted.
    # We do this way for efficiency reasons, to avoid querying the entire database.
    assert response_data["deleted_count"] == 2
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    # The entry owned by the other admin should remain
    assert len(results) == 1
    assert results[0].email == "test3@example.com"

def test_del_whitelist_entries_all_by_officer(client, db_session, test_officer):
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
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Check that the response indicates the correct number of deleted entries
    # Only the entries owned by the officer should be deleted
    assert response_data["deleted_count"] == 3
    statement = select(WhiteListEntry)
    results = db_session.exec(statement).all()
    # The entries owned by the other officer should remain
    assert len(results) == 2
    assert results[0].email == "test4@example.com"
    assert results[1].email == "test5@example.com"

def test_del_whitelist_entries_single_user_is_registered(client, db_session, test_admin):
    # Create an entry owned by the admin with user_is_registered set to True
    entry = WhiteListEntry(
        email="test1@example.com", 
        created_by=test_admin['user'].email, 
        user_is_registered=True)
    db_session.add(entry)
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 1
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    data = {
        "email": "test1@example.com"
    }
    response = client.delete(f"/api/whitelist-entries/single", params=data, headers=headers)
    # The entry should not be deleted because user_is_registered is True
    assert response.status_code == forbidden_exception().status_code
    assert "registered user" in response.json()["detail"].lower()

def test_del_whitelist_entries_all_with_user_is_registered_case_1(client, db_session, test_admin):
    # Create two entries owned by the admin with user_is_registered set to False, 
    # and one entry with user_is_registered set to True, so it should not be deleted
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_admin['user'].email, user_is_registered=False)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_admin['user'].email, user_is_registered=False)
    entry3 = WhiteListEntry(email="test3@example.com", created_by=test_admin['user'].email, user_is_registered=True)
    db_session.add_all([entry1, entry2, entry3])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 3
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/all", headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    # Only the entries with user_is_registered set to False should be deleted
    assert response_data["deleted_count"] == 2
    # The entry with user_is_registered set to True should remain
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 1
    assert results[0].user_is_registered is True
    assert results[0].email == "test3@example.com"

def test_del_whitelist_entries_all_with_user_is_registered_case_2(client, db_session, test_admin):
    # Create two entries owned by the admin with user_is_registered set to False,
    # and one entry with user_is_registered set to True, so it should not be deleted,
    # We also create entries owned by other users to ensure they are not deleted
    entry1 = WhiteListEntry(email="test1@example.com", created_by=test_admin['user'].email, user_is_registered=False)
    entry2 = WhiteListEntry(email="test2@example.com", created_by=test_admin['user'].email, user_is_registered=False)
    entry3 = WhiteListEntry(email="test3@example.com", created_by=test_admin['user'].email, user_is_registered=True)
    other_entry = WhiteListEntry(email="other@example.com", created_by="other_user@example.com", user_is_registered=False)
    db_session.add_all([entry1, entry2, entry3, other_entry])
    db_session.commit()
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 4
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    response = client.delete("/api/whitelist-entries/all", headers=headers)
    # Only the entries owned by the admin and with user_is_registered set to False should be deleted
    assert response.status_code == status.HTTP_200_OK
    response_data = response.json()
    assert response_data["deleted_count"] == 2
    results = db_session.exec(select(WhiteListEntry)).all()
    assert len(results) == 2
    # The remaining entries should be the one with user_is_registered set to True and the other user's entry
    emails = [entry.email for entry in results]
    assert "test3@example.com" in emails
    assert "other@example.com" in emails
