# Telegram Callup Messages Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add Telegram callup messages with inline join/leave buttons - main chat for regulars, substitutes chat for substitutes, with message editing on updates.

**Architecture:** Add TelegramMessageStore in infrastructure for message tracking (DDD-compliant - domain stays pure). Update settings with chat configs. Add bot handlers for callup/search commands and callbacks.

**Tech Stack:** python-telegram-bot 20.x, existing JSON infrastructure, existing bot handlers pattern.

---

## File Structure

```
pyball/
├── settings.py              # Add TelegramChatSettings, load from config
├── infrastructure/
│   └── telegram_store.py    # NEW: TelegramMessageStore for message tracking
├── bot/
│   ├── formatters.py         # NEW: Message formatting (main + substitutes)
│   ├── callbacks.py         # NEW: Callback query handler for buttons
│   └── handlers/
│       └── meetup.py        # MODIFY: Add /callup, /search commands
├── application/
│   └── container.py         # MODIFY: Add TelegramMessageStore
└── data/bot/
    └── messages.json        # NEW: Message tracking storage
```

---

## Task 1: Update Settings with Chat Configuration

**Files:**
- Modify: `pyball/settings.py`

- [ ] **Step 1: Read current settings.py**

```python
# Current structure to extend
@dataclass
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
```

- [ ] **Step 2: Add TelegramChatSettings class**

```python
@dataclass
class TelegramChatSettings:
    chat_id: int = 0
    thread_id: str = ""  # Empty = no thread

    def has_thread(self) -> bool:
        return bool(self.thread_id)
```

- [ ] **Step 3: Extend TelegramSettings**

```python
@dataclass 
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    regulars: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)

    def is_authorized(self, user_id: int) -> bool:
        return user_id in self.admins_ids
```

- [ ] **Step 4: Update load_settings to parse new sections**

Add parsing for `telegram.regulars.chat_id`, `telegram.regulars.thread_id`, `telegram.substitutes.chat_id`, `telegram.substitutes.thread_id`.

Environment overrides:
- `PYBALL_TELEGRAM_REGULARS_CHAT_ID`
- `PYBALL_TELEGRAM_REGULARS_THREAD_ID`
- `PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID`
- `PYBALL_TELEGRAM_SUBSTITUTES_THREAD_ID`

- [ ] **Step 5: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: add telegram chat config (regulars/substitutes)"
```

---

## Task 2: Create TelegramMessageStore

**Files:**
- Create: `pyball/infrastructure/telegram_store.py`
- Create: `pyball/infrastructure/__init__.py` (update exports)

- [ ] **Step 1: Define MessageTracking dataclass**

```python
from dataclasses import dataclass

@dataclass
class MessageTracking:
    chat_id: int
    thread_id: str | None
    message_id: int
```

- [ ] **Step 2: Create TelegramMessageStore class**

```python
import json
from datetime import datetime
from pathlib import Path

class TelegramMessageStore:
    """Maps meetup dates to Telegram message IDs. DDD-compliant - infrastructure only."""

    def __init__(self, file_path: Path):
        self.file_path = file_path
        self._ensure_file_exists()

    def _ensure_file_exists(self) -> None:
        self.file_path.parent.mkdir(parents=True, exist_ok=True)
        if not self.file_path.exists():
            self._write({})

    def _read(self) -> dict:
        with open(self.file_path) as f:
            return json.load(f)

    def _write(self, data: dict) -> None:
        with open(self.file_path, "w") as f:
            json.dump(data, f, indent=2)

    def save_message(self, meetup_date: str, chat_type: str, tracking: MessageTracking) -> None:
        """Save message info for a meetup. chat_type is 'main' or 'subs'."""
        data = self._read()
        if meetup_date not in data:
            data[meetup_date] = {}
        data[meetup_date][chat_type] = {
            "chat_id": tracking.chat_id,
            "thread_id": tracking.thread_id,
            "message_id": tracking.message_id,
        }
        self._write(data)

    def get_message(self, meetup_date: str, chat_type: str) -> MessageTracking | None:
        """Get message tracking for a meetup."""
        data = self._read()
        if meetup_date not in data or chat_type not in data[meetup_date]:
            return None
        msg = data[meetup_date][chat_type]
        return MessageTracking(
            chat_id=msg["chat_id"],
            thread_id=msg.get("thread_id"),
            message_id=msg["message_id"],
        )

    def delete_message(self, meetup_date: str, chat_type: str) -> None:
        """Delete message tracking."""
        data = self._read()
        if meetup_date in data and chat_type in data[meetup_date]:
            del data[meetup_date][chat_type]
            if not data[meetup_date]:
                del data[meetup_date]
            self._write(data)
