import datetime
import json
import uuid

from typing import List, Optional

from pyball.meetup.domain.meetups import Meetups
from pyball.meetup.domain.model.meetup import Meetup
from pyball.settings import DATA_DIRECTORY_PATH
from pyball.utils.event_bus import PyBallEventBus
from pyball.utils.json_encoder import JsonUuidEncoder

import logging

logger = logging.getLogger(__name__)


class MeetupJsonRepository(Meetups):
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("meetup.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def save(self, meetup: Meetup) -> None:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for meetup_line in saved_file_contents:
            if str(meetup.id) == meetup_line["id"]:
                saved_file_contents.remove(meetup_line)
                break

        saved_file_contents.append(
            {
                "id": meetup.id,
                "date_time": meetup.date_time.isoformat(),
                "location": meetup.location,
                "possible_team_sizes": list(meetup.possible_team_sizes),
                "players": meetup.players,
                "teams": meetup.teams,
            }
        )
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4, cls=JsonUuidEncoder))

        for event in meetup.consume_events():
            PyBallEventBus.emit(event.__class__.__name__, event)

    def all(self) -> List[Meetup]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        meetups: List[Meetup] = []
        for meetup_line in saved_file_contents:
            meetups.append(
                Meetup(
                    id=uuid.UUID(meetup_line["id"]),
                    date_time=datetime.datetime.fromisoformat(meetup_line["date_time"]),
                    location=meetup_line["location"],
                    possible_team_sizes=tuple(meetup_line["possible_team_sizes"]),
                    players=list(map(uuid.UUID, meetup_line["players"])),
                    teams=[
                        list(map(uuid.UUID, team_players)) for team_players in meetup_line["teams"]
                    ],
                )
            )

        return meetups

    def get(self, id: uuid.UUID) -> Optional[Meetup]:
        return self._get_by_item(name="id", value=str(id))

    def get_by_date(self, date_time: datetime.datetime) -> Optional[Meetup]:
        return self._get_by_item(name="date_time", value=date_time.isoformat())

    def _get_by_item(self, name: str, value: str) -> Optional[Meetup]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for raw_meetup in saved_file_contents:
            if value == raw_meetup[name]:
                return Meetup(
                    id=uuid.UUID(raw_meetup["id"]),
                    date_time=datetime.datetime.fromisoformat(raw_meetup["date_time"]),
                    location=raw_meetup["location"],
                    possible_team_sizes=tuple(raw_meetup["possible_team_sizes"]),
                    players=list(map(uuid.UUID, raw_meetup["players"])),
                    teams=[
                        list(map(uuid.UUID, team_players)) for team_players in raw_meetup["teams"]
                    ],
                )

        return None
