# Bot Handler Test Coverage Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add 18 tests (5 integration + 13 unit) covering missing paths in `pyball/bot/handlers/meetup.py` and `pyball/bot/handlers/player.py`.

**Architecture:** All tests appended to existing files. Integration tests use the `bot_update`/`bot_context` fixtures (real JSON repos, mock Telegram bot API). Unit tests use `mock_update`/`mock_context` (fully mocked container and stores). No new fixtures or conftest changes.

**Tech Stack:** pytest, pytest-asyncio, unittest.mock (MagicMock, AsyncMock, MonkeyPatch)

---

## File Map

| Action | File |
|---|---|
| Modify | `tests/integration/bot/test_meetup_handlers.py` |
| Modify | `tests/integration/bot/test_player_handlers.py` |
| Modify | `tests/unit/bot/handlers/test_meetup_handlers.py` |
| Modify | `tests/unit/bot/handlers/test_player_handlers.py` |

---

### Task 1: Integration tests — meetup handlers (4 tests)

**Files:**
- Modify: `tests/integration/bot/test_meetup_handlers.py`

- [ ] **Step 1: Update imports**

Replace the existing import block at the top of the file:

```python
"""Integration tests for meetup bot handlers."""

# pylint: disable=redefined-outer-name

from datetime import date, datetime
from unittest.mock import AsyncMock

import pytest
import telegram

from pyball.bot.handlers.meetup import (
    add_player_handler,
    create_teams_handler,
    list_meetups_handler,
    new_meetup_handler,
    next_meetup_handler,
    remove_player_handler,
    search_handler,
    show_meetup_handler,
    start_match_handler,
)
from pyball.domain.meetup.models import Meetup
from pyball.domain.player.models import Player
from pyball.infrastructure.telegram import TelegramMessageStore
```

- [ ] **Step 2: Add `test_next_meetup_creates_meetup`**

Append at the end of the file:

```python
@pytest.mark.asyncio
async def test_next_meetup_creates_meetup(bot_update, bot_context):
    """next_meetup_handler creates a meetup for the next default weekday."""
    await next_meetup_handler(bot_update, bot_context)

    container = bot_context.bot_data["container"]
    meetups = container.meetup_repository.find_all()
    assert len(meetups) == 1
    first_call_text = bot_update.message.reply_text.call_args_list[0][0][0]
    assert "Creating meetup for" in first_call_text
```

- [ ] **Step 3: Add `test_search_handler_sends_and_stores`**

```python
@pytest.mark.asyncio
async def test_search_handler_sends_and_stores(bot_update, bot_context):
    """search_handler sends the substitutes message and persists tracking to the store."""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25"]

    await search_handler(bot_update, bot_context)

    bot_context.bot.send_message.assert_called_once()
    settings = bot_context.bot_data["settings"]
    store = TelegramMessageStore(settings.paths.bot_messages_file)
    tracking = store.get_message("2026-04-25T20:00", "substitute")
    assert tracking is not None
    assert tracking.message_id == 42
```

- [ ] **Step 4: Add `test_add_player_partial_failure`**

```python
@pytest.mark.asyncio
async def test_add_player_partial_failure(bot_update, bot_context):
    """add_player_handler with one valid name and one unknown name replies with Added and Failed."""
    container = bot_context.bot_data["container"]
    player = Player.create("Luis", "regular")
    container.player_repository.save(player)
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00", "Luis,", "Ghost"]

    await add_player_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "Added: Luis" in text
    assert "Failed:" in text
```

- [ ] **Step 5: Add `test_show_meetup_no_players`**

```python
@pytest.mark.asyncio
async def test_show_meetup_no_players(bot_update, bot_context):
    """show_meetup_handler for a meetup with no players replies with 'No players yet.'"""
    container = bot_context.bot_data["container"]
    meetup = Meetup.create(datetime(2026, 4, 25, 20, 0), "Test Field")
    container.meetup_repository.save(meetup)

    bot_context.args = ["2026/04/25", "20:00"]

    await show_meetup_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert "No players yet." in text
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
nox -e test -- tests/integration/bot/test_meetup_handlers.py -v
```

Expected: all tests in the file pass (including the 4 new ones).

- [ ] **Step 7: Commit**

```bash
git add tests/integration/bot/test_meetup_handlers.py
git commit -m "test(integration/bot): add next_meetup, search, add_player partial, show_meetup no players"
```

---

### Task 2: Integration tests — player handlers (1 test)