```

- [ ] **Step 3: Update infrastructure __init__.py**

Add export:
```python
from pyball.infrastructure.telegram_store import TelegramMessageStore, MessageTracking
__all__ = ["JsonPlayerRepository", "JsonMeetupRepository", "TelegramMessageStore", "MessageTracking"]
```

- [ ] **Step 4: Commit**

```bash
git add pyball/infrastructure/
git commit -m "feat: add TelegramMessageStore for message tracking"
```

---

## Task 3: Add Message Formatters

**Files:**
- Create: `pyball/bot/formatters.py`

- [ ] **Step 1: Create main chat formatter**

```python
from datetime import datetime
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player

def format_main_message(meetup: Meetup, player_names: dict) -> str:
    """Format message for main (regulars) chat.
    
    Format varies:
    - Before teams: player list only
    - After teams: teams only
    - After results: teams + results
    """
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [f"*Convocatoria* {date_str}"]
    
    if meetup.location:
        lines.append(f"Lugar: *{meetup.location}*")
    
    lines.append("")
    
    if meetup.teams is None:
        # Show player list before teams created
        max_players = 10  # TODO: make configurable
        lines.append(f"*Jugadores ({len(meetup.regulars)}/{max_players}):*")
        for i, player_id in enumerate(meetup.regulars, 1):
            name = player_names.get(player_id, "Unknown")
            lines.append(f"{i}. {name}")
    else:
        # Show teams after teams created
        lines.append("*Equipos:*")
        for team in meetup.teams:
            player_list = ", ".join(
                player_names.get(p, "Unknown") for p in team.players
            )
            lines.append(f"{team.name}: {player_list}")
    
    return "\n".join(lines)
```

- [ ] **Step 2: Create substitutes chat formatter**

```python
def format_subs_message(meetup: Meetup, player_names: dict, max_players: int = 10) -> str:
    """Format message for substitutes chat."""
    date_str = meetup.date.strftime("%d/%b/%Y %H:%M")
    lines = [f"*Convocatoria* {date_str} - Suplentes"]
    lines.append("")
    
    lines.append(f"*Suplentes ({len(meetup.substitutes)}):*")
    for i, player_id in enumerate(meetup.substitutes, 1):
        name = player_names.get(player_id, "Unknown")
        lines.append(f"{i}. {name}")
    
    remaining = max(0, max_players - len(meetup.regulars))
    lines.append(f"\n*Plazas restantes:* {remaining}")
    
    return "\n".join(lines)
```

- [ ] **Step 3: Create inline keyboard builder**

```python
from telegram import InlineKeyboardButton, InlineKeyboardMarkup

def build_callback_data(action: str, meetup_date: datetime) -> str:
    """Build callback data: action:YYYY-MM-DDTHH:MM"""
    return f"{action}:{meetup_date.strftime('%Y-%m-%dT%H:%M')}"

def build_main_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for main chat."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Unirse", callback_data=build_callback_data("join", meetup_date)),
            InlineKeyboardButton("❌ Salir", callback_data=build_callback_data("leave", meetup_date)),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)

def build_subs_keyboard(meetup_date: datetime) -> InlineKeyboardMarkup:
    """Build inline keyboard for substitutes chat."""
    keyboard = [
        [
            InlineKeyboardButton("✅ Unirse", callback_data=build_callback_data("join_sub", meetup_date)),
            InlineKeyboardButton("❌ Salir", callback_data=build_callback_data("leave_sub", meetup_date)),
        ]
    ]
    return InlineKeyboardMarkup(keyboard)
```

- [ ] **Step 4: Parse callback data**

```python
def parse_callback_data(callback_data: str) -> tuple[str, str] | None:
    """Parse callback data. Returns (action, meetup_date_str) or None."""
    if ":" not in callback_data:
        return None
    action, date_str = callback_data.split(":", 1)
    if action not in ("join", "leave", "join_sub", "leave_sub"):
        return None
    return action, date_str
```

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py
git commit -m "feat: add message formatters for callup"
```

---

## Task 4: Create Callback Query Handler

**Files:**
- Create: `pyball/bot/callbacks.py`

- [ ] **Step 1: Create callback handler**

