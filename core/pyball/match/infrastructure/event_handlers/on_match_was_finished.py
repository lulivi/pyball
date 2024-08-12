from core.pyball.match.domain.model.match import Match
from core.pyball.match.infrastructure.goal_saver import GoalSaver
from core.pyball.utils.event_bus import on


@on("MatchWasFinished")
def on_teams_were_created(event: Match.MatchWasFinished):
    goal_saver = GoalSaver()
