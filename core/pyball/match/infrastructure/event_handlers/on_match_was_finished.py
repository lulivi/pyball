from core.pyball.match.domain.model.match import Match
from core.pyball.match.infrastructure.goal_saver import GoalSaver
from core.pyball.utils.event_bus import PyBallEventBus


@PyBallEventBus.on("MatchWasFinished")
def on_teams_were_created(event: Match.MatchWasFinished):
    for goal in event.goals:
        GoalSaver().save(goal=goal)
