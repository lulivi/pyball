"""Meetup repository interface."""

from datetime import date
from typing import Protocol

from pyball.domain.meetup.models import Meetup, MeetupId


class MeetupRepository(Protocol):
    """Repository interface for Meetup aggregate."""

    def save(self, meetup: Meetup) -> None:
        """Save a meetup to the repository."""
        ...

    def find_by_id(self, meetup_id: MeetupId) -> Meetup | None:
        """Find a meetup by its ID."""
        ...

    def find_by_date(self, meetup_date: date) -> Meetup | None:
        """Find a meetup by its date."""
        ...

    def find_all(self) -> list[Meetup]:
        """Return all meetups."""
        ...

    def delete(self, meetup_id: MeetupId) -> None:
        """Delete a meetup by its ID."""
        ...
