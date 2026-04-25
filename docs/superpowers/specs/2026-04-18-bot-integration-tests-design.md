# Bot Integration Tests Design

**Date:** 2026-04-18
**Scope:** `pyball/bot` — handlers and callbacks

## Goal

Add integration tests for the bot layer that exercise the full stack from handler →
container → use case → real JSON repository, mocking only the Telegram network API.
This complements the existing unit tests (which mock the container entirely) and the
existing persistence integration tests (which bypass the handler layer).

## File Structure

```
tests/integration/bot/
    __init__.py
    conftest.py
    test_player_handlers.py
    test_meetup_handlers.py
    test_callbacks.py
```

## Architecture

### What is real vs mocked

| Component | Real | Mocked |
|---|---|---|
| `JsonPlayerRepository` | ✓ (temp dir) | |
| `JsonMeetupRepository` | ✓ (temp dir) | |
| `TelegramMappingStore` | ✓ (temp file) | |
| `TelegramMessageStore` | ✓ (temp file) | |
| `Container` | ✓ | |
| Domain use cases | ✓ | |
| `context.bot` (Telegram API) | | ✓ (AsyncMock) |
| `@authorized` check | | always authorized |

### conftest.py fixtures

**`temp_dir`** (`tmp_path` scope) — provides a `Path` to an isolated temp directory.
Creates a `meetups/` subdirectory for `JsonMeetupRepository`.

**`real_container`** — patches `pyball.application.container.load_settings` with a
`MagicMock` that returns minimal valid settings (location, base_url, and paths pointing
into `temp_dir`). Constructs a real `Container()` and sets `_player_repository` and
`_meetup_repository` directly to real JSON-backed instances. The `load_settings` patch
is scoped to the test via `monkeypatch`.

**`bot_update`** — `MagicMock(spec=Update)` with `message = AsyncMock(spec=Message)`
and `effective_user.id = 12345`. Mirrors the existing unit conftest.

**`bot_context`** — `MagicMock(spec=ContextTypes.DEFAULT_TYPE)` with:
- `bot_data["container"]` = `real_container`
- `bot_data["settings"]` = settings mock with `telegram.is_authorized() = True`,
  `telegram.admins_ids`, `paths.bot_messages_file`, `paths.bot_mappings_file`,
  `pyball.location`, `pyball.default_week_day`, `pyball.default_hour`
- `context.bot = AsyncMock()` for capturing all Telegram API calls

## Test Coverage

### test_player_handlers.py

Each test calls the handler with real container and asserts on repository state after.

| Test | Handler | Assertion |
|---|---|---|
| `test_new_player_persists` | `new_player_handler` | `repo.find_by_name("Luis")` is not None |
| `test_new_player_duplicate_replies_error` | `new_player_handler` | `reply_text` called with HTML error |
| `test_rename_player_persists` | `rename_player_handler` | repo shows updated name |
| `test_delete_player_removes_from_repo` | `delete_player_handler` | `repo.find_by_id()` returns None |
| `test_list_players_includes_names` | `list_players_handler` | reply contains player names |
| `test_change_group_persists` | `change_group_handler` | repo shows updated group |
| `test_link_player_writes_mapping` | `link_player_handler` | `TelegramMappingStore` has entry |
| `test_unlink_player_removes_mapping` | `unlink_player_handler` | mapping entry removed |

### test_meetup_handlers.py

| Test | Handler | Assertion |
|---|---|---|
| `test_new_meetup_persists` | `new_meetup_handler` | `meetup_repo.find_by_date()` not None |
| `test_new_meetup_duplicate_replies_error` | `new_meetup_handler` | `reply_text` with duplicate message |
| `test_add_player_updates_meetup` | `add_player_handler` | meetup in repo has player |
| `test_remove_player_updates_meetup` | `remove_player_handler` | meetup in repo lacks player |
| `test_create_teams_replies_success` | `create_teams_handler` | `reply_text` called; meetup has teams |
| `test_list_meetups_shows_dates` | `list_meetups_handler` | reply contains meetup date |
| `test_show_meetup_shows_players` | `show_meetup_handler` | reply contains player name |
| `test_start_match_forbidden_admin` | `start_match_handler` | `context.bot.send_message` raises `Forbidden`; handler does not re-raise |

For `test_start_match_forbidden_admin`: configure `context.bot.send_message` as an
`AsyncMock` that raises `telegram.error.Forbidden`. Verify handler catches it and does
not propagate.

### test_callbacks.py

Uses a real `TelegramMappingStore` (backed by `temp_dir / "mappings.json"`) written
before the callback fires, so the player lookup finds a real entry.

| Test | Scenario | Assertion |
|---|---|---|
| `test_join_adds_player_to_meetup` | linked player, meetup exists | player in `meetup.players`; message edited |
| `test_leave_removes_player_from_meetup` | player in meetup | player not in `meetup.players` |
| `test_join_duplicate_answers_already_joined` | player already in meetup | `query.answer` called with "ya estás unido" |
| `test_leave_not_in_meetup_answers` | player not in meetup | `query.answer` called with "No estás en este meetup" |
| `test_unlinked_player_answers_error` | no mapping for telegram_id | `query.answer` called with registration message |
| `test_invalid_callback_data_answers_error` | malformed `query.data` | `query.answer` called with error |

## Constraints

- All async tests decorated with `@pytest.mark.asyncio` (strict mode).
- No Playwright, no real Telegram credentials, no network calls.
- `@authorized` decorator always passes (settings mock returns `True`).
- `TelegramMessageStore` and `TelegramMappingStore` use real JSON files in temp dir;
  no additional mocking needed for the file layer.
