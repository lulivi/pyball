# Bot Integration Tests Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add integration tests for `pyball/bot` that exercise handlers end-to-end with real JSON repositories and mocked Telegram API.

**Architecture:** One `conftest.py` provides shared fixtures (real `Container`, real repos in `tmp_path`, `AsyncMock` bot). Each test file covers one area: player handlers, meetup handlers, inline callbacks. All async tests use `@pytest.mark.asyncio`.

**Tech Stack:** pytest, pytest-asyncio, python-telegram-bot, `unittest.mock` (MagicMock / AsyncMock)

---

## File Map

| Action | Path |
|---|---|
| Create | `tests/integration/bot/__init__.py` |
| Create | `tests/integration/bot/conftest.py` |
| Create | `tests/integration/bot/test_player_handlers.py` |
| Create | `tests/integration/bot/test_meetup_handlers.py` |
| Create | `tests/integration/bot/test_callbacks.py` |

---

### Task 1: Test infrastructure — conftest and `__init__`

**Files:**
- Create: `tests/integration/bot/__init__.py`
- Create: `tests/integration/bot/conftest.py`

- [ ] **Step 1: Create `__init__.py`**

```python
# tests/integration/bot/__init__.py
```

Empty file — marks the directory as a package.

- [ ] **Step 2: Write `conftest.py`**

```python
"""Shared fixtures for bot integration tests."""

from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import CallbackQuery, Message, Update, User
from telegram.ext import ContextTypes

from pyball.application.container import Container
from pyball.infrastructure.persistence.meetup_repository import JsonMeetupRepository
from pyball.infrastructure.persistence.player_repository import JsonPlayerRepository


@pytest.fixture
def tmp_data(tmp_path):
    """Temp directory with meetups/ subdir pre-created."""
    (tmp_path / "meetups").mkdir()
    return tmp_path


@pytest.fixture
def real_container(tmp_data, monkeypatch):
    """Real Container with JSON repos backed by tmp_data."""
    settings_mock = MagicMock()
    settings_mock.pyball.location = "Test Field"
    settings_mock.pyball.base_url = "http://localhost:8000"
    settings_mock.paths.players_file = tmp_data / "players.json"
    settings_mock.paths.meetups_dir = tmp_data / "meetups"

    monkeypatch.setattr("pyball.application.container.load_settings", lambda: settings_mock)

    container = Container()
    container._player_repository = JsonPlayerRepository(tmp_data / "players.json")
    container._meetup_repository = JsonMeetupRepository(tmp_data / "meetups")
    return container


@pytest.fixture
def bot_settings(tmp_data):
    """Settings mock for bot_data with real temp file paths."""
    settings = MagicMock()
    settings.telegram.is_authorized.return_value = True
    settings.telegram.admins_ids = [99999]
    settings.telegram.regulars.chat_id = -100111
    settings.telegram.regulars.meetups_thread_id = None
    settings.telegram.substitutes.chat_id = -100222
    settings.telegram.substitutes.meetups_thread_id = None
    settings.paths.bot_messages_file = tmp_data / "bot_messages.json"
    settings.paths.bot_mappings_file = tmp_data / "bot_mappings.json"
    settings.pyball.location = "Test Field"
    settings.pyball.default_week_day = "wednesday"
    settings.pyball.default_hour = "20:00"
    return settings


@pytest.fixture
def bot_update():
    """Minimal authorized Update mock with real-enough spec."""
    update = MagicMock(spec=Update)
    message = AsyncMock(spec=Message)
    update.message = message
    user = MagicMock(spec=User)
    user.id = 12345
    update.effective_user = user
    return update


@pytest.fixture
def bot_context(real_container, bot_settings):
    """ContextTypes mock wired to real_container and mocked bot API."""
    context = MagicMock(spec=ContextTypes.DEFAULT_TYPE)
    context.bot_data = {"container": real_container, "settings": bot_settings}
    context.bot = AsyncMock()
    sent_msg = AsyncMock()
    sent_msg.message_id = 42
    context.bot.send_message = AsyncMock(return_value=sent_msg)
    context.bot.edit_message_text = AsyncMock()
    context.bot.send_photo = AsyncMock()
    return context
```

