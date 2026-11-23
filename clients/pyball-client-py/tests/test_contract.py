"""Tests for the contract check against a small hand-written schema."""

from typing import Any, Literal

import pytest
from pydantic import BaseModel, Field

from pyball_client import Endpoint
from pyball_client.contract import check, check_endpoints

SCHEMA = {
    "paths": {
        "/meetups": {
            "get": {
                "parameters": [{"name": "date", "in": "query"}],
                "responses": {
                    "200": {
                        "content": {
                            "application/json": {
                                "schema": {
                                    "type": "array",
                                    "items": {"$ref": "#/components/schemas/MeetupOut"},
                                }
                            }
                        }
                    }
                },
            },
            "post": {
                "requestBody": {
                    "required": True,
                    "content": {
                        "application/json": {"schema": {"$ref": "#/components/schemas/Body"}}
                    },
                },
                "responses": {
                    "201": {"content": {"application/json": {"schema": {"type": "object"}}}}
                },
            },
        },
        "/stats.png": {"get": {"responses": {"200": {"content": {"image/png": {}}}}}},
        "/events": {
            "get": {
                "responses": {
                    "200": {
                        "content": {
                            "text/event-stream": {
                                "itemSchema": {
                                    "properties": {
                                        "data": {
                                            "contentSchema": {
                                                "$ref": "#/components/schemas/EventOut"
                                            }
                                        }
                                    }
                                }
                            }
                        }
                    }
                }
            }
        },
    },
    "components": {
        "schemas": {
            "MeetupOut": {
                "type": "object",
                "required": ["id", "teams"],
                "properties": {
                    "id": {"type": "string"},
                    "teams": {
                        "anyOf": [{"type": "array", "items": {"type": "string"}}, {"type": "null"}]
                    },
                    "kind": {"type": "string", "enum": ["classic", "triangular"]},
                },
            },
            "EventOut": {
                "type": "object",
                "required": ["id", "type"],
                "properties": {"id": {"type": "integer"}, "type": {"type": "string"}},
            },
            "Body": {
                "type": "object",
                "required": ["date"],
                "properties": {"date": {"type": "string"}, "capacity": {"type": "integer"}},
            },
        }
    },
}


class Meetup(BaseModel):
    """What a plugin reads of a meetup."""

    id: str
    teams: list[str] | None
    kind: Literal["classic", "triangular"] = "classic"


class Event(BaseModel):
    """What a plugin reads of an event, with an aliased field."""

    id: int
    kind: str = Field(alias="type")


class Body(BaseModel):
    """What a plugin sends."""

    date: str
    capacity: int | None = None


GOOD: list[Endpoint[Any]] = [
    Endpoint("GET", "/meetups", list[Meetup], query=("date",)),
    Endpoint("POST", "/meetups", dict, sample=Body(date="2026-11-25T20:00", capacity=10)),
    Endpoint("GET", "/stats.png", bytes),
    Endpoint("GET", "/events", Event),
]


def test_matching_calls_pass():
    """Answers decode, bodies are accepted, query params and the bytes answer exist."""
    check_endpoints(SCHEMA, GOOD)


class Stale(BaseModel):
    """Reads a field the schema does not have."""

    id: str
    location: str = ""


class Strict(BaseModel):
    """Needs a field the schema leaves nullable."""

    id: str
    teams: list[str]


class Unknown(BaseModel):
    """Sends a field the schema does not take."""

    date: str
    colour: str


@pytest.mark.parametrize(
    ("endpoint", "message"),
    [
        (Endpoint("GET", "/meetups", list[Stale]), "reads 'location'"),
        (Endpoint("GET", "/meetups", list[Strict]), "cannot decode"),
        (Endpoint("GET", "/gone", dict), "is not in the schema"),
        (Endpoint("GET", "/meetups", list[Meetup], query=("day",)), "query parameter day"),
        (Endpoint("POST", "/meetups", dict), "needs a body"),
        (Endpoint("POST", "/meetups", dict, sample=Unknown(date="d", colour="x")), "accepts"),
        (Endpoint("GET", "/meetups", bytes), "no longer answers bytes"),
    ],
)
def test_mismatches_fail(endpoint, message):
    """Each kind of drift between the plugin and the schema fails with its reason."""
    with pytest.raises(AssertionError, match=message):
        check(SCHEMA, endpoint)
