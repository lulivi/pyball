from pyball.meetup.application.create_teams import CreateTeams
from pyball.meetup.domain.model.meetup import Meetup
from pyball.meetup.infrastructure.get_meetup import GetMeetup
from pyball.meetup.infrastructure.meetup_json_repository import MeetupJsonRepository
from pyball.utils.event_bus import on


@on("PlayerWasAdded")
def on_player_was_added(event: Meetup.PlayerWasAdded):
    meetup: Meetup = GetMeetup().by_id(event.meetup_id)

    if not meetup.player_count_is_valid():
        return

    CreateTeams(meetup_repository=MeetupJsonRepository()).execute(event.meetup_id)
