import json
import uuid

from typing import Dict, NamedTuple, Optional

from pyballbot.settings import DATA_DIRECTORY_PATH


class MeetupIdNotFound(Exception):
    """"""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The meetup's ID `{id}` was not found"
        super().__init__(self.message)


class MeetupMessagesIds(NamedTuple):
    regulars_id: int
    substitutes_id: Optional[int]


class MeetupToTelegramIdTranslator:
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("meetup_to_telegram_id_translator.json")
        if not self._json_file.exists():
            self._json_file.write_text("{}")

    def get(self, meetup_id: uuid.UUID) -> MeetupMessagesIds:
        saved_file_contents: Dict[str, MeetupMessagesIds] = json.loads(self._json_file.read_text())
        try:
            return MeetupMessagesIds(*saved_file_contents[str(meetup_id)])
        except KeyError as error:
            raise MeetupIdNotFound(id=meetup_id) from error

    def save(self, meetup_id: uuid.UUID, regulars_id: int, substitutes_id: Optional[int] = None) -> None:
        saved_file_contents: Dict[str, MeetupMessagesIds] = json.loads(self._json_file.read_text())
        saved_file_contents[str(meetup_id)] = MeetupMessagesIds(
            regulars_id=regulars_id, substitutes_id=substitutes_id
        )
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))

    def delete(self, meetup_id: uuid.UUID) -> None:
        saved_file_contents: Dict[str, MeetupMessagesIds] = json.loads(self._json_file.read_text())
        if str(meetup_id) not in saved_file_contents:
            raise MeetupIdNotFound(id=meetup_id)
        del saved_file_contents[str(meetup_id)]
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))
