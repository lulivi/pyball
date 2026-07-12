"""Integration tests for JsonMeetupRepository (persistence)."""

import json
import shutil
import tempfile
from datetime import datetime, time
from pathlib import Path

from pyball.domain.meetup.models import GoalEvent, Match, MatchResult, Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository


class TestJsonMeetupRepository:
    """Integration tests for JsonMeetupRepository."""

    def setup_method(self):
        """Create a temporary directory and repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_save_and_find_by_id(self):
        """Saving a meetup allows it to be retrieved by ID."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)

        assert found is not None
        assert found.date == meetup.date
        assert found.location == "Test Field"

    def test_find_by_datetime(self):
        """A saved meetup can be found by its full datetime."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_datetime(datetime(2024, 1, 15, 20, 0))

        assert found is not None
        assert found.id == meetup.id

    def test_find_by_datetime_not_found_when_time_differs(self):
        """find_by_datetime does not match a meetup at a different time on the same day."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        found = self.repo.find_by_datetime(datetime(2024, 1, 15, 19, 0))

        assert found is None

    def test_find_all(self):
        """find_all returns all saved meetups ordered by date."""
        m1 = Meetup.create(datetime(2024, 1, 10), "Test Field")
        m2 = Meetup.create(datetime(2024, 1, 15), "Test Field")
        self.repo.save(m1)
        self.repo.save(m2)

        all_meetups = self.repo.find_all()

        assert len(all_meetups) == 2
        assert all_meetups[0].date < all_meetups[1].date

    def test_file_is_named_after_meetup_datetime(self):
        """The on-disk file is named after the meetup datetime, not its UUID."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Test Field")
        self.repo.save(meetup)

        expected_path = self.directory / "2024-03-20T20:00.json"
        assert expected_path.exists()

    def test_delete_by_datetime(self):
        """delete_by_datetime removes the file for that meetup."""
        meetup = Meetup.create(datetime(2024, 3, 20, 20, 0), "Test Field")
        self.repo.save(meetup)

        self.repo.delete_by_datetime(datetime(2024, 3, 20, 20, 0))

        assert self.repo.find_by_datetime(datetime(2024, 3, 20, 20, 0)) is None

    def test_save_with_teams(self):
        """Saving a meetup with teams persists the team data."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)
        assert found.teams is not None
        assert len(found.teams) == 2

    def test_save_with_teams_round_trips_goalkeeper(self):
        """Saving and reloading a meetup preserves each team's goalkeeper."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        p1, p2 = PlayerId.generate(), PlayerId.generate()
        meetup.add_player(p1)
        meetup.add_player(p2)
        meetup.set_teams([Team.create("A", [p1], goalkeeper=p1), Team.create("B", [p2])])

        self.repo.save(meetup)

        found = self.repo.find_by_id(meetup.id)
        assert found.teams[0].goalkeeper == p1
        assert found.teams[1].goalkeeper is None

    def test_loads_legacy_team_file_without_goalkeeper_key(self):
        """A meetup file saved before this field existed loads with goalkeeper=None."""
        meetup = Meetup.create(datetime(2024, 1, 16, 20, 0), "Test Field")
        p1 = PlayerId.generate()
        meetup.add_player(p1)
        meetup.set_teams([Team.create("A", [p1]), Team.create("B", [])])
        self.repo.save(meetup)

        file_path = self.repo._get_file_path(meetup)  # pylint: disable=protected-access
        data = json.loads(file_path.read_text(encoding="utf-8"))
        for team in data["teams"]:
            del team["goalkeeper"]
        file_path.write_text(json.dumps(data), encoding="utf-8")

        found = self.repo.find_by_id(meetup.id)
        assert found.teams[0].goalkeeper is None

    def test_delete(self):
        """Deleting a meetup makes it unfindable by ID."""
        meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Test Field")
        self.repo.save(meetup)

        self.repo.delete(meetup.id)

        found = self.repo.find_by_id(meetup.id)
        assert found is None


def test_round_trips_a_triangular_meetup_with_multiple_matches(tmp_path):
    """Saving and reloading a 3-team meetup preserves every match and the closed flag."""
    repo = JsonMeetupRepository(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1, p2, p3 = PlayerId.generate(), PlayerId.generate(), PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.add_player(p3)
    team_a, team_b, team_c = (
        Team.create("A", [p1]),
        Team.create("B", [p2]),
        Team.create("C", [p3]),
    )
    meetup.set_teams([team_a, team_b, team_c])
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(2, 0, ())))
    meetup.add_match(Match(teams_playing=(team_a, team_c)))

    repo.save(meetup)
    loaded = repo.find_by_datetime(datetime(2026, 4, 12, 20, 0))

    assert loaded is not None
    assert len(loaded.teams) == 3
    assert len(loaded.matches) == 2
    assert loaded.matches[0].result.score_a == 2
    assert loaded.matches[1].result is None
    assert not loaded.is_closed()


def test_round_trips_closed_flag(tmp_path):
    """A closed meetup reloads with is_closed() == True."""
    repo = JsonMeetupRepository(tmp_path)
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    team_a, team_b = Team.create("A", []), Team.create("B", [])
    meetup.set_teams([team_a, team_b])
    meetup.add_match(Match(teams_playing=(team_a, team_b), result=MatchResult(1, 0, ())))
    meetup.close()

    repo.save(meetup)
    loaded = repo.find_by_datetime(datetime(2026, 4, 12, 20, 0))

    assert loaded.is_closed()


class TestJsonMeetupRepositoryResult:
    """Integration tests for MatchResult persistence."""

    def setup_method(self):
        """Create a temporary directory and repository for each test."""
        # pylint: disable=attribute-defined-outside-init
        self.temp_dir = tempfile.mkdtemp()
        self.directory = Path(self.temp_dir)
        self.repo = JsonMeetupRepository(self.directory)

    def teardown_method(self):
        """Remove the temporary directory after each test."""
        shutil.rmtree(self.temp_dir)

    def test_save_and_load_meetup_with_result(self):
        """A meetup with a MatchResult round-trips through JSON correctly."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        meetup.set_teams([team_a, team_b])
        scorer = PlayerId.generate()
        assistant = PlayerId.generate()
        event = GoalEvent(
            scorer_id=scorer,
            assistant_id=assistant,
            team="A",
            timestamp=time(20, 15),
        )
        result = MatchResult(score_a=2, score_b=1, events=(event,))
        meetup.add_match(Match(teams_playing=(team_a, team_b), result=result))

        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)

        assert loaded is not None
        assert len(loaded.matches) == 1
        loaded_result = loaded.matches[0].result
        assert loaded_result is not None
        assert loaded_result.score_a == 2
        assert loaded_result.score_b == 1
        assert len(loaded_result.events) == 1
        assert loaded_result.events[0].scorer_id == scorer
        assert loaded_result.events[0].assistant_id == assistant
        assert loaded_result.events[0].team == "A"
        assert loaded_result.events[0].timestamp == time(20, 15)

    def test_save_and_load_meetup_without_result(self):
        """A meetup with no matches loads with an empty matches list."""
        meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)
        assert loaded is not None
        assert not loaded.matches

    def test_own_goal_round_trips(self):
        """An own-goal event (is_own_goal=True) survives a save/load cycle."""
        meetup = Meetup.create(datetime(2026, 6, 1, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        meetup.set_teams([team_a, team_b])
        event = GoalEvent(
            scorer_id=p1,
            assistant_id=None,
            team="B",
            timestamp=time(20, 30),
            is_own_goal=True,
        )
        meetup.add_match(
            Match(
                teams_playing=(team_a, team_b),
                result=MatchResult(score_a=0, score_b=1, events=(event,)),
            )
        )

        self.repo.save(meetup)
        loaded = self.repo.find_by_id(meetup.id)

        assert loaded.matches[0].result.events[0].is_own_goal is True

    def test_missing_is_own_goal_defaults_to_false(self):
        """Old JSON files without is_own_goal field load with is_own_goal=False."""
        meetup = Meetup.create(datetime(2026, 6, 2, 20, 0), "Campo Norte")
        p1 = PlayerId.generate()
        p2 = PlayerId.generate()
        team_a, team_b = Team.create("A", [p1]), Team.create("B", [p2])
        meetup.set_teams([team_a, team_b])
        event = GoalEvent(
            scorer_id=p1,
            assistant_id=None,
            team="A",
            timestamp=time(20, 15),
        )
        meetup.add_match(
            Match(
                teams_playing=(team_a, team_b),
                result=MatchResult(score_a=1, score_b=0, events=(event,)),
            )
        )
        self.repo.save(meetup)

        # Manually strip is_own_goal from the saved file
        file_path = self.directory / f"{meetup.date.isoformat(timespec='minutes')}.json"
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        for ev in data["matches"][0]["result"]["events"]:
            ev.pop("is_own_goal", None)
        with open(file_path, "w", encoding="utf-8") as f:
            json.dump(data, f)

        loaded = self.repo.find_by_id(meetup.id)
        assert loaded.matches[0].result.events[0].is_own_goal is False
