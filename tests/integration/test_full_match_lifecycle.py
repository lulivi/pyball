"""End-to-end integration test: full match lifecycle."""

# pylint: disable=redefined-outer-name

from datetime import date, datetime, time, timedelta

import pytest

from pyball.domain.meetup.errors import (
    DuplicateMeetupError,
    MeetupAlreadyClosedError,
    PlayerNotInMeetupError,
)
from pyball.domain.meetup.season import _season_start

# A fixed point ~2 weeks into the current season, so season-scoped stats
# assertions stay valid no matter when the suite runs.
_MATCH_DATE = datetime.combine(_season_start(date.today()) + timedelta(days=14), time(20, 0))
_ISO_DATE = _MATCH_DATE.strftime("%Y-%m-%dT%H:%M")

_REGULARS = [f"Regular_{i:02d}" for i in range(1, 11)]  # Regular_01..Regular_10
_SUBS = [f"Sub_{i:02d}" for i in range(1, 5)]  # Sub_01..Sub_04


class TestFullMatchLifecycle:
    """Full match lifecycle from player creation to stats."""

    @pytest.mark.asyncio
    async def test_full_lifecycle(self, real_container):
        """Happy path: create players → meetup → add/remove → search → teams → match → stats."""
        await self._create_players(real_container)
        await self._create_meetup(real_container)
        await self._add_players(real_container)
        await self._remove_player(real_container)
        await self._search_substitutes(real_container)
        await self._generate_teams_twice(real_container)
        await self._finish_match(real_container)
        self._verify_stats(real_container)

    # ------------------------------------------------------------------
    # Phase helpers
    # ------------------------------------------------------------------

    async def _create_players(self, real_container):
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
            player = real_container.player_repository.find_by_name(name)
            real_container.add_player_to_meetup_by_id().execute(_MATCH_DATE, player.id)

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 10

    async def _remove_player(self, real_container):
        player = real_container.player_repository.find_by_name("Regular_10")
        real_container.remove_player_from_meetup_by_id().execute(_MATCH_DATE, player.id)

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

    async def _search_substitutes(self, real_container):
        meetup = real_container.open_substitute_search().execute(_MATCH_DATE)
        assert meetup.substitute_search

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

    def _verify_stats(self, real_container):
        report = real_container.compute_stats().execute()
        assert len(report.season.players) > 0

    # ------------------------------------------------------------------
    # Edge cases: player management
    # ------------------------------------------------------------------

    @pytest.mark.asyncio
    async def test_add_player_already_enrolled(self, real_container):
        """Adding an already-enrolled player is a no-op — count stays the same."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        player = real_container.player_repository.find_by_name("Regular_01")
        real_container.add_player_to_meetup_by_id().execute(_MATCH_DATE, player.id)
        real_container.add_player_to_meetup_by_id().execute(_MATCH_DATE, player.id)

        meetup = real_container.meetup_repository.find_by_datetime(_MATCH_DATE)
        assert len(meetup.players) == 1

    @pytest.mark.asyncio
    async def test_remove_player_not_enrolled(self, real_container):
        """Removing a player not in the meetup raises PlayerNotInMeetupError."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")

        player = real_container.player_repository.find_by_name("Regular_01")
        with pytest.raises(PlayerNotInMeetupError):
            real_container.remove_player_from_meetup_by_id().execute(_MATCH_DATE, player.id)

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
            player = real_container.player_repository.find_by_name(f"Player_{i:02d}")
            real_container.add_player_to_meetup_by_id().execute(_MATCH_DATE, player.id)
        real_container.create_teams(None).execute(_MATCH_DATE, 2)

        events = [
            {"scorer": "Player_01", "assistant": None, "team": "A", "timestamp": "20:30:00"},
        ]
        final_score = {"A": 1, "B": 0}
        real_container.finish_match().execute(_ISO_DATE, events, final_score)

        with pytest.raises(MeetupAlreadyClosedError):
            real_container.finish_match().execute(_ISO_DATE, events, final_score)

    def test_stats_no_closed_matches(self, real_container):
        """With no closed match, the season stats are empty."""
        real_container.create_player().execute("Regular_01", "regular")
        real_container.create_meetup().execute(_MATCH_DATE, "Test Field")
        player = real_container.player_repository.find_by_name("Regular_01")
        real_container.add_player_to_meetup_by_id().execute(_MATCH_DATE, player.id)

        assert len(real_container.compute_stats().execute().season.players) == 0
