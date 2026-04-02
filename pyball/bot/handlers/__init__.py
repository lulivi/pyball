"""Bot handlers."""

from pyball.bot.handlers.player import setup_player_handlers
from pyball.bot.handlers.meetup import setup_meetup_handlers

__all__ = ["setup_player_handlers", "setup_meetup_handlers"]
