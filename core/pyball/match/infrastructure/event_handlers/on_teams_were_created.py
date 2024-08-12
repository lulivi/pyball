from core.pyball.meetup.domain.model.meetup import Meetup
from core.pyball.utils.event_bus import on


@on("TeamsWereCreated")
def on_teams_were_created(event: Meetup.TeamsWereCreated):
    pass