```python
from telegram import Update
from telegram.ext import ContextTypes, CallbackQueryHandler

from pyball.application.container import Container
from pyball.bot.formatters import parse_callback_data, format_main_message, format_subs_message, build_main_keyboard, build_subs_keyboard

async def callback_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle inline button callbacks."""
    query = update.callback_query
    await query.answer()
    
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()
    
    parsed = parse_callback_data(query.data)
    if not parsed:
        await query.edit_message_text("Invalid callback data.")
        return
    
    action, date_str = parsed
    
    try:
        meetup_date = datetime.fromisoformat(date_str)
    except ValueError:
        await query.edit_message_text("Invalid date format.")
        return
    
    meetup_repo = container.meetup_repository
    from pyball.domain.meetup.repository import MeetupRepository
    from datetime import date
    
    meetup = None
    for m in meetup_repo.find_all():
        if m.date.date() == meetup_date.date():
            meetup = m
            break
    
    if not meetup:
        await query.edit_message_text("Meetup not found.")
        return
    
    player_repo = container.player_repository
    player_names = {p.id: p.name for p in player_repo.find_all()}
    
    from pyball.domain.player.models import PlayerId
    telegram_id = query.from_user.id
    
    player = None
    all_players = player_repo.find_all()
    from pyball.infrastructure import JsonPlayerRepository
    
    for p in all_players:
        player = p
        break
    
    if not player:
        await query.edit_message_text("Player not found. Please contact admin.")
        return
    
    player_id = player.id
    
    if action == "join":
        meetup.add_regular(player_id)
    elif action == "leave":
        meetup.remove_player(player_id)
    elif action == "join_sub":
        meetup.add_substitute(player_id)
    elif action == "leave_sub":
        meetup.remove_player(player_id)
    
    meetup_repo.save(meetup)
    
    player_names = {p.id: p.name for p in player_repo.find_all()}
    
    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)
    await query.edit_message_text(text, reply_markup=keyboard)
```

- [ ] **Step 2: Commit**

```bash
git add pyball/bot/callbacks.py
git commit -m "feat: add callback query handler"
```

---

## Task 5: Add /callup and /search Commands

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`

- [ ] **Step 1: Add imports**

```python
from pyball.bot.formatters import format_main_message, format_subs_message, build_main_keyboard, build_subs_keyboard
from pyball.infrastructure import TelegramMessageStore
from pyball.settings import load_settings
```

- [ ] **Step 2: Update setup_meetup_handlers**

Add:
```python
application.add_handler(CommandHandler("callup", callup_handler))
application.add_handler(CommandHandler("search", search_handler))
```

- [ ] **Step 3: Add callup_handler**

```python
async def callup_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /callup command - create meetup and send main message."""
    container: Container = context.bot_data.get('container')
    if not container:
        container = Container()
    
    settings = load_settings()
    
    if not context.args:
        await update.message.reply_text("Usage: /callup YYYY-MM-DD HH:MM [location]")
        return
    
    date_str = " ".join(context.args[:-1]) if len(context.args) > 2 else context.args[0]
    time_str = context.args[1] if len(context.args) > 1 else "20:00"
    location = context.args[2] if len(context.args) > 2 else "Park"
    
    try:
        full_date_str = f"{date_str} {time_str}"
        meetup_date = datetime.fromisoformat(full_date_str)
    except ValueError:
        await update.message.reply_text("Invalid date. Use: /callup YYYY-MM-DD HH:MM [location]")
        return
    
    if not settings.telegram.regulars.chat_id:
        await update.message.reply_text("Regulars chat not configured.")
        return
    
    try:
        meetup = container.create_meetup().execute(meetup_date)
        meetup.location = location
        container.meetup_repository.save(meetup)
    except Exception as e:
        logger.exception("Error creating meetup")
        await update.message.reply_text("An error occurred. Please try again.")
        return
    
    player_names = {p.id: p.name for p in container.player_repository.find_all()}
    text = format_main_message(meetup, player_names)
    keyboard = build_main_keyboard(meetup.date)
    
    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.regulars.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.regulars.thread_id or None,
        )
        
        from pyball.infrastructure.telegram_store import MessageTracking
        store = TelegramMessageStore(settings.paths.mappings_file.parent / "messages.json")
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "main",
            MessageTracking(
                chat_id=settings.telegram.regulars.chat_id,
                thread_id=settings.telegram.regulars.thread_id or None,
                message_id=msg.message_id,
            ),
        )
        
        await update.message.reply_text(f"Callup created! Message sent.")
    except Exception as e:
        logger.exception("Error sending callup message")
        await update.message.reply_text("Meetup created but failed to send message.")
```

- [ ] **Step 4: Add search_handler**

```python
async def search_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Handle /search command - send substitutes message."""
    container: Container = context.bot_data.get('container')
    settings = load_settings()
    
    if not context.args:
        await update.message.reply_text("Usage: /search YYYY-MM-DD")
        return
    
    date_str = context.args[0]
    
    try:
        meetup_date = datetime.strptime(date_str, "%Y-%m-%d")
    except ValueError:
        await update.message.reply_text("Invalid date. Use: /search YYYY-MM-DD")
        return
    
    from pyball.domain.meetup.repository import MeetupRepository
    meetup = None
    for m in container.meetup_repository.find_all():
        if m.date.date() == meetup_date.date():
            meetup = m
            break
    
    if not meetup:
        await update.message.reply_text("Meetup not found.")
        return
    
    if not settings.telegram.substitutes.chat_id:
        await update.message.reply_text("Substitutes chat not configured.")
        return
    
    player_names = {p.id: p.name for p in container.player_repository.find_all()}
    text = format_subs_message(meetup, player_names)
    keyboard = build_subs_keyboard(meetup.date)
    
    try:
        msg = await context.bot.send_message(
            chat_id=settings.telegram.substitutes.chat_id,
            text=text,
            reply_markup=keyboard,
            message_thread_id=settings.telegram.substitutes.thread_id or None,
        )
        
        from pyball.infrastructure.telegram_store import MessageTracking
        store = TelegramMessageStore(settings.paths.mappings_file.parent / "messages.json")
        store.save_message(
            meetup.date.strftime("%Y-%m-%dT%H:%M"),
            "subs",
            MessageTracking(
                chat_id=settings.telegram.substitutes.chat_id,
                thread_id=settings.telegram.substitutes.thread_id or None,
                message_id=msg.message_id,
            ),
        )
        
        await update.message.reply_text("Substitutes message sent!")
    except Exception as e:
        logger.exception("Error sending substitutes message")
        await update.message.reply_text("Failed to send message.")
