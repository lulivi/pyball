"""End-to-end integration test: full match lifecycle."""

# pylint: disable=redefined-outer-name

from datetime import date

import pytest

from pyball.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    new_meetup_handler,
    remove_player_handler,
    search_handler,
    start_match_handler,
    stats_handler,
)
from pyball.bot.handlers.player import new_player_handler
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer

_DATE_ARGS = ["2026/06/15", "20:00"]
_ISO_DATE = "2026-06-15T20:00"
_MATCH_DATE = date(2026, 6, 15)

_REGULARS = [f"Regular_{i:02d}" for i in range(1, 11)]  # Regular_01..Regular_10
_SUBS = [f"Sub_{i:02d}" for i in range(1, 5)]  # Sub_01..Sub_04


@pytest.mark.e2e
class TestFullMatchLifecycle:
    """Full match lifecycle from player creation to stats."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(
        self,
        bot_update,
        bot_context,
        real_container,
        monkeypatch,
    ):
        """Happy path: create players → meetup → add/remove → teams → match → stats."""
        await self._create_players(bot_update, bot_context, real_container)
        await self._create_meetup(bot_update, bot_context, real_container)
        await self._add_players(bot_update, bot_context, real_container)
        await self._remove_player(bot_update, bot_context, real_container)
        await self._generate_teams_twice(bot_update, bot_context, real_container)
        await self._search_substitutes(bot_update, bot_context)
        await self._start_match(bot_update, bot_context)
        await self._finish_match(real_container)
        await self._verify_stats(bot_update, bot_context, real_container, monkeypatch)

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------

    async def _create_players(self, bot_update, bot_context, real_container):
        for name in _REGULARS:
            bot_context.args = [name, "regular"]
            await new_player_handler(bot_update, bot_context)
        for name in _SUBS:
            bot_context.args = [name, "substitute"]
            await new_player_handler(bot_update, bot_context)

        all_players = real_container.player_repository.find_all()
        assert len(all_players) == 14

    async def _create_meetup(self, bot_update, bot_context, real_container):
        bot_context.args = _DATE_ARGS
        await new_meetup_handler(bot_update, bot_context)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert meetup is not None
        assert meetup.location == "Test Field"

    async def _add_players(self, bot_update, bot_context, real_container):
        for name in _REGULARS:
            bot_context.args = [*_DATE_ARGS, name]
            await add_player_handler(bot_update, bot_context)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert len(meetup.players) == 10

    async def _remove_player(self, bot_update, bot_context, real_container):
        bot_context.args = [*_DATE_ARGS, "Regular_10"]
        await remove_player_handler(bot_update, bot_context)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert len(meetup.players) == 9

    async def _generate_teams_twice(self, bot_update, bot_context, real_container):
        bot_context.args = _DATE_ARGS
        await create_teams_handler(bot_update, bot_context)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert meetup.teams is not None
        assert len(meetup.teams) == 2

        bot_update.message.reply_text.reset_mock()
        bot_context.args = _DATE_ARGS
        await create_teams_handler(bot_update, bot_context)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert meetup.teams is not None
        call = bot_update.message.reply_text.call_args
        text = call.kwargs.get("text") or (call.args[0] if call.args else "")
        assert "Equipos creados" in text

    async def _search_substitutes(self, bot_update, bot_context):
        bot_update.message.reply_text.reset_mock()
        bot_context.bot.send_message.reset_mock()
        bot_context.args = _DATE_ARGS
        await search_handler(bot_update, bot_context)

        bot_context.bot.send_message.assert_called_once()
        call = bot_update.message.reply_text.call_args
        text = call.kwargs.get("text") or (call.args[0] if call.args else "")
        assert "Substitutes message sent" in text

    async def _start_match(self, bot_update, bot_context):
        bot_update.message.reply_text.reset_mock()
        bot_context.bot.send_photo.reset_mock()
        bot_context.args = _DATE_ARGS
        await start_match_handler(bot_update, bot_context)

        bot_context.bot.send_photo.assert_called_once()
        caption = bot_context.bot.send_photo.call_args.kwargs.get("caption", "")
        assert "2026-06-15" in caption

    async def _finish_match(self, real_container):
        events = [
            {
                "scorer": "Regular_01",
                "assistant": "Regular_02",
                "team": "A",
                "timestamp": "20:30:00",
            },
            {
                "scorer": "Regular_03",
                "assistant": None,
                "team": "A",
                "timestamp": "21:00:00",
            },
            {
                "scorer": "Regular_04",
                "assistant": None,
                "team": "B",
                "timestamp": "21:15:00",
            },
        ]
        final_score = {"A": 2, "B": 1}
        real_container.finish_match().execute(_ISO_DATE, events, final_score)

        meetup = real_container.meetup_repository.find_by_date(_MATCH_DATE)
        assert meetup.is_closed()
        assert meetup.result.score_a == 2
        assert meetup.result.score_b == 1
        assert len(meetup.result.events) == 3

    async def _verify_stats(self, bot_update, bot_context, _real_container, monkeypatch):
        fake_png = b"\x89PNG\r\n\x1a\n"
        captured = {}

        async def fake_render(_self, report, scope="season"):  # pylint: disable=unused-argument
            captured["report"] = report
            return fake_png

        monkeypatch.setattr(StatsHtmlRenderer, "render", fake_render)
        bot_context.bot.send_photo.reset_mock()
        bot_context.args = ["temporada"]
        await stats_handler(bot_update, bot_context)

        bot_context.bot.send_photo.assert_called_once()
        assert "report" in captured
        assert len(captured["report"].season.players) > 0