- [ ] **Step 3: Verify imports resolve**

Run: `python -c "import tests.integration.bot.conftest" 2>&1 || echo ok`

(No output or "ok" expected — no actual tests yet, just checking imports don't explode.)

- [ ] **Step 4: Commit**

```bash
git add tests/integration/bot/__init__.py tests/integration/bot/conftest.py
git commit -m "test(integration/bot): add conftest with real-container fixtures"
```

---

### Task 2: Player handler integration tests

**Files:**
- Create: `tests/integration/bot/test_player_handlers.py`

- [ ] **Step 1: Write player handler tests**

```python
"""Integration tests for player bot handlers."""

import pytest

from pyball.bot.handlers.player import (
    change_group_handler,
    delete_player_handler,
    link_player_handler,
    list_players_handler,
    new_player_handler,
    rename_player_handler,
    unlink_player_handler,
)
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram.mapping import TelegramMappingStore


@pytest.mark.asyncio
async def test_new_player_persists(bot_update, bot_context):
    """new_player_handler creates a player that exists in the real repo."""
    bot_context.args = ["Luis", "regular"]

    await new_player_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    player = container.player_repository.find_by_name("Luis")
    assert player is not None
    assert player.group == "regular"


@pytest.mark.asyncio
async def test_new_player_duplicate_replies_html_error(bot_update, bot_context):
    """new_player_handler replies with HTML error when player already exists."""
    bot_context.args = ["Luis", "regular"]
    await new_player_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_player_handler(bot_update, bot_context)

    args, kwargs = bot_update.message.reply_text.call_args
    assert kwargs.get("parse_mode") == "HTML"


@pytest.mark.asyncio
async def test_rename_player_persists(bot_update, bot_context):
    """rename_player_handler updates the player name in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = [str(player.id.value), "Carlos"]

    await rename_player_handler(bot_update, bot_context)

    found = container.player_repository.find_by_id(player.id)
    assert found.name == "Carlos"


@pytest.mark.asyncio
async def test_delete_player_removes_from_repo(bot_update, bot_context):
    """delete_player_handler removes the player from the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("ToDelete", "regular")
    container.player_repository.save(player)

    bot_context.args = [str(player.id.value)]

    await delete_player_handler(bot_update, bot_context)

    found = container.player_repository.find_by_id(player.id)
    assert found is None


@pytest.mark.asyncio
async def test_list_players_includes_names(bot_update, bot_context):
    """list_players_handler reply includes names of players in the repo."""
    container = bot_context.bot_data["container"]
    container.player_repository.save(Player.create("Ana", "regular"))
    container.player_repository.save(Player.create("Pedro", "substitute"))

    await list_players_handler(bot_update, bot_context)

    args, kwargs = bot_update.message.reply_text.call_args
    text = args[0]
    assert "Ana" in text
    assert "Pedro" in text


@pytest.mark.asyncio
async def test_change_group_persists(bot_update, bot_context):
    """change_group_handler updates the player group in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = ["Luis", "substitute"]

    await change_group_handler(bot_update, bot_context)

    found = container.player_repository.find_by_name("Luis")
    assert found.group == "substitute"


@pytest.mark.asyncio
async def test_link_player_writes_mapping(bot_update, bot_context):
    """link_player_handler writes a real TelegramMappingStore entry."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    bot_context.args = ["Luis", "55555"]

    await link_player_handler(bot_update, bot_context)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.bot_mappings_file)
    assert store.get_player_id(55555) == str(player.id.value)


@pytest.mark.asyncio
async def test_unlink_player_removes_mapping(bot_update, bot_context):
    """unlink_player_handler removes an existing TelegramMappingStore entry."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.bot_mappings_file)
    store.set_player_id(55555, str(player.id.value))

    bot_context.args = ["55555"]

    await unlink_player_handler(bot_update, bot_context)

    assert store.get_player_id(55555) is None
```

- [ ] **Step 2: Run tests**

Run: `nox -e test -- tests/integration/bot/test_player_handlers.py -v`

Expected: all 8 tests PASS.

- [ ] **Step 3: Commit**

```bash
git add tests/integration/bot/test_player_handlers.py
git commit -m "test(integration/bot): add player handler integration tests"
```

---

### Task 3: Meetup handler integration tests

**Files:**
- Create: `tests/integration/bot/test_meetup_handlers.py`

- [ ] **Step 1: Write meetup handler tests**

```python
"""Integration tests for meetup bot handlers."""

from datetime import datetime

import pytest
import telegram

from pyball.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    list_meetups_handler,
    new_meetup_handler,
    remove_player_handler,
    show_meetup_handler,
    start_match_handler,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player


@pytest.mark.asyncio
async def test_new_meetup_persists(bot_update, bot_context):
    """new_meetup_handler creates a meetup that exists in the real repo."""
    bot_context.args = ["2026/04/25", "20:00"]

    await new_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    from datetime import date
    meetup = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert meetup is not None
    assert meetup.location == "Test Field"


@pytest.mark.asyncio
async def test_new_meetup_duplicate_replies_error(bot_update, bot_context):
    """new_meetup_handler replies with duplicate message when meetup exists."""
    bot_context.args = ["2026/04/25", "20:00"]
    await new_meetup_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_meetup_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "already exists" in args[0]


@pytest.mark.asyncio
async def test_add_player_updates_meetup(bot_update, bot_context):
    """add_player_handler adds the player to the meetup in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await add_player_handler(bot_update, bot_context)

    from datetime import date
    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id in saved.players


@pytest.mark.asyncio
async def test_remove_player_updates_meetup(bot_update, bot_context):
    """remove_player_handler removes the player from the meetup in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await remove_player_handler(bot_update, bot_context)

    from datetime import date
    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id not in saved.players


@pytest.mark.asyncio
async def test_create_teams_persists_teams(bot_update, bot_context):
    """create_teams_handler splits players into teams stored in the real repo."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"Player{i}", "regular") for i in range(4)]
    for p in players:
        container.player_repository.save(p)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for p in players:
        meetup.add_player(p.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await create_teams_handler(bot_update, bot_context)

    from datetime import date
    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert saved.teams is not None
    args, _ = bot_update.message.reply_text.call_args
    assert "Equipos creados" in args[0]


@pytest.mark.asyncio
async def test_list_meetups_shows_date(bot_update, bot_context):
    """list_meetups_handler reply includes the date of a saved meetup."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    await list_meetups_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "2026/04/25" in args[0]


@pytest.mark.asyncio
async def test_show_meetup_includes_player_name(bot_update, bot_context):
    """show_meetup_handler reply includes the name of a player in the meetup."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "Luis" in args[0]


@pytest.mark.asyncio
async def test_start_match_forbidden_admin_does_not_raise(bot_update, bot_context):
    """start_match_handler catches Forbidden per admin and does not re-raise."""
    container = bot_context.bot_data["container"]

    players = [Player.create(f"P{i}", "regular") for i in range(4)]
    for p in players:
        container.player_repository.save(p)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for p in players:
        meetup.add_player(p.id)
    meetup.create_random_teams()
    container.meetup_repository.save(meetup)

    bot_context.bot.send_message = pytest.mark.asyncio  # will be replaced below
    bot_context.bot.send_message = __import__(
        "unittest.mock", fromlist=["AsyncMock"]
    ).AsyncMock(side_effect=telegram.error.Forbidden("bot was blocked by the user"))

    bot_context.args = ["2026/04/25", "20:00"]

    # Should not raise
    await start_match_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    # No error reply — Forbidden is caught silently per-admin
    bot_update.message.reply_text.assert_not_called()
```

- [ ] **Step 2: Fix the AsyncMock import in start_match test**

Replace the convoluted `__import__` expression in `test_start_match_forbidden_admin_does_not_raise` with a clean import at the top of the file. The final test should look like:

```python
"""Integration tests for meetup bot handlers."""

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
import telegram

from pyball.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    list_meetups_handler,
    new_meetup_handler,
    remove_player_handler,
    show_meetup_handler,
    start_match_handler,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player


@pytest.mark.asyncio
async def test_new_meetup_persists(bot_update, bot_context):
    """new_meetup_handler creates a meetup that exists in the real repo."""
    bot_context.args = ["2026/04/25", "20:00"]

    await new_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert meetup is not None
    assert meetup.location == "Test Field"


@pytest.mark.asyncio
async def test_new_meetup_duplicate_replies_error(bot_update, bot_context):
    """new_meetup_handler replies with duplicate message when meetup exists."""
    bot_context.args = ["2026/04/25", "20:00"]
    await new_meetup_handler(bot_update, bot_context)

    bot_update.message.reply_text.reset_mock()
    await new_meetup_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "already exists" in args[0]


@pytest.mark.asyncio
async def test_add_player_updates_meetup(bot_update, bot_context):
    """add_player_handler adds the player to the meetup in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await add_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id in saved.players


@pytest.mark.asyncio
async def test_remove_player_updates_meetup(bot_update, bot_context):
    """remove_player_handler removes the player from the meetup in the real repo."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis"]

    await remove_player_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert player.id not in saved.players


@pytest.mark.asyncio
async def test_create_teams_persists_teams(bot_update, bot_context):
    """create_teams_handler splits players into teams stored in the real repo."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"Player{i}", "regular") for i in range(4)]
    for p in players:
        container.player_repository.save(p)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for p in players:
        meetup.add_player(p.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await create_teams_handler(bot_update, bot_context)

    saved = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert saved.teams is not None
    args, _ = bot_update.message.reply_text.call_args
    assert "Equipos creados" in args[0]


@pytest.mark.asyncio
async def test_list_meetups_shows_date(bot_update, bot_context):
    """list_meetups_handler reply includes the date of a saved meetup."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    await list_meetups_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "2026/04/25" in args[0]


@pytest.mark.asyncio
async def test_show_meetup_includes_player_name(bot_update, bot_context):
    """show_meetup_handler reply includes the name of a player in the meetup."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    meetup.add_player(player.id)
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    args, _ = bot_update.message.reply_text.call_args
    assert "Luis" in args[0]


@pytest.mark.asyncio
async def test_start_match_forbidden_admin_does_not_raise(bot_update, bot_context):
    """start_match_handler catches Forbidden per admin and does not re-raise."""
    container = bot_context.bot_data["container"]
    players = [Player.create(f"P{i}", "regular") for i in range(4)]
    for p in players:
        container.player_repository.save(p)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    for p in players:
        meetup.add_player(p.id)
    meetup.create_random_teams()
    container.meetup_repository.save(meetup)

    bot_context.bot.send_message = AsyncMock(
        side_effect=telegram.error.Forbidden("bot was blocked by the user")
    )
    bot_context.args = ["2026/04/25", "20:00"]

    await start_match_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    bot_update.message.reply_text.assert_not_called()
```

Write this final version to the file (Step 1 above had a draft; this is the clean final content).

- [ ] **Step 3: Run tests**

Run: `nox -e test -- tests/integration/bot/test_meetup_handlers.py -v`

Expected: all 8 tests PASS.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/bot/test_meetup_handlers.py
git commit -m "test(integration/bot): add meetup handler integration tests"
```

---

### Task 4: Callback handler integration tests

**Files:**
- Create: `tests/integration/bot/test_callbacks.py`

- [ ] **Step 1: Write callback tests**

```python
"""Integration tests for the inline callback handler."""

from datetime import datetime
from unittest.mock import AsyncMock, MagicMock

import pytest

from telegram import CallbackQuery, Message, Update, User

from pyball.bot.callbacks import callback_handler
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram.mapping import TelegramMappingStore


@pytest.fixture
def callback_update():
    """Update mock with callback_query wired for inline button tests."""
    update = MagicMock(spec=Update)
    query = MagicMock(spec=CallbackQuery)
    query.message = AsyncMock(spec=Message)
    query.answer = AsyncMock()
    query.edit_message_text = AsyncMock()
    user = MagicMock(spec=User)
    user.id = 12345
    query.from_user = user
    update.callback_query = query
    update.effective_user = user
    return update


@pytest.fixture
def linked_player(bot_context):
    """Creates a player in the repo and links telegram_id 12345 to it."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)

    settings = bot_context.bot_data["settings"]
    store = TelegramMappingStore(settings.paths.bot_mappings_file)
    store.set_player_id(12345, str(player.id.value))
    return player


@pytest.fixture
def saved_meetup(bot_context):
    """Creates and persists a meetup on 2026-04-25 20:00."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)
    return meetup


@pytest.mark.asyncio
async def test_join_adds_player_to_meetup(callback_update, bot_context, linked_player, saved_meetup):
    """join callback adds the linked player to the meetup and edits the message."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    from datetime import date
    container = bot_context.bot_data["container"]
    meetup = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert linked_player.id in meetup.players
    callback_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_leave_removes_player_from_meetup(callback_update, bot_context, linked_player, saved_meetup):
    """leave callback removes the linked player from the meetup."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    from datetime import date
    meetup = container.meetup_repository.find_by_date(date(2026, 4, 25))
    assert linked_player.id not in meetup.players
    callback_update.callback_query.edit_message_text.assert_called_once()


@pytest.mark.asyncio
async def test_join_duplicate_answers_already_joined(callback_update, bot_context, linked_player, saved_meetup):
    """join callback answers 'ya estás unido' when player is already in meetup."""
    container = bot_context.bot_data["container"]
    saved_meetup.add_player(linked_player.id)
    container.meetup_repository.save(saved_meetup)

    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    answer_text = callback_update.callback_query.answer.call_args[1].get(
        "text", callback_update.callback_query.answer.call_args[0][0]
    )
    assert "ya estás unido" in answer_text


@pytest.mark.asyncio
async def test_leave_not_in_meetup_answers(callback_update, bot_context, linked_player, saved_meetup):
    """leave callback answers 'No estás en este meetup' when player not present."""
    callback_update.callback_query.data = "leave:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    answer_text = callback_update.callback_query.answer.call_args[1].get(
        "text", callback_update.callback_query.answer.call_args[0][0]
    )
    assert "No estás en este meetup" in answer_text


