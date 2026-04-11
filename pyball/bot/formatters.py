"""Message formatters for Telegram bot."""

import functools
import html
import locale

from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import PlayerId

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass


def build_main_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for main chat."""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Unirse", callback_data=build_callback_data("join", meetup_date)
            ),
            InlineKeyboardButton(
                "❌ Salir", callback_data=build_callback_data("leave", meetup_date)
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_subs_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for substitutes chat."""
    keyboard = [
        [
            InlineKeyboardButton(
                "✅ Unirse", callback_data=build_callback_data("join_sub", meetup_date)
            ),
            InlineKeyboardButton(
                "❌ Salir", callback_data=build_callback_data("leave_sub", meetup_date)
            ),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)


def build_callback_data(action: str, meetup_date: datetime) -> str:
    """Build callback data string for inline buttons."""
    return f"{action}:{meetup_date.strftime('%Y-%m-%dT%H:%M')}"


def format_main_message(meetup: Meetup, player_names: dict, player_groups: dict) -> str:
    """Format message for main (regulars) chat.

    Format varies:
    - Before teams: player list sorted by name
    - After teams: teams only
    - After results: teams + results
    """
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [f"*Convocatoria:* {date_str}"]

    if meetup.location:
        escaped_location = html.escape(meetup.location)
        lines.append(f"*Lugar:* {escaped_location}")

    lines.append("")

    if meetup.teams is None:
        player_names_list = [player_names.get(str(p.value), "") for p in meetup.players]
        sorted_names = sorted(player_names_list, key=functools.cmp_to_key(locale.strcoll))
        max_players = 10
        lines.append(rf"*Jugadores \({len(meetup.players)}/{max_players}\):*")
        for name in sorted_names:
            escaped_name = html.escape(name)
            lines.append(rf"\- {escaped_name}")
    else:
        lines.append("*Equipos:*")
        for team in meetup.teams:
            player_list = "\n".join(
                player_names.get(rf"- `{player.value}`", r"\- Unknown") for player in team.players
            )
            lines.append(rf"*{team.name}*:\n\- {player_list}")

    return "\n".join(lines)


def format_subs_message(meetup: Meetup, player_names: dict, player_groups: dict) -> str:
    """Format message for substitutes chat - shows substitutes only."""
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [rf"*Convocatoria* {date_str} \- Suplentes"]
    lines.append("")

    suplentes = []
    for player_id in meetup.players:
        name = player_names.get(str(player_id.value), "Unknown")
        group = player_groups.get(str(player_id.value), "regular")
        if group != "regular":
            suplentes.append(name)

    sorted_suplentes = sorted(suplentes, key=functools.cmp_to_key(locale.strcoll))

    if sorted_suplentes:
        lines.append(rf"*Suplentes \({len(sorted_suplentes)}\):*")
        for name in sorted_suplentes:
            escaped_name = html.escape(name)
            lines.append(rf"\- {escaped_name}")
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
