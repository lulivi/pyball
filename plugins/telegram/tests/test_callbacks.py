"""Tests for the join/leave buttons."""

# pylint: disable=redefined-outer-name,too-many-arguments,too-many-positional-arguments

from unittest.mock import AsyncMock, MagicMock

import pytest

from pyball_telegram.callbacks import button_pressed
from pyball_telegram.state import LinkStore
from tests.conftest import LUIS, SUB, meetup


def _press(data, user_id=7):
    query = MagicMock(data=data, answer=AsyncMock())
    query.from_user.id = user_id
    return MagicMock(callback_query=query), query


@pytest.fixture
def context(callups):
    """A handler context holding the callups."""
    return MagicMock(bot_data={"callups": callups})


@pytest.fixture
def found(core):
    """The meetup of the buttons, found by its date."""
    core.routes[("GET", "/api/v1/meetups")] = [meetup()]


@pytest.mark.asyncio
@pytest.mark.usefixtures("found")
async def test_a_linked_player_joins_through_the_api(context, callups, core):
    """join adds the linked player; the event refreshes the callups later."""
    LinkStore(callups.config.mapping_file).link(7, SUB)
    core.routes[("PUT", f"/api/v1/meetups/m1/players/{SUB}")] = meetup(players=[LUIS, SUB])
    update, query = _press("join:2026-11-25T20:00")

    await button_pressed(update, context)

    assert ("GET", "/api/v1/meetups?date=2026-11-25T20%3A00%3A00") in core.calls
    assert ("PUT", f"/api/v1/meetups/m1/players/{SUB}") in core.calls
    query.answer.assert_awaited_once_with()


@pytest.mark.asyncio
@pytest.mark.usefixtures("found")
@pytest.mark.parametrize(
    ("data", "linked", "reply"),
    [
        ("join:2026-11-25T20:00", None, "No tienes ningún jugador vinculado"),
        ("join:2026-11-25T20:00", LUIS, "Ya estás unido"),
        ("leave:2026-11-25T20:00", SUB, "No estás en este meetup"),
        ("join_sub:2026-11-25T20:00", SUB, "búsqueda de suplentes está cerrada"),
        ("join:2026-11-25T20:00", "not-a-uuid", "Vinculación de jugador no válida"),
        ("dance:2026-11-25T20:00", None, "Datos de acción no válidos"),
        ("join:yesterday", None, "Formato de fecha no válido"),
    ],
)
async def test_refusals_explain_themselves(context, callups, core, data, linked, reply):
    """Each refusal answers with its alert and changes nothing."""
    if linked:
        LinkStore(callups.config.mapping_file).link(7, linked)
    update, query = _press(data)

    await button_pressed(update, context)

    assert reply in query.answer.call_args.args[0]
    assert not any(method == "PUT" for method, _ in core.calls)


@pytest.mark.asyncio
async def test_buttons_of_a_meetup_with_teams_do_nothing(context, callups, core):
    """Once teams exist, signup is closed."""
    team = {"name": "A", "color": "blanco", "emoji": "⚪", "players": [LUIS], "goalkeeper": None}
    core.routes[("GET", "/api/v1/meetups")] = [meetup(teams=[team, team | {"name": "B"}])]
    LinkStore(callups.config.mapping_file).link(7, LUIS)
    update, query = _press("leave:2026-11-25T20:00")

    await button_pressed(update, context)

    assert "Los equipos ya están hechos" in query.answer.call_args.args[0]
