import json
import uuid

from typing import List, Optional

from core.pyball.match.domain.matches import Matches
from core.pyball.settings import DATA_DIRECTORY_PATH
from pyball.match.domain.model.match import Match
from pyball.utils.event_bus import PyBallEventBus
from pyball.utils.json_encoder import JsonUuidEncoder


class GoalSaver(Matches):
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("goals.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def save(self, goal: dict) -> None:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        # What do we want to save?

        self._json_file.write_text(json.dumps(saved_file_contents, indent=4, cls=JsonUuidEncoder))

    def get(self, id: uuid.UUID) -> Optional[Match]:
        return self._get_by_item(item_name="id", value=str(id))

    # def get_by_meetup_id(self, date_time: datetime.datetime) -> List[Match]:
    #     return self._get_by_item(item_name="date_time", value=date_time)

    def _get_by_item(self, item_name: str, value: str) -> Optional[Match]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for match_line in saved_file_contents:
            # What data do we need to retrieve?
            goals = []
            if value == getattr(goals, item_name):
                return goals

        return None
