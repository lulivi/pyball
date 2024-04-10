from typing import Dict, List, Tuple, Union
import uuid


class FinishMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def finish(
        self,
        match_id: uuid.UUID,
        match_statistics: List[Dict[str, Union[uuid.UUID, int]]],
    ) -> None:
        pass
