import uuid

from typing import Dict, List, Union

from pyball.greenfield.match.application.errors import MatchIdNotFound, RegisterGoalError
from pyball.greenfield.match.domain.errors import (
    AssistantIsRivalError,
    OwnGoalWithAssistError,
    PlayerIdNotFoundError,
    PlayerIdNotInGoalError,
)
from pyball.greenfield.match.domain.matches import Matches


class FinishMatch:
    def __init__(self, match_repository: Matches) -> None:
        self._matches = match_repository

    def finish(
        self,
        match_id: uuid.UUID,
        goals: List[Dict[str, Union[uuid.UUID, bool]]],
    ) -> None:
        match = self._matches.get(match_id)

        if match is None:
            raise MatchIdNotFound(match_id)

        try:
            match.finish_match(goals=goals)
        except (
            PlayerIdNotInGoalError,
            PlayerIdNotFoundError,
            AssistantIsRivalError,
            OwnGoalWithAssistError,
        ) as error:
            raise RegisterGoalError(str(error)) from error

        self._matches.save(match)
