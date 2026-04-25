# Telegram User Authorization - Design

## Overview

Restrict bot access to only approved Telegram user IDs to prevent unauthorized users from modifying callups.

## Configuration

Add `ADMINS_IDS` to `.env`:
```
ADMINS_IDS=123456789,987654321,111222333
```

## Implementation

### 1. Settings (`pyball/settings.py`)

```python
@dataclass
class TelegramSettings:
    bot_token: str = field(default_factory=lambda: os.environ.get("bot_token", ""))
    admins_ids: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise SettingsValidationError("bot_token is required but not set in .env file")

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids
```

Parse `ADMINS_IDS` from environment:
```python
admins_str = os.environ.get("admins_ids", "")
admins_ids = tuple(int(x.strip()) for x in admins_str.split(",") if x.strip())
```

### 2. Authorization Decorator (`pyball/bot/auth.py`)

```python
from functools import wraps

def authorized(func):
    """Decorator to restrict handler to authorized users only."""
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        settings = context.bot_data.get('settings')
        user_id = update.effective_user.id
        
        if not settings.telegram.is_authorized(user_id):
            await update.message.reply_text("Unauthorized. You don't have permission to use this bot.")
            return
        
        return await func(update, context)
    return wrapper
```

### 3. Apply to Handlers

Wrap handler functions with `@authorized` decorator:

```python
@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    ...
```

### 4. Load Settings in Bot

In `pyball/bot/main.py`, add settings to `bot_data`:
```python
app.run_async(safe_dispatcher_callback)
app.post_init = lambda app: app.bot_data.update({'settings': settings, 'container': container})
```

## Error Handling

- Unauthorized users receive: "Unauthorized. You don't have permission to use this bot."
- All errors are logged with user ID for audit purposes

## Testing

- Unit tests for `is_authorized()` method
- Integration test for authorization flow
