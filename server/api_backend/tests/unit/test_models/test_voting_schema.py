# Quidalert – a network alert manager: if a client sends an alert, the server propagates it to chief and nearby users.
# Copyright (C) 2026  Davide Quirillo
# Licensed under the GNU GPL v3 or later. See LICENSE for details.

import pytest
from models.general import VotingSchema

def test_vote_schema_positive_success():
    data = {
        "vote": 1
    }
    request = VotingSchema.model_validate(data)
    assert request.vote == data["vote"]
    # Another example
    data = {
        "vote": +1
    }
    request = VotingSchema.model_validate(data)
    assert request.vote == data["vote"]

def test_vote_schema_negative_success():
    data = {
        "vote": -1
    }
    request = VotingSchema.model_validate(data)
    assert request.vote == data["vote"]

def test_vote_schema_invalid_vote():
    data = {
        "vote": 0
    }
    with pytest.raises(ValueError):
        VotingSchema.model_validate(data)
    # Another example with an invalid vote value
    data = {
        "vote": 5
    }
    with pytest.raises(ValueError):
        VotingSchema.model_validate(data)
    # Another example with an invalid vote value
    data = {
        "vote": -5
    }
    with pytest.raises(ValueError):
        VotingSchema.model_validate(data)
