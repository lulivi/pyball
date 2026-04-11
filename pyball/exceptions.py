"""Custom exceptions for the PyBall bot."""


class PyBallError(Exception):
    """Base exception for all PyBall errors."""


class MeetupError(PyBallError):
    """Errors related to meetup operations."""


class PlayerError(PyBallError):
    """Errors related to player management."""


class TelegramBotError(PyBallError):
    """Errors related to Telegram bot interaction."""


class StorageError(PyBallError):
    """Errors related to data storage/persistence."""
