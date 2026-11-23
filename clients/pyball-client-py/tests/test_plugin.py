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

"""Tests for the plugin environment, config table and state helpers."""

import pytest

from pyball_client import plugin


def test_api_url_and_token_come_from_the_environment(monkeypatch):
    """PYBALL_API_URL loses its trailing slash; a missing token is a PluginError."""
    monkeypatch.setenv("PYBALL_API_URL", "http://core:8000/api/v1/")
    monkeypatch.delenv("PYBALL_API_TOKEN", raising=False)
    assert plugin.api_url() == "http://core:8000/api/v1"
    with pytest.raises(plugin.PluginError, match="PYBALL_API_TOKEN"):
        plugin.api_token()

    monkeypatch.delenv("PYBALL_API_URL")
    monkeypatch.setenv("PYBALL_API_TOKEN", "t")
    assert plugin.api_url() == plugin.DEFAULT_API_URL
    assert plugin.api_token() == "t"


def test_reads_only_the_plugins_own_table(tmp_path):
    """The table under [pyball.plugins.<name>], or an empty one."""
    config = tmp_path / "config.toml"
    config.write_text('[pyball.core]\nname = "x"\n\n[pyball.plugins.demo]\nchat_id = -1\n')
    assert plugin.table(config, "demo") == {"chat_id": -1}
    assert plugin.table(config, "other") == {}
    with pytest.raises(plugin.PluginError):
        plugin.table(tmp_path / "missing.toml", "demo")


def test_event_id_round_trips(tmp_path):
    """No file means no event yet; a saved id loads back, its folder created."""
    path = tmp_path / "data" / "plugins" / "demo" / "last_event_id"
    assert plugin.load_event_id(path) is None
    plugin.save_event_id(path, 42)
    assert plugin.load_event_id(path) == 42
    assert [p.name for p in path.parent.iterdir()] == ["last_event_id"]
