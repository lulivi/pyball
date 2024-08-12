import functools

from collections import defaultdict
from typing import Callable, Dict, List

from pyball.utils.aggregate import Event


class EventBus:
    def __init__(self) -> None:
        self.event_mapper: Dict[str, List[Callable]] = defaultdict(lambda: [])

    def subscribe(self, func: Callable, event: str) -> None:
        self.event_mapper[event].append(func)

    def emit(self, event: Event) -> None:
        for subscriber in self.event_mapper[event.__class__.__name__]:
            try:
                subscriber(event)
            except:
                pass


PyBallEventBus = EventBus()


def on(event_name: str):
    def decorator(function):
        @functools.wraps(function)
        def wrapper(*args, **kwargs):
            PyBallEventBus.subscribe(func=function, event=event_name)

        return wrapper

    return decorator
