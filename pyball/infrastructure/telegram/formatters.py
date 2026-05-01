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
"""Message formatters for Telegram bot."""

import functools
import locale
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup
from telegram.constants import KeyboardButtonStyle

from pyball.domain.meetup.models import Meetup

_MDV2_RE = re.compile(r"([_*\[\]()~`>#+=|{}.!\\-])")
_DEFAULT_DATE_FMT = "%Y-%m-%d %H:%M"


def format_display(dt: datetime, fmt: str = _DEFAULT_DATE_FMT) -> str:
    """Format a datetime for user-facing display."""
    return dt.strftime(fmt)


def parse_display(s: str, fmt: str = _DEFAULT_DATE_FMT) -> datetime:
    """Parse a user-facing date string into a datetime."""
    return datetime.strptime(s, fmt)


def _escape_mdv2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return _MDV2_RE.sub(r"\\\1", text)


def build_main_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for main chat."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✔ Unirse",
                    style=KeyboardButtonStyle.GREEN,
                    callback_data=build_callback_data("join", meetup_date),
                ),
                InlineKeyboardButton(
                    text="✖ Salir",
                    style=KeyboardButtonStyle.RED,
                    callback_data=build_callback_data("leave", meetup_date),
                ),
            ]
        ]
    )


def build_subs_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for substitutes chat."""
    return InlineKeyboardMarkup(
        [
            [
                InlineKeyboardButton(
                    text="✔ Unirse",
                    style=KeyboardButtonStyle.GREEN,
                    callback_data=build_callback_data("join_sub", meetup_date),
                ),
                InlineKeyboardButton(
                    text="✖ Salir",
                    style=KeyboardButtonStyle.RED,
                    callback_data=build_callback_data("leave_sub", meetup_date),
                ),
            ]
        ]
    )


def build_callback_data(action: str, meetup_date: datetime) -> str:
    """Build callback data string for inline buttons."""
    return f"{action}:{meetup_date.strftime('%Y-%m-%dT%H:%M')}"


def format_main_message(
    meetup: Meetup,
    player_names: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
    date_fmt: str = _DEFAULT_DATE_FMT,
) -> str:
    """Format message for main (regulars) chat.

    Format varies:
    - Before teams: player list sorted by name
    - After teams: teams only
    - After results: teams + results
    """
    date_str = format_display(meetup.date, date_fmt)
    if meetup.result is not None:
        header = f"🎉 *Partido terminado:* `{date_str}`"
    else:
        header = f"📅 *Convocatoria:* `{date_str}`"
    lines = [header]

    if meetup.location:
        lines.append(f"📍 *Lugar:* {_escape_mdv2(meetup.location)}")

    lines.append("")

    if meetup.teams is None:
        player_names_list = [player_names.get(str(p.value), "") for p in meetup.players]
        sorted_names = sorted(player_names_list, key=functools.cmp_to_key(locale.strcoll))
        max_players = 10
        lines.append(rf"*Jugadores \({len(meetup.players)}/{max_players}\):*")
        for name in sorted_names:
            lines.append(rf"  \- {_escape_mdv2(name)}")
    else:
        lines.append("*Equipos:*")
        team_emojis = ("⚪", "⚫")
        for i, team in enumerate(meetup.teams):
            display_name = team_display_names[i] if i < len(team_display_names) else team.name
            score = None
            if meetup.result is not None:
                score = meetup.result.score_a if i == 0 else meetup.result.score_b
            escaped = _escape_mdv2(display_name)
            emoji = team_emojis[i] if i < len(team_emojis) else ""
            header = (
                rf"{emoji} Equipo *{escaped} \({score}\):*"
                if score is not None
                else f"\n{emoji} *{escaped}:*"
            )
            lines.append(header)
            for player in team.players:
                name = _escape_mdv2(player_names.get(str(player.value), "Unknown"))
                lines.append(rf"  \- {name}")

    if meetup.result is not None and meetup.result.events:
        lines.append("")
        lines.append(r"⏱️ *Goles:*")
        for event in meetup.result.events:
            scorer = _escape_mdv2(player_names.get(str(event.scorer_id.value), "?"))
            minutes = event.timestamp.strftime("%M")
            if event.assistant_id:
                assistant = _escape_mdv2(player_names.get(str(event.assistant_id.value), "?"))
                lines.append(rf"  \- ⚽ {minutes}' {scorer} \({assistant}\)")
            else:
                lines.append(rf"  \- ⚽ {minutes}' {scorer}")

    return "\n".join(lines)


def format_subs_message(
    meetup: Meetup,
    player_names: dict,
    player_groups: dict,
    team_display_names: tuple[str, str] = ("Equipo A", "Equipo B"),
    date_fmt: str = _DEFAULT_DATE_FMT,
) -> str:
    """Format message for substitutes chat - shows substitutes only."""
    if meetup.result is not None:
        return "*Partido terminado*"

    date_str = format_display(meetup.date, date_fmt)

    suplentes = []
    for player_id in meetup.players:
        player_group = player_groups.get(str(player_id.value), "regular")
        if player_group != "regular":
            name = player_names.get(str(player_id.value), "Unknown")
            suplentes.append((player_id, name))

    if meetup.teams is not None and suplentes:
        team_map = {}
        for i, team in enumerate(meetup.teams):
            for player in team.players:
                team_map[str(player.value)] = i

        team_emojis = ("⚪", "⚫")
        subs_by_team: dict[int, list[str]] = {}
        for player_id, name in suplentes:
            team_idx = team_map.get(str(player_id.value), -1)
            if team_idx not in subs_by_team:
                subs_by_team[team_idx] = []
            subs_by_team[team_idx].append(name)

        lines = [rf"*Convocatoria* `{date_str}` \- Suplentes"]
        lines.append(f"Jugadores apuntados {len(meetup.players)}/10")
        lines.append("")

        for team_idx in sorted(subs_by_team.keys()):
            emoji = team_emojis[team_idx] if team_idx < len(team_emojis) else ""
            display_name = (
                f"{team_display_names[team_idx]}:"
                if team_idx < len(team_display_names)
                else f"Equipo {team_idx}:"
            )
            names = ", ".join([_escape_mdv2(player) for player in sorted(subs_by_team[team_idx])])
            lines.append(rf"{emoji} *{display_name}* {names}")

        return "\n".join(lines)

    sorted_suplentes = sorted(
        [name for _, name in suplentes], key=functools.cmp_to_key(locale.strcoll)
    )

    lines = [rf"*Convocatoria* `{date_str}` \- Suplentes"]
    lines.append(f"Jugadores apuntados {len(meetup.players)}/10")
    lines.append("")

    if sorted_suplentes:
        lines.append(rf"*Suplentes \({len(sorted_suplentes)}\):*")
        for name in sorted_suplentes:
            lines.append(rf"  \- {_escape_mdv2(name)}")
    else:
        lines.append("*No hay suplentes*")

    return "\n".join(lines)


def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """Parse callback data. Returns (action, meetup_date_str) or None."""
    if ":" not in callback_data:
        return None
    action, date_str = callback_data.split(":", 1)
    if action not in ("join", "leave", "join_sub", "leave_sub"):
        return None
    return action, date_str
