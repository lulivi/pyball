"""Tests for ComputeStats use case."""

from datetime import date, datetime, time, timedelta
from unittest.mock import MagicMock

from pyball.application.meetup.compute_stats import ComputeStats, StatsReport
from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, PlayerId, Team
from pyball.domain.meetup.season import _season_start
from pyball.domain.player.models import Player
from pyball.infrastructure.persistence import LegacyStats


def make_player(name: str) -> Player:
    """Create a player with a generated ID."""
    return Player.create(name=name, group="regular")


def in_season(offset_days: int = 30) -> datetime:
    """Return a datetime comfortably inside the current season (Sep 1 onwards)."""
    return datetime.combine(_season_start(date.today()) + timedelta(days=offset_days), time(20, 0))


def before_season(offset_days: int = 30) -> datetime:
    """Return a datetime before the current season start."""
    return datetime.combine(_season_start(date.today()) - timedelta(days=offset_days), time(20, 0))


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
    team_a_obj = Team.create("A", team_a)
    team_b_obj = Team.create("B", team_b)
    meetup.teams = [team_a_obj, team_b_obj]
    meetup.add_match(
        Match(
            teams_playing=(team_a_obj, team_b_obj),
            result=MatchResult(score_a=score_a, score_b=score_b, events=tuple(events or [])),
        )
    )
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
            timestamp=time(20, 5),
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
            timestamp=time(20, 5),
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
            timestamp=time(20, 5),
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

    def test_points_tie_broken_by_fewest_matches_played(self):
        """Tied on points, the player with fewer matches ranks first — wins don't matter."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        dave = make_player("Dave")
        # Alice: 3 draws → 3 pts, 3 MP, 0 wins
        # Bob: 1 win + 3 losses → 3 pts, 4 MP, 1 win (old order put Bob first)
        meetups = []
        for d in (3, 4, 5):
            meetups.append(
                make_meetup(datetime(2026, 1, d, 20, 0), [alice.id], [charlie.id], 0, 0)
            )
        meetups.append(make_meetup(datetime(2026, 1, 10, 20, 0), [bob.id], [dave.id], 1, 0))
        for d in (11, 12, 13):
            meetups.append(make_meetup(datetime(2026, 1, d, 20, 0), [bob.id], [dave.id], 0, 1))
        meetup_repo, player_repo = make_repos(meetups, [alice, bob, charlie, dave])
        report = ComputeStats(meetup_repo, player_repo).execute()
        names = [p.player_name for p in report.all_time.players]
        assert names.index("Alice") < names.index("Bob")


class TestComputeStatsSeasonFilter:
    """Season boundary filtering."""

    def test_meetup_in_season_is_included(self):
        """A meetup after the current season start is in the season scope."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(in_season(), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.season.players) > 0

    def test_meetup_before_season_excluded_from_season(self):
        """A meetup before season start is excluded from season scope but not all-time."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(before_season(), [alice.id], [bob.id], 1, 0)
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
            timestamp=time(20, 5),
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
            timestamp=time(20, 5),
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
                    timestamp=time(20, 5),
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
        charlie = make_player("Charlie")
        # meetup1: Alice draws with Charlie (1 pt each)
        # meetup2: Bob beats Charlie — prev: Bob rank 1 (3pts), Alice rank 2 (1pt)
        # meetup3 (latest): Alice beats Bob — Alice rank 1 (4pts), Bob rank 2 (3pts) → delta = +1
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [charlie.id], 1, 1)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [bob.id], [charlie.id], 1, 0)
        meetup3 = make_meetup(datetime(2026, 1, 24, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2, meetup3], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.points_rank_delta == 1

    def test_points_rank_delta_uses_fewest_matches_tiebreak(self):
        """The previous ranking breaks point ties by fewest matches played, not by wins."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        carol = make_player("Carol")
        dave = make_player("Dave")
        # Alice: 3 draws (3 pts, 3 matches, 0 wins); Bob: 1 win + 3 losses (3 pts, 4 matches)
        opponents = [make_player(f"Opp{i}") for i in range(6)]
        results = [
            ([alice.id], [opponents[0].id], 1, 1),
            ([alice.id], [opponents[1].id], 1, 1),
            ([alice.id], [opponents[2].id], 1, 1),
            ([bob.id], [opponents[3].id], 1, 0),
            ([opponents[4].id], [bob.id], 1, 0),
            ([opponents[5].id], [bob.id], 1, 0),
            ([opponents[0].id], [bob.id], 1, 0),
        ]
        meetups = [
            make_meetup(datetime(2026, 1, 1 + i, 20, 0), team_a, team_b, score_a, score_b)
            for i, (team_a, team_b, score_a, score_b) in enumerate(results)
        ]
        # Latest meetup: Carol draws with Dave; neither Alice nor Bob plays
        meetups.append(make_meetup(datetime(2026, 2, 1, 20, 0), [carol.id], [dave.id], 1, 1))
        meetup_repo, player_repo = make_repos(meetups, [alice, bob, carol, dave, *opponents])
        report = ComputeStats(meetup_repo, player_repo).execute()
        by_name = {p.player_name: p for p in report.all_time.players}
        # Alice stays ahead of Bob in both rankings (fewer matches); the old key (wins first)
        # would have put Bob ahead of Alice before the latest meetup
        assert by_name["Alice"].points_rank_delta == 0
        assert by_name["Bob"].points_rank_delta == 0

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

    def test_goals_rank_delta_none_when_player_had_no_previous_goals(self):
        """A player with 0 goals in the previous ranking gets goals_rank_delta=None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 5),
        )
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals_rank_delta is None

    def test_assists_rank_delta_none_when_player_had_no_previous_assists(self):
        """A player with 0 assists previously gets assists_rank_delta=None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=bob.id,
            team="A",
            timestamp=time(20, 5),
        )
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(
            datetime(2026, 1, 17, 20, 0), [alice.id, bob.id], [alice.id], 1, 0, [event]
        )
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        assert bob_stats.assists_rank_delta is None

    def test_goals_rank_delta_independent_from_points_rank(self):
        """goals_rank_delta reflects the goals ranking, not the points ranking."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        # meetup1: Bob wins (3 pts) and scores 2 goals -> Bob 1st in points, 1st in goals
        # Alice loses and scores 1 goal -> Alice 2nd in points, 2nd in goals
        event_b1 = GoalEvent(
            scorer_id=bob.id,
            assistant_id=None,
            team="B",
            timestamp=time(20, 5),
        )
        event_b2 = GoalEvent(
            scorer_id=bob.id,
            assistant_id=None,
            team="B",
            timestamp=time(20, 10),
        )
        event_a1 = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 15),
        )
        meetup1 = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id],
            [bob.id],
            1,
            2,
            [event_a1, event_b1, event_b2],
        )
        # meetup2: Alice wins and scores 3 goals, Bob draws and scores 1 goal
        # Alice: now 4 pts (1st in points), 4 goals (1st in goals) -> both deltas = 0
        # Bob: now 3 pts (2nd in points, same as before), 3 goals (2nd in goals,
        # same as before) -> both deltas = 0
        event_a2 = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 5),
        )
        event_a3 = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 10),
        )
        event_a4 = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 15),
        )
        event_b3 = GoalEvent(
            scorer_id=bob.id,
            assistant_id=None,
            team="B",
            timestamp=time(20, 20),
        )
        meetup2 = make_meetup(
            datetime(2026, 1, 17, 20, 0),
            [alice.id],
            [bob.id],
            3,
            1,
            [event_a2, event_a3, event_a4, event_b3],
        )
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        # Alice was 2nd in goals (prev), now 1st -> delta = 2 - 1 = +1
        # Alice was not in points ranking (prev), now 1st -> delta = None
        # This shows goals_rank_delta and points_rank_delta are independent
        assert alice_stats.goals_rank_delta == 1
        assert alice_stats.points_rank_delta is None

    def test_zero_points_player_has_none_points_rank_delta(self):
        """A player with 0 points is excluded from the points ranking, so delta is None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        # Bob has 0 points in both rankings -> not ranked -> delta None
        assert bob_stats.points_rank_delta is None


