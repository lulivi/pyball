import json
import uuid

from typing import List, Optional

from core.pyball.match.domain.matches import Matches
from core.pyball.settings import DATA_DIRECTORY_PATH
from pyball.match.domain.model.match import Match
from pyball.utils.event_bus import PyBallEventBus
from pyball.utils.json_encoder import JsonUuidEncoder


class MatchJsonRepository(Matches):
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("matches.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def save(self, match: Match) -> None:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for match_line in saved_file_contents:
            if str(match.id) == match_line["id"]:
                saved_file_contents.remove(match_line)
                break

        saved_file_contents.append(
            {
                "id": match.id,
                "meetup_id": match.meetup_id,
                "teams": match.teams,
                "goals": match.goals,
                "score": match.score,
            }
        )
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4, cls=JsonUuidEncoder))

        for event in match.consume_events():
            PyBallEventBus.emit(event.__class__.__name__, event)

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self._get_by_item(item_name="id", value=str(id))

    # def get_by_meetup_id(self, date_time: datetime.datetime) -> List[Match]:
    #     return self._get_by_item(item_name="date_time", value=date_time)

    def _get_by_item(self, item_name: str, value: str) -> Optional[Match]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for match_line in saved_file_contents:
            match = Match(
                id=uuid.UUID(match_line["id"]),
                meetup_id=uuid.UUID(match_line["meetup_id"]),
                teams={
                    team_name: [uuid.UUID(player) for player in players]
                    for team_name, players in match_line["teams"].items()
                },
                goals=[
                    {
                        key: value if key == "scoring_team" else uuid.UUID(value)
                        for key, value in goal.items()
                    }
                    for goal in match_line["goals"]
                ],
                score=match_line["score"],
            )
            if value == getattr(match, item_name):
                return match

        return None
