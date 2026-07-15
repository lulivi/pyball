"""End-to-end integration test: full match lifecycle."""

# pylint: disable=redefined-outer-name

from datetime import datetime

import pytest

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupAlreadyClosedError,
    PlayerNotInMeetupError,
)
from pyball.infrastructure.images.stats_renderer import StatsHtmlRenderer
from pyball.infrastructure.telegram.bot.handlers.meetup import search_handler, stats_handler

_DATE_ARGS = ["2026-06-15", "20:00"]
_ISO_DATE = "2026-06-15T20:00"
_MATCH_DATE = datetime(2026, 6, 15, 20, 0)

_REGULARS = [f"Regular_{i:02d}" for i in range(1, 11)]  # Regular_01..Regular_10
_SUBS = [f"Sub_{i:02d}" for i in range(1, 5)]  # Sub_01..Sub_04


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
        """Happy path: create players → meetup → add/remove → search → teams → match → stats."""
        await self._create_players(bot_update, bot_context, real_container)
        await self._create_meetup(real_container)
        await self._add_players(real_container)
        await self._remove_player(real_container)
        await self._search_substitutes(bot_update, bot_context)
        await self._generate_teams_twice(real_container)
        await self._finish_match(real_container)
        await self._verify_stats(bot_update, bot_context, real_container, monkeypatch)

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------

    # pylint: disable-next=unused-argument
    async def _create_players(self, bot_update, bot_context, real_container):
        for name in _REGULARS:
            real_container.create_player().execute(name, "regular")
        for name in _SUBS:
            real_container.create_player().execute(name, "substitute")

        all_players = real_container.player_repository.find_all()
        assert len(all_players) == 14

    async def _create_meetup(self, real_container):
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert meetup is not None
        assert meetup.location == "Test Field"

    async def _add_players(self, real_container):
        for name in _REGULARS:
            real_container.add_player_to_meetup().execute(_MATCH_DATE, name)

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 10

    async def _remove_player(self, real_container):
        real_container.remove_player_from_meetup().execute(_MATCH_DATE, "Regular_10")

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 9

    async def _generate_teams_twice(self, real_container):
        real_container.create_teams(None).execute(_MATCH_DATE, 2)

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert meetup.teams is not None
        assert len(meetup.teams) == 2

        real_container.create_teams(None).execute(_MATCH_DATE, 2)

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert meetup.teams is not None
        assert meetup.current_match() is not None

    async def _search_substitutes(self, bot_update, bot_context):
        bot_update.message.reply_text.reset_mock()
        bot_context.bot.send_message.reset_mock()
        bot_context.args = _DATE_ARGS
        await search_handler(bot_update, bot_context)

        bot_context.bot.send_message.assert_called_once()
        bot_context.bot.set_message_reaction.assert_called()
        bot_update.message.reply_text.assert_not_called()

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

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert meetup.is_closed()
        result = meetup.matches[-1].result
        assert result.score_a == 2
        assert result.score_b == 1
        assert len(result.events) == 3

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

    # ------------------------------------------------------------------
    # Edge cases: player management
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_add_player_already_enrolled(self, real_container):
        """Adding an already-enrolled player is a no-op — count stays the same."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        real_container.add_player_to_meetup().execute(_MATCH_DATE, "Regular_01")
        real_container.add_player_to_meetup().execute(_MATCH_DATE, "Regular_01")

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 1

    @pytest.mark.asyncio
    async def test_remove_player_not_enrolled(self, real_container):
        """Removing a player not in the meetup raises PlayerNotInMeetupError."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        with pytest.raises(PlayerNotInMeetupError):
            real_container.remove_player_from_meetup().execute(_MATCH_DATE, "Regular_01")

    # ------------------------------------------------------------------
    # Edge cases: fuzzy matching
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_add_player_fuzzy_name(self, real_container):
        """A one-character typo in the name is resolved by fuzzy matching."""
        real_container.create_player().execute("Regular_03", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        real_container.add_player_to_meetup().execute(_MATCH_DATE, "Regulr_03")  # missing 'a'

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 1

    @pytest.mark.asyncio
    async def test_add_player_unknown_name(self, real_container):
        """An unrecognisable name raises ValueError from fuzzy matching."""
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        with pytest.raises(ValueError):
            real_container.add_player_to_meetup().execute(_MATCH_DATE, "NameThatDoesNotExist")

    # ------------------------------------------------------------------
    # Edge cases: meetup lifecycle errors
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_create_duplicate_meetup(self, real_container):
        """Creating a meetup on an already-taken date raises DuplicateMeetupError."""
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        with pytest.raises(DuplicateMeetupError):
            real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

    @pytest.mark.asyncio
    async def test_finish_already_closed_match(self, real_container):
        """Calling finish_match twice on the same meetup raises MeetupAlreadyClosedError."""
        for i in range(1, 5):
            real_container.create_player().execute(f"Player_{i:02d}", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")
        for i in range(1, 5):
            real_container.add_player_to_meetup().execute(_MATCH_DATE, f"Player_{i:02d}")
        real_container.create_teams(None).execute(_MATCH_DATE, 2)

        events = [
            {"scorer": "Player_01", "assistant": None, "team": "A", "timestamp": "20:30:00"},
        ]
        final_score = {"A": 1, "B": 0}
        real_container.finish_match().execute(_ISO_DATE, events, final_score)

        with pytest.raises(MeetupAlreadyClosedError):
            real_container.finish_match().execute(_ISO_DATE, events, final_score)

    @pytest.mark.asyncio
    async def test_stats_no_closed_matches(
        self, bot_update, bot_context, real_container, monkeypatch
    ):
        """stats_handler with no closed matches still sends a photo (empty report)."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")
        real_container.add_player_to_meetup().execute(_MATCH_DATE, "Regular_01")

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
        assert len(captured["report"].season.players) == 0
