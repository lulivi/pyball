from core.pyball.meetup.domain.model.meetup import Meetup
from core.pyball.utils.event_bus import PyBallEventBus


@PyBallEventBus.on("TeamsWereCreated")
def on_teams_were_created(event: Meetup.TeamsWereCreated):
    pass
