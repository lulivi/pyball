"""Tests for the callup messages; their text matches what the core's bot posted."""

from pyball_telegram.formatters import escape_summary, format_main_message, format_subs_message
from tests.conftest import LUIS, SUB, meetup, parse

NAMES = {LUIS: "Luis", SUB: "Manu (Sub)"}
GROUPS = {LUIS: "regular", SUB: "substitute"}
FMT = "%Y-%m-%d %H:%M"


def _teams(scores=None):
    teams = [
        {"name": "A", "color": "blanco", "emoji": "⚪", "players": [LUIS], "goalkeeper": None},
        {"name": "B", "color": "amarillo", "emoji": "🟡", "players": [SUB], "goalkeeper": None},
    ]
    matches = [{"teams": ["A", "B"], "score": scores}] if scores else []
    return parse(meetup(players=[LUIS, SUB], teams=teams, matches=matches))


def test_open_meetup_lists_the_players():
    """Before teams: date, escaped location and the players over the capacity."""
    text = format_main_message(parse(meetup(location="Campo (Norte)")), NAMES, FMT, "")
    assert text == (
        "📅 *Convocatoria:* `2026-11-25 20:00`\n"
        "📍 *Lugar:* Campo \\(Norte\\)\n\n"
        "*Jugadores \\(1/10\\):*\n"
        "  \\- `Luis`"
    )


def test_teams_show_their_club_color_and_latest_score():
    """With teams, each one under its color; with a result, its score."""
    assert "⚪ *Blanco:*" in format_main_message(_teams(), NAMES, FMT, "")
    text = format_main_message(_teams([2, 1]), NAMES, FMT, "")
    assert "⚪ Equipo *Blanco \\(2\\):*" in text
    assert "🟡 Equipo *Amarillo \\(1\\):*" in text


def test_closed_meetup_shows_the_core_summary_escaped():
    """Once closed, the message is the core's summary with its bold spans kept."""
    text = format_main_message(parse(meetup(closed=True)), NAMES, FMT, "⚪ *Blanco - 2*\nAna.")
    assert text == "⚪ *Blanco \\- 2*\nAna\\."
    assert escape_summary("*A:* (x)") == "*A:* \\(x\\)"


def test_substitutes_message_follows_the_search():
    """Open search: count over capacity; closed and full: Completo; subs listed by team."""
    searching = parse(meetup(players=[LUIS, SUB], substitute_search=True))
    text = format_subs_message(searching, NAMES, GROUPS, FMT)
    assert "Jugadores apuntados 2/10" in text
    assert "*Suplentes \\(1\\):*\n  \\- `Manu (Sub)`" in text

    full = parse(meetup(players=[LUIS] * 10))
    text = format_subs_message(full, NAMES, GROUPS, FMT)
    assert text.endswith("✅ *Completo* \\(10 jugadores\\)")

    assert "🟡 *Amarillo:* `Manu (Sub)`" in format_subs_message(_teams(), NAMES, GROUPS, FMT)
    assert format_subs_message(parse(meetup(closed=True)), NAMES, GROUPS, FMT) == (
        "*Partido terminado*"
    )
