"""Message formatters for Telegram bot."""

import functools
import locale
import re
from datetime import datetime

from telegram import InlineKeyboardButton, InlineKeyboardMarkup

from pyball.domain.meetup.models import Meetup

try:
    locale.setlocale(locale.LC_ALL, "")
except locale.Error:
    pass

_MDV2_RE = re.compile(r"([_*\[\]()~`>#+=|{}.!\\-])")


def _escape_mdv2(text: str) -> str:
    """Escape special characters for Telegram MarkdownV2."""
    return _MDV2_RE.sub(r"\\\1", text)


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


def format_main_message(
    meetup: Meetup,
    player_names: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
) -> str:
    """Format message for main (regulars) chat.

    Format varies:
    - Before teams: player list sorted by name
    - After teams: teams only
    - After results: teams + results
    """
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
    lines = [f"*Convocatoria:* `{date_str}`"]

    if meetup.location:
        lines.append(f"*Lugar:* {_escape_mdv2(meetup.location)}")

    lines.append("")

    if meetup.teams is None:
        player_names_list = [player_names.get(str(p.value), "") for p in meetup.players]
        sorted_names = sorted(player_names_list, key=functools.cmp_to_key(locale.strcoll))
        max_players = 10
        lines.append(rf"*Jugadores \({len(meetup.players)}/{max_players}\):*")
        for name in sorted_names:
            lines.append(rf"\- {_escape_mdv2(name)}")
    else:
        lines.append("*Equipos:*")
        for i, team in enumerate(meetup.teams):
            display_name = team_display_names[i] if i < len(team_display_names) else team.name
            score = None
            if meetup.result is not None:
                score = meetup.result.score_a if i == 0 else meetup.result.score_b
            escaped = _escape_mdv2(display_name)
            header = rf"*{escaped} \({score}\):*" if score is not None else f"\n*{escaped}:*"
            lines.append(header)
            for player in team.players:
                name = _escape_mdv2(player_names.get(str(player.value), "Unknown"))
                lines.append(rf"\- {name}")

    return "\n".join(lines)


def format_subs_message(meetup: Meetup, player_names: dict, player_groups: dict) -> str:
    """Format message for substitutes chat - shows substitutes only."""
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
    if meetup.result is not None:
        score_line = rf"{meetup.result.score_a} \- {meetup.result.score_b}"
        lines = [rf"*Convocatoria* `{date_str}` \- Suplentes \| {score_line}"]
    else:
        lines = [rf"*Convocatoria* `{date_str}` \- Suplentes"]
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
            lines.append(rf"\- {_escape_mdv2(name)}")
    else:
        lines.append("*No hay suplentes*")

    return "\n".join(lines)


def format_match_result_message(
    meetup: Meetup,
    player_names: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
) -> str:
    """Format a match-finished announcement message.

    Intended to be sent as a new message (not an edit) after the match ends.
    """
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
    assert meetup.result is not None
    assert meetup.teams is not None

    score_a = meetup.result.score_a
    score_b = meetup.result.score_b
    name_a = _escape_mdv2(team_display_names[0])
    name_b = _escape_mdv2(team_display_names[1])

    lines = [
        rf"⚽ *Partido terminado* — `{date_str}`",
        "",
        rf"*{name_a}* {score_a} \- {score_b} *{name_b}*",
    ]

    if meetup.result.events:
        lines.append("")
        lines.append(r"📋 *Goles:*")
        for event in meetup.result.events:
            scorer = _escape_mdv2(player_names.get(str(event.scorer_id.value), "?"))
            # Map "A" -> team_display_names[0], "B" -> team_display_names[1]
            if event.team == "A":
                team = _escape_mdv2(team_display_names[0])
            elif event.team == "B":
                team = _escape_mdv2(team_display_names[1])
            else:
                team = _escape_mdv2(event.team)
            
            if event.assistant_id:
                assistant = _escape_mdv2(player_names.get(str(event.assistant_id.value), "?"))
                lines.append(rf"\- ⚽ {scorer} \(asist: {assistant}\) \[{team}\]")
            else:
                lines.append(rf"\- ⚽ {scorer} \[{team}\]")

    return "\n".join(lines)


def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """Parse callback data. Returns (action, meetup_date_str) or None."""
    if ":" not in callback_data:
        return None
    action, date_str = callback_data.split(":", 1)
    if action not in ("join", "leave", "join_sub", "leave_sub"):
        return None
    return action, date_str
