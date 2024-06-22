import uuid

from abc import ABC, abstractmethod


class IPlayerChecker(ABC):
    @abstractmethod
    def check_player_exists(player_id: uuid.UUID) -> bool:
        pass
