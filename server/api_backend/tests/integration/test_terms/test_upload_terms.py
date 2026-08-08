# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import io
from fastapi import status
from core.exceptions import (
    invalid_file_type_exception, 
    file_too_large_exception,
    bad_file_upload_exception
)
from services.fileutils import MAX_SMALL_FILE_SIZE

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

def test_upload_terms_called_by_non_admin(client, test_baseuser):
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

def test_upload_terms_called_by_officer(client, test_officer):
    file_content = b"Fake file content for testing"
    file_name = "test_file.md"
    headers = {
        "Authorization": f"Bearer {test_officer['access_token']}"
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

def test_upload_terms_with_no_filename_or_no_file(client, test_admin):
    file_content = b"Fake file content for testing"
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (None, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert (response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT 
        or (response.status_code == status.HTTP_400_BAD_REQUEST))
    files = {
        "file": ("", io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert (response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        or (response.status_code == status.HTTP_400_BAD_REQUEST))
    files = {
        "file": ("test_file.md", None, "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert (response.status_code == status.HTTP_422_UNPROCESSABLE_CONTENT
        or (response.status_code == status.HTTP_400_BAD_REQUEST))

def test_upload_terms_with_invalid_extension(client, test_admin):
    file_content = b"Fake file content for testing"
    file_name = "test_file.txt" # invalid extension (only .md and .markdown are allowed)
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == status.HTTP_400_BAD_REQUEST

def test_upload_terms_with_invalid_content_type(client, test_admin):
    file_content = b"Fake file content for testing"
    file_name = "test_file.md"
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "application/octet-stream")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == invalid_file_type_exception().status_code
    assert response.json() is not None
    assert response.json()['detail'] == invalid_file_type_exception().detail

def test_upload_terms_file_too_large(client, test_admin):
    file_content = b"Fake file content for testing" * (MAX_SMALL_FILE_SIZE // len("Fake file content for testing") + 2)
    file_name = "test_file.md"
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == file_too_large_exception(MAX_SMALL_FILE_SIZE).status_code
    assert response.json() is not None
    assert response.json()['detail'] == file_too_large_exception(MAX_SMALL_FILE_SIZE).detail

def test_upload_terms_bad_textual_encoding(client, test_admin):
    file_content = b"\xff\xfe\xfd\xfc" # invalid UTF-8
    file_name = "test_file.md"
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == bad_file_upload_exception().status_code
    assert response.json() is not None
    assert response.json()['detail'] == bad_file_upload_exception().detail

def test_upload_terms_html_is_escaped(client, test_admin):
    file_content = b"A simple html <script>alert('xss')</script>"
    file_name = "test_file.md"
    data = {
        "language": "en"
    }
    headers = {
        "Authorization": f"Bearer {test_admin['access_token']}"
    }
    files = {
        "file": (file_name, io.BytesIO(file_content), "text/plain")
    }
    response = client.post("/api/terms", data=data, files=files, headers=headers)
    assert response.status_code == status.HTTP_200_OK
    response = client.get("/api/terms?lang=en")
    content = response.content.decode("utf-8")
    assert "<script>" not in content
    assert "&lt;script&gt;" in content
