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
"""Tests for funnelbot's club discovery and routing state."""

from pathlib import Path

import funnelbot
import pytest


@pytest.fixture(name="reloads", autouse=True)
def fixture_reloads(tmp_path: Path, monkeypatch: pytest.MonkeyPatch) -> list[bool]:
    """Point funnelbot at temp dirs with two clubs; queue reload results by appending."""
    apps = tmp_path / "apps"
    for club, env in (("tensores", "PORT=8000\n"), ("cucarachas", "IMAGE=x\nPORT=8001\n")):
        (apps / club).mkdir(parents=True)
        (apps / club / ".env").write_text(env)
    (apps / "noport").mkdir()
    (apps / ".hidden").mkdir()
    (apps / "file.txt").write_text("")
    (tmp_path / "caddy").mkdir()
    monkeypatch.setattr(funnelbot, "APPS_DIR", apps)
    monkeypatch.setattr(funnelbot, "CADDY_DIR", tmp_path / "caddy")

    results: list[bool] = []

    async def fake_reload() -> bool:
        return results.pop(0) if results else True

    monkeypatch.setattr(funnelbot, "_reload_caddy", fake_reload)
    return results


def _enabled_file(club: str) -> Path:
    return funnelbot.CADDY_DIR / "enabled" / club


def test_list_clubs_skips_hidden_dirs_and_files():
    assert funnelbot.list_clubs() == ["cucarachas", "noport", "tensores"]


def test_read_port():
    assert funnelbot.read_port("cucarachas") == "8001"
    assert funnelbot.read_port("noport") is None


@pytest.mark.parametrize(
    "data, expected",
    [
        ("tensores on", ("tensores", "on")),
        ("cucarachas log", ("cucarachas", "log")),
        ("reset", ("", "reset")),
        ("unknown on", None),
        ("tensores restart", None),
        ("../tensores on", None),
    ],
)
def test_parse_command(data, expected):
    assert funnelbot.parse_command(data) == expected


@pytest.mark.asyncio
async def test_switch_on_writes_the_club_import():
    assert await funnelbot.switch_on("tensores") is None
    assert _enabled_file("tensores").read_text() == "import club tensores 8000\n"
    assert funnelbot.enabled_clubs() == {"tensores"}


@pytest.mark.asyncio
async def test_switch_on_refuses_a_club_without_port():
    assert await funnelbot.switch_on("noport") is not None
    assert funnelbot.enabled_clubs() == set()


@pytest.mark.asyncio
async def test_switch_off_deletes_the_club_file():
    await funnelbot.switch_on("tensores")
    await funnelbot.switch_on("cucarachas")
    assert await funnelbot.switch_off("tensores") is None
    assert funnelbot.enabled_clubs() == {"cucarachas"}


@pytest.mark.asyncio
async def test_reset_deletes_every_file_including_removed_clubs():
    await funnelbot.switch_on("tensores")
    _enabled_file("gone").write_text("import club gone 9000\n")
    assert await funnelbot.reset() is None
    assert funnelbot.enabled_clubs() == set()


@pytest.mark.asyncio
async def test_failed_reload_restores_the_previous_files(reloads):
    await funnelbot.switch_on("tensores")
    reloads.extend([False, False])
    assert await funnelbot.switch_off("tensores") is not None
    assert await funnelbot.switch_on("cucarachas") is not None
    assert funnelbot.enabled_clubs() == {"tensores"}
    assert _enabled_file("tensores").read_text() == "import club tensores 8000\n"


def test_panel_shows_each_club_port_and_state():
    _enabled_file("tensores").parent.mkdir()
    _enabled_file("tensores").write_text("import club tensores 8000\n")
    panel = funnelbot.format_panel_message()
    assert "Tensores (port 8000): 🟢 ON" in panel
    assert "Cucarachas (port 8001): 🔴 OFF" in panel
    assert "Noport (port ?): 🔴 OFF" in panel
