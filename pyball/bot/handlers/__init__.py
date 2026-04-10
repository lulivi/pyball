"""Bot handlers."""

from pyball.bot.handlers.general import setup_general_handlers
from pyball.bot.handlers.meetup import setup_meetup_handlers
from pyball.bot.handlers.player import setup_player_handlers

__all__ = ["setup_player_handlers", "setup_meetup_handlers", "setup_general_handlers"]
