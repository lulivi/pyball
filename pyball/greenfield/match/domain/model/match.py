import uuid

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from pyball.greenfield.utils.aggregate import Aggregate, Event


class Match(Aggregate):

    def __init__(
        self,
        id: uuid.UUID,
        meetup_id: uuid.UUID,
        local: List[uuid.UUID],
        visiting: List[uuid.UUID],
    ):
        self.id: uuid.UUID = id
        self.meetup_id: uuid.UUID = meetup_id
        self.local: List[uuid.UUID] = local
        self.visiting: List[uuid.UUID] = visiting
        self.goals: List[dict] = []
        self.score: Optional[Tuple[int, int]] = None

    def register_goal(self, player_id: uuid.UUID, assistant_id: Optional[uuid.UUID], own: bool):
        # TODO: PDS - Implement this method
        return NotImplemented

    @dataclass
    class MatchWasFinished(Event):
        match_id: uuid.UUID
        results: List[Dict[str, Union[uuid.UUID, int]]]
