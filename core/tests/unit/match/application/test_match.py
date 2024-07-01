import uuid

from unittest import TestCase

from tests.unit.match.application.fake_match_repository import FakeMatchRepository

from pyball.greenfield.match.application.create_match import CreateMatch
from pyball.greenfield.match.application.finish_match import FinishMatch


class TestMatch(TestCase):
    # TODO: PDS - Make this test green again
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
        self.assertIsNone(obtained_match.score)

    # TODO: PDS - Make this test green again
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
        # statistics
        goals = [
            {"player_id": local_team[0], "scoring_team": "local", "assistant_id": local_team[1]},
            {
                "player_id": visiting_team[0],
                "scoring_team": "visiting",
                "assistant_id": visiting_team[0],
            },
            {"player_id": visiting_team[0], "scoring_team": "local"},
        ]

        # Act
        FinishMatch(fake_match_repository).finish(
            match_id,
            goals,
        )

        # Assert
        obtained_match = fake_match_repository.get(match_id)
        events = list(obtained_match.consume_events())
        self.assertEqual(len(events), 1)
        self.assertEqual(events[0].match_id, match_id)
        self.assertEqual(events[0].goals, goals)
        self.assertEqual(obtained_match.score, {"local": 2, "visiting": 1})
