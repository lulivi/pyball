import datetime
import uuid

from abc import ABC, abstractmethod
from typing import Optional

from pyball.greenfield.player.domain.model.player import Player


class Players(ABC):
    @abstractmethod
    def save(self, player: Player) -> None:
        pass

    @abstractmethod
    def get(self, id: uuid.UUID) -> Optional[Player]:
        pass

    @abstractmethod
    def get_by_name(self, name: str) -> Optional[Player]:
        pass