**Files:**
- Modify: `tests/integration/bot/test_player_handlers.py`

- [ ] **Step 1: Add `test_list_players_empty_repo`**

Append at the end of the file:

```python
@pytest.mark.asyncio
async def test_list_players_empty_repo(bot_update, bot_context):
    """list_players_handler with an empty repo replies with 'No players found.'"""
    await list_players_handler(bot_update, bot_context)

    (text, *_), _ = bot_update.message.reply_text.call_args
    assert text == "No players found."
```

- [ ] **Step 2: Run tests and verify they pass**

```bash
nox -e test -- tests/integration/bot/test_player_handlers.py -v
```

Expected: all tests in the file pass (including the new one).

- [ ] **Step 3: Commit**

```bash
git add tests/integration/bot/test_player_handlers.py
git commit -m "test(integration/bot): add list_players empty repo"
```

---

### Task 3: Unit tests — meetup handlers (4 tests)

**Files:**
- Modify: `tests/unit/bot/handlers/test_meetup_handlers.py`

- [ ] **Step 1: Update imports**

Replace the existing import block:

```python
"""Tests for meetup bot handlers."""

from unittest.mock import MagicMock

import pytest

from pyball.bot.handlers.meetup import (
    create_teams_handler,
    new_meetup_handler,
    show_meetup_handler,
)
```

- [ ] **Step 2: Add `test_show_meetup_handler_no_args`**

Append at the end of the file:

```python
@pytest.mark.asyncio
async def test_show_meetup_handler_no_args(mock_update, mock_context):
    mock_context.args = []
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Usage: /show_meetup `YYYY/MM/DD HH:MM`"
    )
```

- [ ] **Step 3: Add `test_show_meetup_handler_invalid_date`**

```python
@pytest.mark.asyncio
async def test_show_meetup_handler_invalid_date(mock_update, mock_context):
    mock_context.args = ["bad", "date"]
    mock_context.bot_data["container"] = MagicMock()

    await show_meetup_handler(mock_update, mock_context)

    (text, *_), _ = mock_update.message.reply_text.call_args
    assert "Invalid date format" in text
```

- [ ] **Step 4: Add `test_show_meetup_handler_not_found`**

```python
@pytest.mark.asyncio
async def test_show_meetup_handler_not_found(mock_update, mock_context):
    mock_context.args = ["2026/04/25", "20:00"]

    container = MagicMock()
    container.meetup_repository.find_by_date.return_value = None
    mock_context.bot_data["container"] = container

    await show_meetup_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Meetup not found.")
```

- [ ] **Step 5: Add `test_create_teams_handler_no_teams`**

```python
@pytest.mark.asyncio
async def test_create_teams_handler_no_teams(mock_update, mock_context):
    mock_context.args = ["2026/04/25", "20:00"]

    container = MagicMock()
    mock_meetup = MagicMock()
    mock_meetup.teams = []
    container.create_teams.return_value.execute.return_value = mock_meetup
    mock_context.bot_data["container"] = container

    await create_teams_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("No teams created.")
```

- [ ] **Step 6: Run tests and verify they pass**

```bash
nox -e test -- tests/unit/bot/handlers/test_meetup_handlers.py -v
```

Expected: all tests pass (6 total including the 2 pre-existing ones).

- [ ] **Step 7: Commit**

```bash
git add tests/unit/bot/handlers/test_meetup_handlers.py
git commit -m "test(unit/bot): add show_meetup and create_teams unit tests"
```

---

### Task 4: Unit tests — player handlers (9 tests)

**Files:**
- Modify: `tests/unit/bot/handlers/test_player_handlers.py`

- [ ] **Step 1: Update imports**

Replace the `from pyball.domain.player.errors import ...` line with:

```python
from pyball.domain.player.errors import (
    InvalidPlayerIdError,
    NameAlreadyTakenError,
    PlayerAlreadyExistsError,
    PlayerNotFoundError,
)
```

- [ ] **Step 2: Add `test_new_player_handler_invalid_group`**

Append at the end of the file:

```python
@pytest.mark.asyncio
async def test_new_player_handler_invalid_group(mock_update, mock_context):
    mock_context.args = ["Luis", "vip"]
    mock_context.bot_data["container"] = MagicMock()

    await new_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Group must be 'regular' or 'substitute'"
    )
```

- [ ] **Step 3: Add `test_rename_player_handler_invalid_id`**

