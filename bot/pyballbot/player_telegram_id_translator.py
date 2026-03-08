import json
import uuid

from dataclasses import dataclass
from typing import Dict, List, Optional

from pyballbot.settings import DATA_DIRECTORY_PATH


class PlayerIdNotFound(Exception):
    """"""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player's UUID `{id}` was not found"
        super().__init__(self.message)


class PlayerIdAlreadyInUse(Exception):
    """There is a player with the same UUID in the Translator."""

    def __init__(self, id: uuid.UUID) -> None:
        self.id = id
        self.message = f"The player's UUID `{id}` is already in use"
        super().__init__(self.message)


class PlayerTelegramIdNotFound(Exception):
    """"""

    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player's Telegram ID `{telegram_id}` is was not found"
        super().__init__(self.message)


class PlayerTelegramIdAlreadyInUse(Exception):
    """There is a player with the same UUID in the repository."""

    def __init__(self, telegram_id: str) -> None:
        self.telegram_id = telegram_id
        self.message = f"The player's Telegram ID `{telegram_id}` is already in use"
        super().__init__(self.message)


@dataclass
class PlayerIds:
    id: uuid.UUID
    telegram_id: str

    def as_json(self) -> Dict[str, str]:
        return {"id": str(self.id), "telegram_id": self.telegram_id}

    @staticmethod
    def from_json(json_object: Dict[str, str]) -> "PlayerIds":
        return PlayerIds(id=uuid.UUID(json_object["id"]), telegram_id=json_object["telegram_id"])


class PlayerToTelegramIdTranslatorService:
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("player_to_telegram_id_translator.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def translate_player_id(self, id: uuid.UUID) -> str:
        player_ids: Optional[PlayerIds] = self._get_by_item(name="id", value=str(id))

        if player_ids is None:
            raise PlayerIdNotFound(id)

        return player_ids.telegram_id

    def translate_telegram_id(self, telegram_id: str) -> uuid.UUID:
        player_ids: Optional[PlayerIds] = self._get_by_item(name="telegram_id", value=telegram_id)

        if player_ids is None:
            raise PlayerTelegramIdNotFound(telegram_id=telegram_id)

        return player_ids.id

    def _get_by_item(self, name: str, value: str) -> Optional[PlayerIds]:
        saved_file_contents: List[Dict[str, str]] = json.loads(self._json_file.read_text())

        for element in saved_file_contents:
            if value == element[name]:
                return PlayerIds.from_json(element)

        return None

    def save(self, id: uuid.UUID, telegram_id: str) -> None:
        if self._get_by_item(name="id", value=str(id)):
            raise PlayerIdAlreadyInUse(id=id)
        if self._get_by_item(name="telegram_id", value=telegram_id):
            raise PlayerTelegramIdAlreadyInUse(telegram_id=telegram_id)

        saved_file_contents: List[Dict[str, str]] = json.loads(self._json_file.read_text())
        saved_file_contents.append(PlayerIds(id=id, telegram_id=telegram_id).as_json())
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))

    def delete(self, id: uuid.UUID) -> None:
        player_ids = self._get_by_item(name="id", value=str(id))

        if player_ids is None:
            return None

        saved_file_contents: List[Dict[str, str]] = json.loads(self._json_file.read_text())
        saved_file_contents.remove(player_ids.as_json())
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))
