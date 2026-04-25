# Exception Handling Design

## Overview
Replaced generic `except Exception` blocks with specific exception handling to improve error reporting, logging, and robustness of the Telegram bot.

## Custom Exceptions (`pyball/exceptions.py`)
Introduced a hierarchy of custom exceptions derived from `PyBallError`:
- `PyBallError`: Base class.
- `MeetupError`: For domain-level meetup errors.
- `PlayerError`: For domain-level player errors.
- `TelegramBotError`: For Telegram API interaction errors.
- `StorageError`: For data persistence errors.

## Implementation Details
- Handlers were updated to catch specific exceptions (`ValueError`, `InvalidMeetupDateError`, `telegram.error.TelegramError`) before falling back to a general `Exception` block for truly unexpected errors.
- Added structured logging to differentiate between expected domain errors and unexpected runtime errors.
- Improved user feedback messages for specific failure cases (e.g., Telegram connection issues).
