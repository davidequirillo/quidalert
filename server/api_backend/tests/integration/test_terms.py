# Quidalert – a network alert manager: it receives alerts from users and makes decisions to help them
# Copyright (C) 2025  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import io
from fastapi import status

def test_get_terms_default_language(client):
    response = client.get("/api/terms")
    content = response.content.decode("utf-8")
    assert ("Legal terms" in content) or ("Title" in content)
                                                                           
def test_get_terms_en_language(client):
    client.headers["Accept-Language"] = "en"
    response = client.get("/api/terms")
    content = response.content.decode("utf-8")
    assert ("Legal terms" in content) or ("Title" in content)
    assert response.status_code == 200

def test_get_terms_it_language(client):
    client.headers["Accept-Language"] = "it"
    response = client.get("/api/terms")
    content = response.content.decode("utf-8")
    assert ("Termini legali" in content) or ("Titolo" in content)
    assert response.status_code == 200

def test_upload_terms_not_logged_in(client):
    file_content = b"Fake file content for testing"
    file_name = "test_file.md"
    # We prepare files dict as requested by TestClient for multipart/form-data upload
    # Format: {"parameter_name": (file_name, file_object, content_type)}
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data={'language': 'en'}, files=files)
    assert response.status_code == status.HTTP_401_UNAUTHORIZED

def test_upload_terms_logged_but_not_admin(client, test_baseuser):
    file_content = b"Fake file content for testing"
    file_name = "test_file.md"
    headers = {
        "Authorization": f"Bearer {test_baseuser['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data={'language': 'en'}, files=files, headers=headers)
    assert response.status_code == status.HTTP_403_FORBIDDEN

def test_upload_terms_with_blank_or_invalid_language(client, test_admin):
    file_content = b"Fake file content for testing"
    file_name = "test_file.md"
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", files=files, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = {
        "language": ""
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
    data = {
        "language": "blah blah blah" # invalid language, but it should be accepted and default to English
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == status.HTTP_200_OK