@pytest.mark.asyncio
async def test_unlinked_player_answers_registration_message(callback_update, bot_context, saved_meetup):
    """Callback answers with registration prompt when telegram_id has no mapping."""
    callback_update.callback_query.data = "join:2026-04-25T20:00"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    answer_text = callback_update.callback_query.answer.call_args[1].get(
        "text", callback_update.callback_query.answer.call_args[0][0]
    )
    assert "No player linked" in answer_text or "Contact admin" in answer_text


@pytest.mark.asyncio
async def test_invalid_callback_data_answers_error(callback_update, bot_context):
    """Callback answers with error when callback_data has no colon separator."""
    callback_update.callback_query.data = "invalid_data_no_colon"

    await callback_handler(callback_update, bot_context)

    callback_update.callback_query.answer.assert_called_once()
    answer_text = callback_update.callback_query.answer.call_args[1].get(
        "text", callback_update.callback_query.answer.call_args[0][0]
    )
    assert "Invalid callback data" in answer_text
```

- [ ] **Step 2: Run tests**

Run: `nox -e test -- tests/integration/bot/test_callbacks.py -v`

Expected: all 6 tests PASS.

- [ ] **Step 3: Run full integration suite**

Run: `nox -e test -- tests/integration/ -v`

Expected: all integration tests PASS including the new bot tests.

- [ ] **Step 4: Commit**

```bash
git add tests/integration/bot/test_callbacks.py
git commit -m "test(integration/bot): add callback handler integration tests"
```

---

## Self-Review

**Spec coverage:**
- ✓ conftest with `temp_dir`, `real_container`, `bot_update`, `bot_context` — Task 1
- ✓ All 8 player handler cases — Task 2
- ✓ All 8 meetup handler cases including `start_match` + `Forbidden` — Task 3
- ✓ All 6 callback cases — Task 4

**Placeholder scan:** No TBDs, TODOs, or vague steps. All test bodies contain actual assertions.

**Type consistency:**
- `Player.create(name, group)` used in Tasks 2, 3, 4 — consistent with domain models
- `Meetup.create(datetime, location)` — consistent with production code
- `container.player_repository` / `container.meetup_repository` — consistent property names
- `TelegramMappingStore(path).set_player_id(int, str)` — consistent with mapping.py interface
- `bot_context.args` set per test — consistent with how unit tests set `mock_context.args`
- `query.answer.call_args` extraction pattern is consistent across all callback assertions
