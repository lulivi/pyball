import datetime
import uuid

from typing import Dict, List, Optional

from pyball.meetup.domain.meetups import Meetups
from pyball.meetup.domain.model.meetup import Meetup


class FakeMeetupRepository(Meetups):
    def __init__(self) -> None:
        self.meetups: Dict[Meetup] = {}

    def save(self, meetup: Meetup) -> None:
        self.meetups[meetup.id] = meetup

    def all(self) -> List[Meetup]:
        return list(self.meetups.values())

    def get(self, id: uuid.UUID) -> Optional[Meetup]:
        return self.meetups.get(id)

    def get_by_date(self, date_time: datetime.datetime) -> Optional[Meetup]:
        for meetup in self.meetups.values():
            if meetup.date_time == date_time:
                return meetup

        return None
