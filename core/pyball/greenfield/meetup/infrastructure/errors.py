import datetime
import uuid


class MeetupDateAlreadyUsed(Exception):
    """There is a meetup with the same UUID or date in the repository."""

    def __init__(self, date_time: datetime.datetime) -> None:
        self.date_time = date_time
        self.message = f"The date `{date_time}` is already in use"
        super().__init__(self.message)


class MeetupDateNotFound(Exception):
    """The meetup was not found."""

    def __init__(self, date_time: datetime.datetime) -> None:
        self.date_time = date_time
        self.message = f"There is no meetup with the date `{date_time}`"
        super().__init__(self.message)


class PlayerTelegramIdNotFound(Exception):
    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The Player Telegram ID `{telegram_id}` could not be found"
        super().__init__(self.message)


class PlayerNameNotFound(Exception):
    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"The Player `{name}` could not be found"
        super().__init__(self.message)


class PlayerIsAlreadyInMeetup(Exception):
    """The player is already in the meetup."""

    def __init__(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.meetup_id = meetup_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is already in the meetup `{meetup_id}`"
        super().__init__(self.message)
