from abc import ABC, abstractmethod
from typing import Iterator, List


class Event(ABC):
    @property
    @abstractmethod
    def bus_string(self) -> str:
        raise NotImplementedError


class Aggregate:
    @property
    def events(self) -> List[Event]:
        if not hasattr(self, "_events"):
            self._events = []

        return self._events

    def trigger_event(self, event: Event) -> None:
        self.events.append(event)

    def consume_events(self) -> Iterator[Event]:
        while self.events:
            yield self.events.pop(0)
