# Bot Handler Test Coverage — Design Spec

**Date:** 2026-04-18  
**Branch:** feature/pyball-v4  
**Goal:** Fill identified coverage gaps in `pyball/bot/handlers/meetup.py` (51%) and `pyball/bot/handlers/player.py` (59%).

---

## Scope

Add 5 integration tests and 13 unit tests following existing patterns. Two previously agreed tests (`test_new_meetup_handler_no_args`, `test_new_meetup_handler_invalid_date`) are already implemented and excluded.

### Out of scope

- `if message is None: return` guards
- `setup_*_handlers` functions
- Generic `except TelegramError` / `except Exception` branches
- `close_match_messages` (covered via HTTP endpoint)

---

## Approach

All tests written in a single pass (Option A). Integration tests use the `bot_update` / `bot_context` fixtures from `tests/integration/bot/conftest.py`. Unit tests use `mock_update` / `mock_context` from `tests/unit/bot/handlers/conftest.py`. No new fixtures or conftest changes needed.

---

## Integration Tests (`tests/integration/bot/`)

Appended to existing test files.

### `test_meetup_handlers.py`

| Test | Setup | Assert |
|---|---|---|
| `test_next_meetup_creates_meetup` | `bot_settings.pyball.default_week_day = "wednesday"`, `default_hour = "20:00"` | `meetup_repository.find_all()` returns 1 entry; first `reply_text` call contains `"Creating meetup for"` |
| `test_search_handler_sends_and_stores` | Save a meetup to repo | `bot.send_message` called once; `TelegramMessageStore` has a `"substitute"` entry for that date |
| `test_add_player_partial_failure` | Save meetup + player "Luis"; pass names `["Luis", "Ghost"]` | Reply contains `"Added: Luis"` and `"Failed:"` |
| `test_show_meetup_no_players` | Save meetup with no players | Reply contains `"No players yet."` |

### `test_player_handlers.py`

| Test | Setup | Assert |
|---|---|---|
| `test_list_players_empty_repo` | Empty repo (default fixture state) | Reply == `"No players found."` |

---

## Unit Tests (`tests/unit/bot/handlers/`)

Appended to existing test files.

### `test_meetup_handlers.py`

| Test | Setup | Assert |
|---|---|---|
| `test_show_meetup_handler_no_args` | `mock_context.args = []` | Reply == `"Usage: /show_meetup \`YYYY/MM/DD HH:MM\`"` |
| `test_show_meetup_handler_invalid_date` | `mock_context.args = ["bad", "date"]` | Reply contains `"Invalid date format"` |
| `test_show_meetup_handler_not_found` | `args = ["2026/04/25", "20:00"]`; `container.meetup_repository.find_by_date.return_value = None` | Reply == `"Meetup not found."` |
| `test_create_teams_handler_no_teams` | `execute` returns meetup with `meetup.teams = []` | Reply == `"No teams created."` |

### `test_player_handlers.py`

| Test | Setup | Assert |
|---|---|---|
| `test_new_player_handler_invalid_group` | `args = ["Luis", "vip"]` | Reply == `"Group must be 'regular' or 'substitute'"` |
| `test_rename_player_handler_invalid_id` | `execute` raises `InvalidPlayerIdError` | Reply == `"Invalid player ID format."` |
| `test_rename_player_handler_not_found` | `execute` raises `PlayerNotFoundError` | Reply == `"Player not found."` |
| `test_rename_player_handler_name_taken` | `execute` raises `NameAlreadyTakenError` | Reply called with `parse_mode="HTML"` |
| `test_link_player_handler_non_numeric_id` | `args = ["Luis", "abc"]` | Reply == `"Invalid telegram_id. Must be a number."` |
| `test_link_player_handler_already_linked_same` | mapping returns same `player_id_str` | Reply contains `"already linked to this player"` |
| `test_link_player_handler_already_linked_other` | mapping returns different `player_id_str` | Reply contains `"linked to another player"` |
| `test_unlink_player_handler_non_numeric_id` | `args = ["abc"]` | Reply == `"Invalid telegram_id. Must be a number."` |
| `test_unlink_player_handler_not_linked` | `mapping_store.get_player_id.return_value = None` | Reply == `"This Telegram ID is not linked to any player."` |

---

## Notes

- `next_meetup_handler` uses `datetime.now()` internally; the test asserts on the side-effect (meetup persisted) and on the first reply text prefix rather than the exact date string, making it date-independent.
- `search_handler` integration test reads back the `TelegramMessageStore` file directly to verify persistence, mirroring the pattern in `test_unlink_player_removes_mapping`.
- `link_player` unit tests for "already linked" cases patch `TelegramMappingStore` like the existing success test does.
