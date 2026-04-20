from datetime import datetime

import pytest

from pyball.bot.formatters import (
    _escape_mdv2,
    format_main_message,
    format_match_result_message,
    format_subs_message,
)
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId


def test_format_main_message_before_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names)

    assert "*Convocatoria:*" in text
    assert "2024/01/15 20:00" in text
    assert "- Carlos" in text
    assert "- Luis" in text


def test_format_subs_message():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)

    player_names = {str(p1.value): "Pedro"}
    player_groups = {str(p1.value): "substitute"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "Suplentes" in text
    assert "Pedro" in text


def test_format_main_message_all_unmasked():
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    p_regular = PlayerId.generate()
    p_substitute = PlayerId.generate()
    meetup.add_player(p_regular)
    meetup.add_player(p_substitute)

    player_names = {str(p_regular.value): "Mario", str(p_substitute.value): "Luigi"}

    text = format_main_message(meetup, player_names)

    assert "Mario" in text
    assert "Luigi" in text


def test_format_subs_message_masked_regulars():
    meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Parque Central")
    p_regular = PlayerId.generate()
    p_substitute = PlayerId.generate()
    meetup.add_player(p_regular)
    meetup.add_player(p_substitute)

    player_names = {str(p_regular.value): "Mario", str(p_substitute.value): "Luigi"}
    player_groups = {str(p_regular.value): "regular", str(p_substitute.value): "substitute"}

    text = format_subs_message(meetup, player_names, player_groups)

    assert "Mario" not in text
    assert "Luigi" in text


def test_escape_mdv2_special_characters():
    assert _escape_mdv2("Hello (world)") == r"Hello \(world\)"
    assert _escape_mdv2("score: 1.0") == r"score: 1\.0"
    assert _escape_mdv2("player_name") == r"player\_name"


def test_format_main_message_with_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names, team_display_names=("Claro", "Oscuro"))

    assert "*Equipos:*" in text
    assert "Claro" in text
    assert "Oscuro" in text
    assert "Luis" in text or "Carlos" in text


def test_format_main_message_with_teams_shows_custom_display_names():
    """format_main_message uses team_display_names instead of internal 'A'/'B'."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names, team_display_names=("Blancos", "Negros"))

    assert "Blancos" in text
    assert "Negros" in text
    assert "*A:*" not in text
    assert "*B:*" not in text


def test_format_match_result_message_uses_display_names():
    """format_match_result_message uses team_display_names for score line."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    meetup.set_result(MatchResult(score_a=2, score_b=1, events=()))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_match_result_message(
        meetup, player_names, team_display_names=("Claro", "Oscuro")
    )

    assert "Claro" in text
    assert "Oscuro" in text
    assert "*A*" not in text
    assert "*B*" not in text


def test_format_main_message_with_result_shows_score():
    """When meetup has a result, format_main_message shows score next to team name."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    event = GoalEvent(
        scorer_id=p1, assistant_id=None, team="A", timestamp=datetime(2026, 4, 12, 20, 15)
    )
    meetup.set_result(MatchResult(score_a=3, score_b=1, events=(event,)))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_main_message(meetup, player_names, team_display_names=("A", "B"))

    assert "A (3)" in text or r"A \(3\)" in text
    assert "B (1)" in text or r"B \(1\)" in text
    assert "Dani" in text
    assert "Rafa" in text


def test_format_subs_message_with_result_shows_score():
    """When meetup has a result, format_subs_message shows score next to team name."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    meetup.set_result(MatchResult(score_a=2, score_b=0, events=()))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    player_groups = {str(p1.value): "regular", str(p2.value): "regular"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "2" in text
    assert "0" in text
