import json
import uuid

from dataclasses import dataclass
from typing import List, Optional

from pyball.player.domain.errors import PlayerIdIsAlreadyInUse, PlayerNameIsAlreadyInUse
from pyball.player.domain.model.player import Player
from pyball.player.domain.players import Players
from pyball.settings import DATA_DIRECTORY_PATH


class PlayerJsonRepository(Players):
    def __init__(self) -> None:
        self._json_file = DATA_DIRECTORY_PATH.joinpath("player.json")
        if not self._json_file.exists():
            self._json_file.write_text("[]")

    def save(self, player: Player) -> None:
        if self._get_by_item(name="id", value=str(player.id)):
            raise PlayerIdIsAlreadyInUse(id=player.id)

        if self._get_by_item(name="name", value=player.name):
            raise PlayerNameIsAlreadyInUse(name=player.name)

        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())
        saved_file_contents.append(
            {"id": str(player.id), "name": player.name, "main": player.main}
        )
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))

    def all(self) -> List[Player]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())
        return [
            Player(id=uuid.UUID(player["id"]), name=player["name"], main=player["main"])
            for player in saved_file_contents
        ]

    def get(self, id: uuid.UUID) -> Optional[Player]:
        return self._get_by_item(name="id", value=str(id))

    def get_by_name(self, name: str) -> Optional[Player]:
        return self._get_by_item(name="name", value=name)

    def _get_by_item(self, name: str, value: str) -> Optional[Player]:
        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())

        for raw_player in saved_file_contents:
            if value == raw_player[name]:
                return Player(
                    id=uuid.UUID(raw_player["id"]),
                    name=raw_player["name"],
                    main=raw_player["main"],
                )

        return None

    def delete(self, player: Player) -> None:
        if self._get_by_item(name="id", value=player.id) is None:
            return None

        saved_file_contents: List[dict] = json.loads(self._json_file.read_text())
        saved_file_contents.remove(
            {"id": str(player.id), "name": player.name, "main": player.main}
        )
        self._json_file.write_text(json.dumps(saved_file_contents, indent=4))