```python
@pytest.mark.asyncio
async def test_rename_player_handler_invalid_id(mock_update, mock_context):
    mock_context.args = ["bad-id", "New Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = InvalidPlayerIdError("bad id")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Invalid player ID format.")
```

- [ ] **Step 4: Add `test_rename_player_handler_not_found`**

```python
@pytest.mark.asyncio
async def test_rename_player_handler_not_found(mock_update, mock_context):
    mock_context.args = ["pid1", "New Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = PlayerNotFoundError("not found")
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with("Player not found.")
```

- [ ] **Step 5: Add `test_rename_player_handler_name_taken`**

```python
@pytest.mark.asyncio
async def test_rename_player_handler_name_taken(mock_update, mock_context):
    mock_context.args = ["pid1", "Existing Name"]

    container = MagicMock()
    container.rename_player.return_value.execute.side_effect = NameAlreadyTakenError(
        "name taken"
    )
    mock_context.bot_data["container"] = container

    await rename_player_handler(mock_update, mock_context)

    _, kwargs = mock_update.message.reply_text.call_args
    assert kwargs.get("parse_mode") == "HTML"
```

- [ ] **Step 6: Add `test_link_player_handler_non_numeric_id`**

```python
@pytest.mark.asyncio
async def test_link_player_handler_non_numeric_id(mock_update, mock_context):
    mock_context.args = ["Luis", "abc"]
    mock_context.bot_data["container"] = MagicMock()

    with pytest.MonkeyPatch.context() as m:
        m.setattr("pyball.bot.handlers.player.TelegramMappingStore", MagicMock())
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Invalid telegram_id. Must be a number."
    )
```

- [ ] **Step 7: Add `test_link_player_handler_already_linked_same`**

```python
@pytest.mark.asyncio
async def test_link_player_handler_already_linked_same(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis", "12345"]

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.player_id = player_id

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = str(player_id.value)

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "This Telegram ID is already linked to this player."
    )
```

- [ ] **Step 8: Add `test_link_player_handler_already_linked_other`**

```python
@pytest.mark.asyncio
async def test_link_player_handler_already_linked_other(mock_update, mock_context):
    from pyball.domain.player.models import PlayerId

    mock_context.args = ["Luis", "12345"]

    player_id = PlayerId.generate()
    mock_player = MagicMock()
    mock_player.name = "Luis"
    mock_player.player_id = player_id

    container = MagicMock()
    container.player_repository.find_all.return_value = [mock_player]
    mock_context.bot_data["container"] = container

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = str(PlayerId.generate().value)  # different player

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await link_player_handler(mock_update, mock_context)

    (text, *_), _ = mock_update.message.reply_text.call_args
    assert "linked to another player" in text
```

- [ ] **Step 9: Add `test_unlink_player_handler_non_numeric_id`**

```python
@pytest.mark.asyncio
async def test_unlink_player_handler_non_numeric_id(mock_update, mock_context):
    mock_context.args = ["abc"]

    with pytest.MonkeyPatch.context() as m:
        m.setattr("pyball.bot.handlers.player.TelegramMappingStore", MagicMock())
        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "Invalid telegram_id. Must be a number."
    )
```

- [ ] **Step 10: Add `test_unlink_player_handler_not_linked`**

```python
@pytest.mark.asyncio
async def test_unlink_player_handler_not_linked(mock_update, mock_context):
    mock_context.args = ["12345"]

    mock_mapping = MagicMock()
    mock_mapping.get_player_id.return_value = None

    with pytest.MonkeyPatch.context() as m:
        m.setattr(
            "pyball.bot.handlers.player.TelegramMappingStore",
            MagicMock(return_value=mock_mapping),
        )
        await unlink_player_handler(mock_update, mock_context)

    mock_update.message.reply_text.assert_called_with(
        "This Telegram ID is not linked to any player."
    )
```

- [ ] **Step 11: Run tests and verify they pass**

```bash
nox -e test -- tests/unit/bot/handlers/test_player_handlers.py -v
```

Expected: all tests pass (16 total including the 7 pre-existing ones).

- [ ] **Step 12: Commit**

```bash
git add tests/unit/bot/handlers/test_player_handlers.py
git commit -m "test(unit/bot): add player handler error path unit tests"
```

---

## Final Verification

- [ ] **Run the full test suite**

```bash
make test
```

Expected: all tests pass, coverage for `pyball/bot/handlers/meetup.py` and `pyball/bot/handlers/player.py` meaningfully improved.