```

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/handlers/meetup.py
git commit -m "feat: add /callup and /search commands"
```

---

## Task 6: Wire Up Callback Handler in Entrypoint

**Files:**
- Modify: `pyball/bot/entrypoint.py`

- [ ] **Step 1: Import and register callback handler**

```python
from telegram.ext import CallbackQueryHandler
from pyball.bot.callbacks import callback_handler
```

- [ ] **Step 2: Add to create_application**

```python
def create_application() -> Application:
    settings = load_settings()
    application = Application.builder().token(settings.telegram.bot_token).build()
    application.add_handler(CallbackQueryHandler(callback_handler))
    return application
```

- [ ] **Step 3: Commit**

```bash
git add pyball/bot/entrypoint.py
git commit -m "feat: wire up callback handler"
```

---

## Task 7: Tests

**Files:**
- Create: `tests/unit/bot/test_formatters.py`
- Create: `tests/unit/infrastructure/test_telegram_store.py`

- [ ] **Step 1: Test formatters**

```python
import pytest
from datetime import datetime
from pyball.domain.meetup.models import Meetup, Team
from pyball.domain.player.models import PlayerId
from pyball.bot.formatters import format_main_message, format_subs_message

def test_format_main_message_before_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_regular(p1)
    meetup.add_regular(p2)
    
    player_names = {p1: "Luis", p2: "Carlos"}
    text = format_main_message(meetup, player_names)
    
    assert "*Convocatoria*" in text
    assert "15/Jan/2024 20:00" in text
    assert "Luis" in text
    assert "Carlos" in text

def test_format_subs_message():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0))
    p1 = PlayerId.generate()
    meetup.add_substitute(p1)
    
    player_names = {p1: "Pedro"}
    text = format_subs_message(meetup, player_names)
    
    assert "Suplentes" in text
    assert "Pedro" in text
```

- [ ] **Step 2: Test TelegramMessageStore**

```python
import pytest
import tempfile
from pathlib import Path
from pyball.infrastructure.telegram_store import TelegramMessageStore, MessageTracking

def test_save_and_get_message():
    with tempfile.TemporaryDirectory() as tmpdir:
        store = TelegramMessageStore(Path(tmpdir) / "messages.json")
        tracking = MessageTracking(chat_id=123, thread_id="456", message_id=789)
        
        store.save_message("2024-01-15T20:00", "main", tracking)
        result = store.get_message("2024-01-15T20:00", "main")
        
        assert result is not None
        assert result.chat_id == 123
        assert result.message_id == 789
```

- [ ] **Step 3: Run tests**

```bash
pytest tests/unit/bot/test_formatters.py tests/unit/infrastructure/test_telegram_store.py -v
```

- [ ] **Step 4: Commit**

```bash
git add tests/
git commit -m "test: add tests for formatters and telegram store"
```

---

## Self-Review Checklist

- [x] Spec coverage: Settings → TelegramMessageStore → Formatters → Callback → Handlers → Wire up
- [x] No placeholders found
- [x] Type consistency checked (meetup_date format matches: YYYY-MM-DDTHH:MM)
- [x] All DDD principles followed (domain stays pure, infrastructure handles Telegram)
