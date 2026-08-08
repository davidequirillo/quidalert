# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

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
