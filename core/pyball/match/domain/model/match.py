import uuid

from dataclasses import dataclass
from typing import Dict, List, Optional, Tuple, Union

from pyball.match.application.errors import RegisterGoalError
from pyball.match.domain.errors import (
    AssistantIsRivalError,
    OwnGoalWithAssistError,
    PlayerIdNotFoundError,
    PlayerIdNotInGoalError,
    TeamNotInGoalError,
)
from pyball.utils.aggregate import Aggregate, Event


class Match(Aggregate):
    def __init__(
        self,
        id: uuid.UUID,
        meetup_id: uuid.UUID,
        local: List[uuid.UUID],
        visiting: List[uuid.UUID],
    ) -> None:
        self.id: uuid.UUID = id
        self.meetup_id: uuid.UUID = meetup_id
        self.teams: Dict[List[uuid.UUID]] = {
            "local": local,
            "visiting": visiting,
        }
        self.goals: List[Dict[str, Union[uuid.UUID, str]]] = []
        self.score: Optional[Dict[str, int]] = None

    @property
    def local(self) -> List[uuid.UUID]:
        return self.teams["local"]

    @property
    def visiting(self) -> List[uuid.UUID]:
        return self.teams["visiting"]

    def finish_match(self, goals: List[Dict[str, Union[uuid.UUID, bool]]]) -> None:
        self.goals = goals.copy()

        if self.score is None:
            self.score = {"local": 0, "visiting": 0}

        for goal in goals:
            if "player_id" not in goal:
                raise PlayerIdNotInGoalError()

            if "scoring_team" not in goal:
                raise TeamNotInGoalError()

            self._process_goal(
                player_id=goal["player_id"],
                scoring_team=goal["scoring_team"],
                assistant_id=goal.get("assistant_id"),
            )

        self.trigger_event(
            self.MatchWasFinished(
                match_id=self.id,
                local=self.local,
                visiting=self.visiting,
                goals=self.goals,
                score=self.score,
            )
        )

    def _process_goal(
        self, player_id: uuid.UUID, scoring_team: str, assistant_id: Optional[uuid.UUID]
    ) -> None:
        self._check_goal_is_correct(
            player_id=player_id,
            scoring_team=scoring_team,
            assistant_id=assistant_id,
        )
        self.score[scoring_team] += 1

    def _check_goal_is_correct(
        self, player_id: uuid.UUID, scoring_team: str, assistant_id: Optional[uuid.UUID]
    ):
        player_team = self._identify_players_team(player_id)

        if not assistant_id:
            return

        if scoring_team != player_team:
            raise OwnGoalWithAssistError()

        assistant_team = self._identify_players_team(assistant_id)

        if assistant_team != player_team:
            raise AssistantIsRivalError(player_id=player_id, assistant_id=assistant_id)

    def _identify_players_team(self, player_id: uuid.UUID) -> str:
        if player_id in self.local:
            return "local"

        if player_id in self.visiting:
            return "visiting"

        raise PlayerIdNotFoundError(player_id)

    @dataclass
    class MatchWasFinished(Event):
        match_id: uuid.UUID
        local: List[uuid.UUID]
        visiting: List[uuid.UUID]
        goals: List[dict]
        score: Tuple[int, int]
