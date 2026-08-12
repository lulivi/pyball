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
"""Tests for build_meetup_active_response's signupUrl field."""

from datetime import datetime
from unittest.mock import MagicMock

from pyball.infrastructure.http.presenters import build_meetup_active_response


def _base_container():
    container = MagicMock()
    container.team_colors = ("blanco", "negro")
    container.team_hex_bg = ("#e4e4e7", "#27272a")
    container.team_hex_text = ("#27272a", "#e4e4e7")
    container.team_emojis = ("⚪", "⚫")
    return container


def _meetup_without_teams():
    meetup = MagicMock()
    meetup.teams = None
    meetup.date = datetime(2026, 5, 28, 20, 0)
    meetup.location = "X"
    meetup.locked = False
    meetup.is_signup_open.return_value = True
    meetup.players = []
    return meetup


def _meetup_with_teams():
    pid = MagicMock()
    pid.value = "p1"
    meetup = MagicMock()
    meetup.date = datetime(2026, 5, 28, 20, 0)
    meetup.location = "X"
    meetup.players = [pid]
    meetup.teams = [MagicMock(players=[pid]), MagicMock(players=[])]
    meetup.locked = False
    meetup.matches = []
    meetup.is_signup_open.return_value = False
    return meetup


def _player():
    player = MagicMock()
    player.id.value = "p1"
    player.name = "Ana"
    player.position = None
    return player


def test_signup_url_present_when_enabled_and_no_teams():
    container = _base_container()
    container.get_active_meetup.return_value.execute.return_value = _meetup_without_teams()
    container.player_repository.find_all.return_value = []
    container.signup_link_builder.return_value.build.return_value = "http://x/signup?token=t"

    response = build_meetup_active_response(container, enable_web_signup=True)

    assert response["signupUrl"] == "http://x/signup?token=t"


def test_signup_url_absent_when_disabled_and_no_teams():
    container = _base_container()
    container.get_active_meetup.return_value.execute.return_value = _meetup_without_teams()
    container.player_repository.find_all.return_value = []

    response = build_meetup_active_response(container, enable_web_signup=False)

    assert "signupUrl" not in response


def test_signup_url_present_when_enabled_and_teams_exist():
    container = _base_container()
    container.get_active_meetup.return_value.execute.return_value = _meetup_with_teams()
    container.player_repository.find_all.return_value = [_player()]
    container.match_link_builder.return_value.build.return_value = "http://x/match"
    container.signup_link_builder.return_value.build.return_value = "http://x/signup?token=t"

    response = build_meetup_active_response(container, enable_web_signup=True)

    assert response["signupUrl"] == "http://x/signup?token=t"
    assert response["teams"]["matchUrl"] == "http://x/match"


def test_signup_url_absent_when_disabled_and_teams_exist():
    container = _base_container()
    container.get_active_meetup.return_value.execute.return_value = _meetup_with_teams()
    container.player_repository.find_all.return_value = [_player()]
    container.match_link_builder.return_value.build.return_value = "http://x/match"

    response = build_meetup_active_response(container, enable_web_signup=False)

    assert "signupUrl" not in response
