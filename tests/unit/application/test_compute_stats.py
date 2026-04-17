"""Tests for ComputeStats use case."""

from datetime import datetime
from unittest.mock import MagicMock

from pyball.application.meetup.compute_stats import ComputeStats, StatsReport
from pyball.domain.meetup.models import GoalEvent, MatchResult, Meetup, PlayerId, Team
from pyball.domain.player.models import Player


def make_player(name: str) -> Player:
    """Create a player with a generated ID."""
    return Player.create(name=name, group="regular")


def make_meetup(  # pylint: disable=too-many-arguments,too-many-positional-arguments
    date_: datetime,
    team_a: list[PlayerId],
    team_b: list[PlayerId],
    score_a: int,
    score_b: int,
    events: list[GoalEvent] | None = None,
) -> Meetup:
    """Create a finished meetup with teams and result."""
    meetup = Meetup.create(date=date_, location="Test Park")
    for pid in team_a + team_b:
        meetup.add_player(pid)
    meetup.teams = [Team.create("A", team_a), Team.create("B", team_b)]
    meetup.set_result(MatchResult(score_a=score_a, score_b=score_b, events=tuple(events or [])))
    return meetup


def make_repos(meetups, players):
    """Return (meetup_repo, player_repo) fakes."""
    meetup_repo = MagicMock()
    meetup_repo.find_all.return_value = meetups
    player_repo = MagicMock()
    player_repo.find_all.return_value = players
    return meetup_repo, player_repo


class TestComputeStatsEmpty:
    """Edge cases: empty or unfinished meetups."""

    def test_no_meetups_returns_empty_scopes(self):
        """No meetups → empty player and chemistry lists in both scopes."""
        meetup_repo, player_repo = make_repos([], [])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert isinstance(report, StatsReport)
        assert not report.all_time.players
        assert not report.season.players
        assert not report.all_time.chemistry

    def test_meetup_without_result_is_excluded(self):
        """Meetups with no result set are ignored."""
        player = make_player("Alice")
        meetup = Meetup.create(date=datetime(2026, 1, 10, 20, 0), location="Park")
        meetup.add_player(player.id)
        meetup_repo, player_repo = make_repos([meetup], [player])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert not report.all_time.players


class TestComputeStatsGoalsAndAssists:
    """Goal and assist counting."""

    def test_goal_increments_scorer(self):
        """A goal event increments the scorer's goal count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals == 1

    def test_assist_increments_assistant(self):
        """A goal event with an assistant increments the assistant's assist count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=bob.id,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert bob_stats.assists == 1

    def test_no_assist_does_not_crash(self):
        """A goal event with no assistant is handled cleanly."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals == 1
        assert alice_stats.assists == 0


class TestComputeStatsWinDrawLoss:
    """Win, draw, loss counting per player."""

    def test_team_a_win(self):
        """Team A players get a win when score_a > score_b."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 2, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert alice_stats.wins == 1 and alice_stats.losses == 0
        assert bob_stats.losses == 1 and bob_stats.wins == 0

    def test_team_b_win(self):
        """Team B players get a win when score_b > score_a."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 3)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert bob_stats.wins == 1
        assert alice_stats.losses == 1

    def test_draw(self):
        """Both teams get a draw when scores are equal."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        for p in report.all_time.players:
            assert p.draws == 1 and p.wins == 0 and p.losses == 0

    def test_points_calculation(self):
        """Points = wins*3 + draws."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins one, draws one → 3 + 1 = 4 pts
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 2, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points == 4

    def test_players_sorted_by_points_desc(self):
        """Players list is sorted by points descending."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins, Bob loses
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert report.all_time.players[0].player_name == "Alice"


class TestComputeStatsSeasonFilter:
    """Season boundary filtering."""

    def test_meetup_in_season_is_included(self):
        """A meetup after season start (Sep 1 of current year) is in the season scope."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Season 2025/2026: starts 2025-09-01
        meetup = make_meetup(datetime(2025, 10, 5, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.season.players) > 0

    def test_meetup_before_season_excluded_from_season(self):
        """A meetup before season start is excluded from season scope but not all-time."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # On test date 2026-04-13, season starts 2025-09-01, so 2024-05-01 is excluded
        meetup = make_meetup(datetime(2024, 5, 1, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.season.players) == 0
        assert len(report.all_time.players) > 0


class TestComputeStatsChemistry:
    """Chemistry pair counting."""

    def test_chemistry_pair_counted(self):
        """A scorer+assistant pair increments the chemistry count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=bob.id,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.chemistry) == 1
        pair = report.all_time.chemistry[0]
        assert pair.scorer_name == "Alice"
        assert pair.assistant_name == "Bob"
        assert pair.count == 1

    def test_chemistry_no_pair_when_no_assistant(self):
        """A goal without an assistant does not create a chemistry pair."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=datetime(2026, 1, 10, 20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert not report.all_time.chemistry

    def test_chemistry_top_10_only(self):
        """Only the top 10 chemistry pairs by count are returned."""
        # Create 11 different scorer+assistant pairs
        players = [make_player(f"Player{i}") for i in range(22)]
        meetups = []
        day_counter = 1
        for i in range(11):
            scorer = players[i * 2]
            assistant = players[i * 2 + 1]
            # Pair i appears (i+1) times across (i+1) meetups
            for _j in range(i + 1):
                event = GoalEvent(
                    scorer_id=scorer.id,
                    assistant_id=assistant.id,
                    team="A",
                    timestamp=datetime(2026, 1, 10, 20, 5),
                )
                m = make_meetup(
                    datetime(2026, 3, day_counter, 20, 0),
                    [scorer.id, assistant.id],
                    [players[0].id],
                    1,
                    0,
                    [event],
                )
                meetups.append(m)
                day_counter = (day_counter % 28) + 1
        meetup_repo, player_repo = make_repos(meetups, players)
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.chemistry) == 10


class TestComputeStatsRankDelta:
    """Rank delta computation (trend indicators)."""

    def test_rank_delta_none_when_only_one_meetup(self):
        """With only one finished meetup there is no previous ranking — all deltas are None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        for p in report.all_time.players:
            assert p.points_rank_delta is None

    def test_rank_delta_zero_when_position_unchanged(self):
        """A player who stays in the same position gets delta 0."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # Alice wins both matches — stays 1st
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points_rank_delta == 0

    def test_rank_delta_positive_when_moved_up(self):
        """A player who moved up in ranking gets a positive delta."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # meetup1: draw (both get 1 pt — Bob listed 1st by sort stability, Alice 2nd)
        # meetup2: Alice wins big — Alice takes 1st overall, delta = +1
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [bob.id], [alice.id], 1, 1)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points_rank_delta == 1

    def test_rank_delta_negative_when_dropped(self):
        """A player who dropped in ranking gets a negative delta."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 0, 1)
        meetup3 = make_meetup(datetime(2026, 1, 24, 20, 0), [alice.id], [bob.id], 0, 1)
        meetup_repo, player_repo = make_repos([meetup1, meetup2, meetup3], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points_rank_delta is not None
        assert alice_stats.points_rank_delta < 0  # Alice dropped

    def test_rank_delta_none_for_new_player(self):
        """A player absent from the previous ranking gets rank_delta=None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        # meetup1: Alice vs Bob (no Charlie)
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        # meetup2: Alice vs Charlie (Charlie's first appearance)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [charlie.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        charlie_stats = next(p for p in report.all_time.players if p.player_name == "Charlie")
        assert charlie_stats.points_rank_delta is None
