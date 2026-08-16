# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import MessageIn, MessageOut

def test_create_message_empty_data():
    # It fails because a non empty content is required
    data = {}
    with pytest.raises(ValueError):
        MessageIn.model_validate(data)

def test_create_message_with_empty_content():
    # Content must be a non empty string
    data = {
        "content": None,
    }
    with pytest.raises(ValueError):
        MessageIn.model_validate(data)
    
    data = {
        "content": "",
    }
    with pytest.raises(ValueError):
        MessageIn.model_validate(data)

def test_create_message_with_content():
    data = {
        "content": "This is a test message",
    }
    message = MessageIn.model_validate(data)
    assert message.content == data["content"]

def test_create_message_content_too_long():
    data = {
        "content": "A" * 513,
    }
    with pytest.raises(ValueError):
        MessageIn.model_validate(data)

def test_create_message_out_with_defaults():
    data = {
        "content": "This is a test message",
        "alert_id": 1 
        # Note: user_id is not required in MessageOut (required in Message)
    }
    message = MessageOut.model_validate(data)
    assert message.content == data["content"]
    assert message.is_banned == False
    assert message.created_at is not None
