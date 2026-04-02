"""PyBall - Telegram bot for managing football meetups."""

from importlib.metadata import version, PackageNotFoundError

try:
    __version__ = version("pyball")
except PackageNotFoundError:
    __version__ = "0.0.0"
