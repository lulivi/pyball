from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import PlayerId


def format_main_message(
    meetup: Meetup, player_names: dict, player_groups: dict | None = None
) -> str:
    """Format message for main (regulars) chat.

    Format varies:
    - Before teams: player list only
    - After teams: teams only
    - After results: teams + results
    """
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [f"*Convocatoria* {date_str}"]

    if meetup.location:
        lines.append(f"Lugar: *{meetup.location}*")

    lines.append("")

    if meetup.teams is None:
        max_players = 10
        lines.append(f"*Jugadores ({len(meetup.players)}/{max_players}):*")
        for i, player_id in enumerate(meetup.players, 1):
            name = player_names.get(str(player_id.value), "Unknown")
            lines.append(f"{i}. {name}")
    else:
        lines.append("*Equipos:*")
        for team in meetup.teams:
            player_list = ", ".join(
                player_names.get(str(p.value), "Unknown") for p in team.players
            )
            lines.append(f"{team.name}: {player_list}")

    return "\n".join(lines)


def format_subs_message(
    meetup: Meetup, player_names: dict, player_groups: dict | None = None
) -> str:
    """Format message for substitutes chat - regulars masked when player_groups provided."""
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [f"*Convocatoria* {date_str} - Suplentes"]
    lines.append("")

    lines.append(f"*Suplentes ({len(meetup.players)}):*")
    for i, player_id in enumerate(meetup.players, 1):
        if player_groups is not None:
            group = player_groups.get(str(player_id.value), "regular")
            if group == "regular":
                lines.append(f"{i}. ---------")
                continue
        name = player_names.get(str(player_id.value), "Unknown")
        lines.append(f"{i}. {name}")

    return "\n".join(lines)


def build_callback_data(action: str, meetup_date: datetime) -> str:
    """Build callback data: action:YYYY-MM-DDTHH:MM"""
    return f"{action}:{meetup_date.strftime('%Y-%m-%dT%H:%M')}"


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


def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """Parse callback data. Returns (action, meetup_date_str) or None."""
    if ":" not in callback_data:
        return None
    action, date_str = callback_data.split(":", 1)
    if action not in ("join", "leave", "join_sub", "leave_sub"):
        return None
    return action, date_str
