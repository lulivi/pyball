# Telegram Authorization Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Restrict bot access to only approved Telegram user IDs from `ADMINS_IDS` environment variable.

**Architecture:** Add authorization check via decorator pattern. Settings module parses `ADMINS_IDS` from environment, handlers are wrapped with `@authorized` decorator that checks user ID against allowed list.

**Tech Stack:** python-telegram-bot 20.*, standard library `functools`

---

## Task 1: Update Settings with ADMINS_IDS

**Files:**
- Modify: `pyball/settings.py`

- [ ] **Step 1: Add ADMINS_IDS parsing to TelegramSettings**

Replace `TelegramSettings` class with:

```python
@dataclass
class TelegramSettings:
    bot_token: str = field(default_factory=lambda: os.environ.get("bot_token", ""))
    admins_ids: tuple[int, ...] = field(default_factory=tuple)

    def __post_init__(self) -> None:
        if not self.bot_token:
            raise SettingsValidationError("bot_token is required but not set in .env file")
        admins_str = os.environ.get("admins_ids", "")
        self.admins_ids = tuple(int(x.strip()) for x in admins_str.split(",") if x.strip())

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids
```

- [ ] **Step 2: Run tests to verify settings work**

Run: `poetry run python -c "from pyball.settings import load_settings; s = load_settings(); print(s.telegram.admins_ids)"`
Expected: Empty tuple `()` if not set in .env

- [ ] **Step 3: Add unit test for is_authorized**

Add to `tests/unit/` or create `tests/unit/test_settings.py`:

```python
import pytest
from pyball.settings import Settings, TelegramSettings

class TestTelegramSettings:
    def test_is_authorized_returns_true_for_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(123) is True
        assert settings.is_authorized(456) is True
        assert settings.is_authorized(789) is True

    def test_is_authorized_returns_false_for_non_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(999) is False

    def test_is_authorized_returns_false_for_empty_list(self):
        settings = TelegramSettings(admins_ids=())
        assert settings.is_authorized(123) is False
```

- [ ] **Step 4: Run test to verify it passes**

Run: `poetry run pytest tests/unit/test_settings.py -v`
Expected: 3 passed

- [ ] **Step 5: Commit**

```bash
git add pyball/settings.py tests/unit/test_settings.py
git commit -m "feat: add ADMINS_IDS setting and is_authorized method"
```

---

## Task 2: Create Authorization Decorator

**Files:**
- Create: `pyball/bot/auth.py`
- Modify: `pyball/bot/handlers/player.py`
- Modify: `pyball/bot/handlers/meetup.py`

- [ ] **Step 1: Create auth.py with authorized decorator**

Create `pyball/bot/auth.py`:

```python
"""Authorization utilities for bot handlers."""

import logging
from functools import wraps
from typing import Callable

from telegram import Update
from telegram.ext import ContextTypes

logger = logging.getLogger(__name__)


def authorized(func: Callable) -> Callable:
    """Decorator to restrict handler to authorized users only.
    
    Checks if the user's Telegram ID is in ADMINS_IDS.
    """
    @wraps(func)
    async def wrapper(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
        if not update.effective_user:
            logger.warning("No effective user in update")
            return
        
        settings = context.bot_data.get('settings')
        if not settings:
            logger.error("Settings not found in bot_data")
            return
        
        user_id = update.effective_user.id
        
        if not settings.telegram.is_authorized(user_id):
            logger.warning(f"Unauthorized access attempt from user ID: {user_id}")
            await update.message.reply_text(
                "Unauthorized. You don't have permission to use this bot."
            )
            return
        
        return await func(update, context)
    return wrapper
```

- [ ] **Step 2: Add authorized decorator to player handlers**

Modify `pyball/bot/handlers/player.py`:

Add import:
```python
from pyball.bot.auth import authorized
```

Wrap each handler function with `@authorized`:

```python
@authorized
async def new_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def rename_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def delete_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def list_players_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
```

- [ ] **Step 3: Add authorized decorator to meetup handlers**

Modify `pyball/bot/handlers/meetup.py`:

Add import:
```python
from pyball.bot.auth import authorized
```

Wrap each handler function with `@authorized`:

```python
@authorized
async def new_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def add_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def remove_player_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def create_teams_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def list_meetups_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:

@authorized
async def show_meetup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
```

- [ ] **Step 4: Write unit test for authorized decorator**

Create `tests/unit/test_auth.py`:

```python
import pytest
from unittest.mock import MagicMock, AsyncMock, patch
from telegram import Update, User, Message

from pyball.bot.auth import authorized


@pytest.fixture
def mock_update():
    user = MagicMock(spec=User)
    user.id = 123
    message = MagicMock(spec=Message)
    message.reply_text = AsyncMock()
    update = MagicMock(spec=Update)
    update.effective_user = user
    update.message = message
    return update


@pytest.fixture
def mock_context():
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    return context


@pytest.mark.asyncio
async def test_authorized_allows_admin_user(mock_update, mock_context):
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    mock_context.bot_data = {'settings': settings}
    
    @authorized
    async def handler(update, context):
        return "success"
    
    result = await handler(mock_update, mock_context)
    assert result == "success"


@pytest.mark.asyncio
async def test_authorized_blocks_non_admin_user(mock_update, mock_context):
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = False
    mock_context.bot_data = {'settings': settings}
    
    @authorized
    async def handler(update, context):
        return "success"
    
    result = await handler(mock_update, mock_context)
    assert result is None
    mock_update.message.reply_text.assert_called_once_with(
        "Unauthorized. You don't have permission to use this bot."
    )
```

- [ ] **Step 5: Run tests to verify**

Run: `poetry run pytest tests/unit/test_auth.py -v`
Expected: 2 passed

- [ ] **Step 6: Commit**

```bash
git add pyball/bot/auth.py pyball/bot/handlers/player.py pyball/bot/handlers/meetup.py tests/unit/test_auth.py
git commit -m "feat: add authorization decorator for bot handlers"
```

---

## Task 3: Update Bot to Load Settings into bot_data

**Files:**
- Modify: `pyball/bot/main.py` (or wherever Application is created)

- [ ] **Step 1: Find and update main bot file**

Find the file where `Application` is created and configured. Check `pyball/bot/` directory:

```bash
ls -la pyball/bot/
```

- [ ] **Step 2: Add settings to bot_data on initialization**

In the Application setup, add settings to bot_data. Example pattern:

```python
from pyball.settings import load_settings

settings = load_settings()

app = Application.builder().token(settings.telegram.bot_token).build()

app.bot_data['settings'] = settings
app.bot_data['container'] = container
```

- [ ] **Step 3: Run full test suite**

Run: `poetry run pytest tests/ -v`
Expected: All tests pass

- [ ] **Step 4: Commit**

```bash
git add pyball/bot/main.py  # or whatever the file is named
git commit -m "feat: inject settings into bot_data for authorization"
```

---

## Task 4: Add ADMINS_IDS to .env.example

**Files:**
- Modify: `.env` or `.env.example`

- [ ] **Step 1: Add ADMINS_IDS to .env.example**

Add to `.env` (create if doesn't exist):

```
# Telegram Bot Configuration
BOT_TOKEN=your_bot_token_here

# Comma-separated list of authorized Telegram user IDs
ADMINS_IDS=
```

- [ ] **Step 2: Commit**

```bash
git add .env
git commit -m "docs: add ADMINS_IDS to .env example"
```

---

## Verification

1. Run all tests: `poetry run pytest tests/ -v`
2. Manually test by adding your Telegram ID to `.env` and using the bot
3. Verify unauthorized users get rejection message
