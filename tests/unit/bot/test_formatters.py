from datetime import datetime

import pytest

from pyball.bot.formatters import _escape_mdv2, format_main_message, format_subs_message
from pyball.domain.meetup.models import Meetup, Team
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
    assert "15/Jan/2024 20:00" in text
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
    meetup.create_random_teams()

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names)

    assert "*Equipos:*" in text
    assert "Luis" in text or "Carlos" in text
