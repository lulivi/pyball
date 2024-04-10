

from dataclasses import dataclass
from typing import Dict, List, Union
import uuid
from pyball.greenfield.utils.aggregate import Aggregate, Event


class Match(Aggregate):

    @dataclass
    class MatchWasFinished(Event):
        match_id: uuid.UUID
        results: List[Dict[str, Union[uuid.UUID, int]]]
