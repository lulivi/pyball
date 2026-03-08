import datetime
import uuid

from typing import Optional

from pyball.meetup.domain.model.meetup import Meetup
from pyball.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository


class TranslateDate:
    def __init__(self) -> None:
        self._meetups = MeetupJsonRepository()

    def execute(self, date_time: datetime.datetime) -> Optional[uuid.UUID]:
        meetup: Optional[Meetup] = self._meetups.get_by_date(date_time=date_time)
        return meetup and meetup.id
