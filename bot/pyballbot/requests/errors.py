import datetime
import uuid

from pyballbot.settings import DATETIME_FORMAT


class PlayerQueryError(Exception):
    """"""


class PlayerNameDoesNotExist(PlayerQueryError):
    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"The player name `{name}` does not exist"
        super().__init__(self.message)


class PlayerIdDoesNotExist(PlayerQueryError):
    def __init__(self, id: str) -> None:
        self.id = id
        self.message = f"The player ID `{id}` does not exist"
        super().__init__(self.message)


###


class PlayerCreationError(Exception):
    """"""


class PlayerNameIsAlreadyInUse(PlayerCreationError):

    def __init__(self, name: str) -> None:
        self.name = name
        self.message = f"The player name `{name}` is already in use"
        super().__init__(self.message)


class PlayerTelegramIdIsAlreadyInUse(PlayerCreationError):

    def __init__(self, telegram_id: uuid.UUID) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player Telegram ID `{telegram_id}` is already in use"
        super().__init__(self.message)


###


class PlayerUpdateError(Exception):
    """"""


###


class MeetupQueryError(Exception):
    """"""


class MeetupIdDoesNotExist(MeetupQueryError):

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The meetup ID `{id}` does not exist"
        super().__init__(self.message)


class MeetupDateTimeDoesNotExist(MeetupQueryError):
    def __init__(self, date_time) -> None:
        self.date_time = date_time
        self.message = f"The meetup date and time `{date_time}` does not exist"
        super().__init__(self.message)


###


class MeetupCreationError(Exception):
    """"""


class MeetupDateTimeIsAlreadyInUse(MeetupCreationError):
    def __init__(self, date_time: datetime.datetime) -> None:
        self.date_time = date_time
        self.message = f"The meetup date `{date_time.strftime(DATETIME_FORMAT)}` is already in use"
        super().__init__(self.message)


class AddPlayerToMeetupError(Exception):
    """"""


class PlayerIsAreadyCalled(AddPlayerToMeetupError):

    def __init__(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.meetup_id = meetup_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is already in the meetup `{meetup_id}`"
        super().__init__(self.message)


class RemovePlayerFromMeetupError(Exception):
    """"""


class PlayerIsNotCalled(RemovePlayerFromMeetupError):

    def __init__(self, meetup_id: uuid.UUID, player_id: uuid.UUID) -> None:
        self.meetup_id = meetup_id
        self.player_id = player_id
        self.message = f"The player `{player_id}` is not in the meetup `{meetup_id}`"
        super().__init__(self.message)


class CreateTeamsError(Exception):
    """"""


class CreateMatchesError(Exception):
    """"""


class InvalidPlayerCount(CreateTeamsError):
    """"""


# Core


class CouldNotConnectToTheCore(Exception):
    """"""
