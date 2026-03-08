from event_bus.event_bus import EventBus
from pyballbot.settings import EVENT_BUS_BOT_CLIENT_URL, EVENT_BUS_SERVER_URL

PyBallBotEventBus = EventBus(EVENT_BUS_BOT_CLIENT_URL, EVENT_BUS_SERVER_URL)
