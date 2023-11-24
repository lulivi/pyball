import datetime

from abc import ABC, abstractmethod
from typing import Optional

from pyball.match.domain.model.match import Match


class Matches(ABC):
    @abstractmethod
    def save(self, match: Match) -> None:
        pass

    @abstractmethod
    def get(self, id) -> Optional[Match]:
        pass

    @abstractmethod
    def get_by_date(self, date: datetime.datetime) -> Optional[Match]:
        pass
