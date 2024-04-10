import uuid

from unittest import TestCase

from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.application.finish_match import FinishMatch
from tests.unit.match.application.fake_match_repository import FakeMatchRepository


class TestMatch(TestCase):
    def test_match_is_created(self) -> None:
        # Arrange
        match_id = uuid.uuid4()
        meetup_id = uuid.uuid4()
        local_team = [uuid.uuid4() for _ in range(5)]
        visiting_team = [uuid.uuid4() for _ in range(5)]
        fake_match_repository = FakeMatchRepository()

        # Act
        CreateMatch(fake_match_repository).create(
            match_id,
            meetup_id,
            local_team,
            visiting_team,
        )

        # Assert
        obtained_match = fake_match_repository.get(match_id)
        self.assertIsNotNone(obtained_match)
        self.assertEqual(match_id, obtained_match.id)
        self.assertEqual(local_team, obtained_match.local)
        self.assertEqual(visiting_team, obtained_match.visiting)
        self.assertIsNone(obtained_match.result)

    def test_results_are_added_and_event_is_risen(self) -> None:
        # Arrange
        match_id = uuid.uuid4()
        meetup_id = uuid.uuid4()
        local_team = [uuid.uuid4() for _ in range(5)]
        visiting_team = [uuid.uuid4() for _ in range(5)]
        fake_match_repository = FakeMatchRepository()
        CreateMatch(fake_match_repository).create(
            match_id,
            meetup_id,
            local_team,
            visiting_team,
        )
        match_statistics = [
            {"player_id": uuid.uuid4(), "team": "Local", "assistant": uuid.uuid4()},
            {"player_id": uuid.uuid4(), "team": "Visiting"},
        ]

        # Act
        FinishMatch(fake_match_repository).finish(
            match_id,
            match_statistics,
        )

        # Assert
        obtained_match = fake_match_repository.get(match_id)
        events = list(obtained_match.consume_events())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].match_id, match_id)
        self.assertEqual(events[0].match_statistics, match_statistics)
