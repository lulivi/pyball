# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

"""The telegram plugin against PyBall's committed plugin contract, plugins/openapi.json."""

import json
from pathlib import Path

from pyball_client.contract import check_endpoints, operation

from pyball_telegram.api import ENDPOINTS, EVENTS

ROOT = Path(__file__).parents[1]
SCHEMA = json.loads((ROOT.parent / "openapi.json").read_text(encoding="utf-8"))
SOURCES = sorted((ROOT / "src" / "pyball_telegram").glob("*.py"))


def test_every_call_the_plugin_makes_matches_the_schema():
    """Each declared endpoint exists, takes what the plugin sends and decodes into its types."""
    check_endpoints(SCHEMA, ENDPOINTS)


def test_the_plugin_can_resume_the_event_stream():
    """GET /events still reads the Last-Event-ID header."""
    params = operation(SCHEMA, EVENTS)["parameters"]
    assert any(p["in"] == "header" and p["name"] == "last-event-id" for p in params)


def test_the_plugin_calls_pyball_only_through_its_endpoints():
    """A path written anywhere but api.py would go unchecked."""
    for source in SOURCES:
        if source.name != "api.py":
            assert '"/' not in source.read_text(encoding="utf-8"), f"{source.name} builds a path"


def test_the_plugin_imports_nothing_from_pyball():
    """The plugin uses only the plugin API, never the core's code."""
    for source in SOURCES:
        text = source.read_text(encoding="utf-8")
        assert "from pyball." not in text and "import pyball\n" not in text, source.name
