"""Tests for the committed plugin contract, plugins/openapi.json."""

from pathlib import Path

from pyball.infrastructure.plugins.openapi import schema_text

_COMMITTED = Path(__file__).parents[3] / "plugins" / "openapi.json"


def test_committed_schema_matches_the_plugin_api():
    """A change to the /api/v1 routes or models regenerates plugins/openapi.json with it."""
    assert (
        _COMMITTED.read_text(encoding="utf-8") == schema_text()
    ), "plugins/openapi.json is out of date: run `make openapi` and commit it"
