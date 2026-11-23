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

"""The callup messages, in Telegram MarkdownV2, and their join/leave buttons."""

from __future__ import annotations

import functools
import locale
import re
from datetime import datetime
from typing import Iterable

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import KeyboardButtonStyle

from pyball_telegram.api import Match, Meetup, Team

ACTIONS = ("join", "leave", "join_sub", "leave_sub")

_MDV2_RE = re.compile(r"([_*\[\]()~`>#+=|{}.!\\-])")


def format_main_message(meetup: Meetup, names: dict[str, str], date_fmt: str, summary: str) -> str:
    """Format the regulars callup.

    Before teams it lists the players by name; with teams, each team and its latest
    score; once closed, the result ``summary`` the core builds.
    """
    if meetup.closed:
        return escape_summary(summary)

    lines = _header(meetup, date_fmt)
    lines.append("")
    if meetup.teams is None:
        lines.append(rf"*Jugadores \({len(meetup.players)}/{meetup.capacity}\):*")
        lines.extend(
            rf"  \- `{name}`" for name in _sorted(names.get(p, "") for p in meetup.players)
        )
        return "\n".join(lines)

    lines.append("*Equipos:*")
    for team in meetup.teams:
        display = _escape(team.color.capitalize())
        score = _latest_score(team, meetup.matches)
        lines.append(
            rf"{team.emoji} Equipo *{display} \({score}\):*"
            if score is not None
            else f"\n{team.emoji} *{display}:*"
        )
        lines.extend(rf"  \- `{name}`" for name in _sorted(names.get(p, "") for p in team.players))
    return "\n".join(lines)


def format_subs_message(
    meetup: Meetup, names: dict[str, str], groups: dict[str, str], date_fmt: str
) -> str:
    """Format the substitutes callup: only the substitutes, by team once there are teams."""
    if meetup.closed:
        return "*Partido terminado*"

    subs = [p for p in meetup.players if groups.get(p, "regular") != "regular"]
    lines = _header(meetup, date_fmt)
    lines.append("")

    if meetup.teams is not None and subs:
        team_of = {p: i for i, team in enumerate(meetup.teams) for p in team.players}
        by_team: dict[int, list[str]] = {}
        for player in subs:
            by_team.setdefault(team_of.get(player, -1), []).append(names.get(player, "Unknown"))
        lines.append(f"Jugadores apuntados {len(meetup.players)}")
        lines.append("")
        for index in sorted(by_team):
            team = meetup.teams[index]
            joined = ", ".join(f"`{name}`" for name in sorted(by_team[index]))
            lines.append(rf"{team.emoji} *{team.color.capitalize()}:* {joined}")
        return "\n".join(lines)

    listed = _sorted(f"`{names.get(p, 'Unknown')}`" for p in subs)
    if not meetup.substitute_search and len(meetup.players) >= meetup.capacity:
        lines.append(rf"✅ *Completo* \({len(meetup.players)} jugadores\)")
        if not listed:
            return "\n".join(lines)
        lines.append("")
    elif not meetup.substitute_search:
        lines.append(f"Jugadores apuntados {len(meetup.players)}")
        lines.append("")
    else:
        lines.append(f"Jugadores apuntados {len(meetup.players)}/{meetup.capacity}")
        lines.append("")

    if listed:
        lines.append(rf"*Suplentes \({len(listed)}\):*")
        lines.extend(rf"  \- {name}" for name in listed)
    else:
        lines.append("*No hay suplentes*")
    return "\n".join(lines)


def escape_summary(summary: str) -> str:
    """Escape a core result summary for MarkdownV2, keeping its *bold* spans bold."""
    return "*".join(_escape(part) for part in summary.split("*"))


def main_keyboard(date: datetime) -> InlineKeyboardMarkup:
    """Return the join/leave buttons of the regulars callup."""
    return _keyboard("join", "leave", date)


def subs_keyboard(date: datetime) -> InlineKeyboardMarkup:
    """Return the join/leave buttons of the substitutes callup."""
    return _keyboard("join_sub", "leave_sub", date)


def parse_callback_data(data: str) -> tuple[str, str] | None:
    """Return the (action, meetup date) of a button, or None if it is not one of ours."""
    action, sep, date = data.partition(":")
    if not sep or action not in ACTIONS:
        return None
    return action, date


def format_display(date: datetime, fmt: str) -> str:
    """Format a date for people."""
    return date.strftime(fmt)


def parse_display(text: str, fmt: str) -> datetime:
    """Parse a date written by people; raise ValueError if it is not in ``fmt``."""
    return datetime.strptime(text, fmt)


def _keyboard(join: str, leave: str, date: datetime) -> InlineKeyboardMarkup:
    stamp = date.strftime("%Y-%m-%dT%H:%M")
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✔ Unirse",
                    style=KeyboardButtonStyle.GREEN,
                    callback_data=f"{join}:{stamp}",
                ),
                InlineKeyboardButton(
                    text="✖ Salir", style=KeyboardButtonStyle.RED, callback_data=f"{leave}:{stamp}"
                ),
            ]
        ]
    )


def _header(meetup: Meetup, date_fmt: str) -> list[str]:
    lines = [f"📅 *Convocatoria:* `{format_display(meetup.date, date_fmt)}`"]
    if meetup.location:
        lines.append(f"📍 *Lugar:* {_escape(meetup.location)}")
    return lines


def _sorted(names: Iterable[str]) -> list[str]:
    """Sort names the way the club's locale does."""
    return sorted(names, key=functools.cmp_to_key(locale.strcoll))


def _escape(text: str) -> str:
    return _MDV2_RE.sub(r"\\\1", text)


def _latest_score(team: Team, matches: list[Match]) -> int | None:
    """Return the team's score in its latest finished match, or None if it has not played."""
    for match in reversed(matches):
        if match.score is not None and team.name in match.teams:
            return match.score[match.teams.index(team.name)]
    return None