class TestComputeStatsWinningPairs:
    """Winning teammate pair counting."""

    def test_winning_pair_counted_from_winning_team(self):
        """Two players on the winning team increment their winning-pair count."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 2, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.winning_pairs) == 1
        wp = report.all_time.winning_pairs[0]
        assert {wp.player_a_name, wp.player_b_name} == {"Alice", "Bob"}
        assert wp.count == 1

    def test_draw_produces_no_winning_pairs(self):
        """A drawn match contributes no winning pairs."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 1)
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert not report.all_time.winning_pairs

    def test_winning_pairs_sorted_by_count_desc(self):
        """Winning pairs are returned sorted by count descending."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        # alice+bob win together twice; alice+charlie win once
        m1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0)
        m2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id, bob.id], [charlie.id], 1, 0)
        m3 = make_meetup(datetime(2026, 1, 24, 20, 0), [alice.id, charlie.id], [bob.id], 1, 0)
        meetup_repo, player_repo = make_repos([m1, m2, m3], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        pairs = report.all_time.winning_pairs
        assert {pairs[0].player_a_name, pairs[0].player_b_name} == {"Alice", "Bob"}
        assert pairs[0].count == 2

    def test_winning_pairs_capped_at_five(self):
        """Only top 5 winning pairs are returned."""
        players = [make_player(f"P{i}") for i in range(12)]
        meetups = []
        day = 1
        # Create 6 distinct winning pairs with different counts
        for i in range(6):
            pa, pb = players[i * 2], players[i * 2 + 1]
            for _ in range(i + 1):
                m = make_meetup(
                    datetime(2026, 3, day, 20, 0), [pa.id, pb.id], [players[0].id], 1, 0
                )
                meetups.append(m)
                day = (day % 28) + 1
        meetup_repo, player_repo = make_repos(meetups, players)
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert len(report.all_time.winning_pairs) == 5


class TestComputeStatsLegacyAssistsInRankDelta:
    """Rank delta correctly accounts for legacy assists in prev_data."""

    def test_legacy_only_player_not_in_prev_meetups_gets_zero_assists_delta(self):
        """Player with legacy assists but absent from prev_meetups gets delta=0, not None."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")

        # meetup1 (prev_meetup): Alice vs Charlie — Bob does not play
        meetup1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [charlie.id], 1, 0)
        # meetup2 (latest): Alice vs Bob — Bob's first tracked meetup
        meetup2 = make_meetup(datetime(2026, 1, 17, 20, 0), [alice.id], [bob.id], 1, 0)

        bob_id = str(bob.id.value)
        legacy = MagicMock(spec=LegacyStats)
        legacy.all_players.return_value = [bob_id]
        legacy.get_assists.side_effect = lambda pid, since: (
            5 if pid == bob_id and since is None else 0
        )

        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo, legacy).execute()

        bob_stats = next(p for p in report.all_time.players if p.player_name == "Bob")
        # Bob was ranked #1 in assists in prev_data (via legacy) and is still #1 now → delta = 0
        assert bob_stats.assists_rank_delta == 0

    def test_season_prev_data_uses_season_window_for_legacy_assists(self):
        """Season prev_data must filter legacy assists by season start, not all-time."""
        alice = make_player("Alice")
        bob = make_player("Bob")

        # Both meetups are inside the current season
        meetup1 = make_meetup(in_season(30), [alice.id], [bob.id], 1, 0)
        meetup2 = make_meetup(in_season(37), [alice.id], [bob.id], 1, 0)

        alice_id = str(alice.id.value)
        legacy = MagicMock(spec=LegacyStats)
        legacy.all_players.return_value = [alice_id]
        # Alice has 0 all-time (pre-season) legacy assists but 5 season legacy assists
        legacy.get_assists.side_effect = lambda pid, since: (
            5 if pid == alice_id and since is not None else 0
        )

        meetup_repo, player_repo = make_repos([meetup1, meetup2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo, legacy).execute()

        alice_stats = next(p for p in report.season.players if p.player_name == "Alice")
        # Alice had 5 season legacy assists before the latest meetup (rank #1)
        # and still has 5 after — rank unchanged → delta must be 0
        assert alice_stats.assists_rank_delta == 0


class TestComputeStatsTiebreaker:
    """Points ranking tiebreaker: points → fewest matches played → name."""

    def test_goals_do_not_break_equal_points(self):
        """Equal points and matches played are ranked by name, not by goals."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        dummy = make_player("Dummy")

        # Alice and Bob are both on team A → both win (3 pts each)
        # Bob scores 2 goals, Alice scores 1; goals are not a tiebreaker, so name decides
        e1 = GoalEvent(scorer_id=bob.id, assistant_id=None, team="A", timestamp=time(20, 1))
        e2 = GoalEvent(scorer_id=bob.id, assistant_id=None, team="A", timestamp=time(20, 2))
        e3 = GoalEvent(scorer_id=alice.id, assistant_id=None, team="A", timestamp=time(20, 3))

        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id, bob.id],
            [dummy.id],
            3,
            0,
            [e1, e2, e3],
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, dummy])
        report = ComputeStats(meetup_repo, player_repo).execute()

        pts_players = [p for p in report.all_time.players if p.points > 0]
        assert pts_players[0].player_name == "Alice"
        assert pts_players[1].player_name == "Bob"

    def test_assists_do_not_break_equal_points(self):
        """Equal points and matches played are ranked by name, not by assists."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")  # scorer so bob/charlie can have assists
        dummy = make_player("Dummy")

        # Alice and Bob both win with 1 goal each; Bob has 1 assist, Alice has 0
        # Assists are not a tiebreaker (points, then matches_played, then name)
        alice_goal = GoalEvent(
            scorer_id=alice.id, assistant_id=None, team="A", timestamp=time(20, 1)
        )
        bob_goal = GoalEvent(scorer_id=bob.id, assistant_id=None, team="A", timestamp=time(20, 2))
        charlie_goal_assisted_by_bob = GoalEvent(
            scorer_id=charlie.id, assistant_id=bob.id, team="A", timestamp=time(20, 3)
        )

        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id, bob.id, charlie.id],
            [dummy.id],
            3,
            0,
            [alice_goal, bob_goal, charlie_goal_assisted_by_bob],
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie, dummy])
        report = ComputeStats(meetup_repo, player_repo).execute()

        pts_players = [p for p in report.all_time.players if p.points > 0]
        names = [p.player_name for p in pts_players]
        # All three (Alice, Bob, Charlie) have 1 win and 1 match played → 3 points
        # Bob's extra assist does not help: name decides, so Alice stays ahead
        assert names.index("Alice") < names.index("Bob")

    def test_alphabetical_breaks_fully_equal_players(self):
        """Players equal on all stats are ranked alphabetically."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        dummy = make_player("Dummy")

        # Alice and Bob both win with 0 goals — no tiebreaker stat differs
        meetup = make_meetup(
            datetime(2026, 1, 10, 20, 0),
            [alice.id, bob.id],
            [dummy.id],
            1,
            0,
        )
        meetup_repo, player_repo = make_repos([meetup], [alice, bob, dummy])
        report = ComputeStats(meetup_repo, player_repo).execute()

        pts_players = [p for p in report.all_time.players if p.points > 0]
        assert pts_players[0].player_name == "Alice"
        assert pts_players[1].player_name == "Bob"


class TestComputeStatsLatestMatchDate:
    """StatsReport.latest_match_date reflects the most recent finished meetup."""

    def test_latest_match_date_is_most_recent_finished(self):
        """latest_match_date equals the datetime of the most recently finished meetup."""
        alice = make_player("Alice")
        bob = make_player("Bob")

        m1 = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0)
        m2 = make_meetup(datetime(2026, 2, 14, 20, 30), [alice.id], [bob.id], 0, 1)

        meetup_repo, player_repo = make_repos([m1, m2], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()

        assert report.latest_match_date == datetime(2026, 2, 14, 20, 30)

    def test_latest_match_date_none_when_no_finished_meetups(self):
        """latest_match_date is None when there are no finished meetups."""
        meetup_repo, player_repo = make_repos([], [])
        report = ComputeStats(meetup_repo, player_repo).execute()
        assert report.latest_match_date is None


class TestComputeStatsOwnGoals:
    """Own-goal stat counting."""

    def test_own_goal_increments_own_goals_not_goals(self):
        """An own-goal event increments own_goals for the scorer, not goals."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="B",
            timestamp=time(20, 5),
            is_own_goal=True,
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 1, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()

        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.goals == 0
        assert alice_stats.own_goals == 1

    def test_own_goal_does_not_generate_chemistry(self):
        """An own-goal event produces no chemistry pair."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="B",
            timestamp=time(20, 5),
            is_own_goal=True,
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 0, 1, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()

        assert not report.all_time.chemistry

    def test_regular_goal_own_goals_counter_stays_zero(self):
        """A regular goal event leaves own_goals at zero for the scorer."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        event = GoalEvent(
            scorer_id=alice.id,
            assistant_id=None,
            team="A",
            timestamp=time(20, 5),
        )
        meetup = make_meetup(datetime(2026, 1, 10, 20, 0), [alice.id], [bob.id], 1, 0, [event])
        meetup_repo, player_repo = make_repos([meetup], [alice, bob])
        report = ComputeStats(meetup_repo, player_repo).execute()

        alice_stats = next(p for p in report.all_time.players if p.player_name == "Alice")
        assert alice_stats.own_goals == 0
        assert alice_stats.goals == 1


class TestComputeStatsTriangular:
    """Triangular tournament: each round is an independent match."""

    def test_triangular_each_round_counts_as_an_independent_match(self):
        """A 3-team meetup with 2 rounds gives each player credit per round played, not meetup."""
        alice = make_player("Alice")
        bob = make_player("Bob")
        charlie = make_player("Charlie")
        team_a = Team.create("A", [alice.id])
        team_b = Team.create("B", [bob.id])
        team_c = Team.create("C", [charlie.id])

        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        meetup.teams = [team_a, team_b, team_c]
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
        meetup.add_match(Match(teams_playing=(team_a, team_c), result=MatchResult(0, 1, ())))

        meetup_repo, player_repo = make_repos([meetup], [alice, bob, charlie])
        report = ComputeStats(meetup_repo, player_repo).execute()
        by_name = {p.player_name: p for p in report.all_time.players}

        assert by_name["Alice"].matches_played == 2  # played both rounds
        assert by_name["Alice"].wins == 1
        assert by_name["Alice"].losses == 1
        assert by_name["Bob"].matches_played == 1  # only round 1
        assert by_name["Charlie"].matches_played == 1  # only round 2
