"""Meetup repository interface."""

from datetime import date
from typing import Protocol

from pyball.domain.meetup.models import Meetup, MeetupId


class MeetupRepository(Protocol):
    """Repository interface for Meetup aggregate."""

    def save(self, meetup: Meetup) -> None:
        ...

    def find_by_id(self, meetup_id: MeetupId) -> Meetup | None:
        ...

    def find_by_date(self, meetup_date: date) -> Meetup | None:
        ...

    def find_all(self) -> list[Meetup]:
        ...

    def delete(self, meetup_id: MeetupId) -> None:
        ...
