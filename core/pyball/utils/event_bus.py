from event_bus.event_bus import EventBus
from pyball.settings import EVENT_BUS_CORE_CLIENT_URL, EVENT_BUS_SERVER_URL


PyBallEventBus = EventBus(EVENT_BUS_CORE_CLIENT_URL, EVENT_BUS_SERVER_URL)
