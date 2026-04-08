from datetime import datetime

import pytest

from pyball.bot.formatters import format_main_message, format_subs_message
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import PlayerId


def test_format_main_message_before_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_regular(p1)
    meetup.add_regular(p2)

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names)

    assert "*Convocatoria*" in text
    assert "15/Jan/2024 20:00" in text
    assert "Luis" in text
    assert "Carlos" in text


def test_format_subs_message():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
    p1 = PlayerId.generate()
    meetup.add_substitute(p1)

    player_names = {str(p1.value): "Pedro"}
    text = format_subs_message(meetup, player_names)

    assert "Suplentes" in text
    assert "Pedro" in text
