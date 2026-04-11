# Match Tracking Design

## Overview

Add live match tracking to PyBall: the admin generates a secure URL from the Telegram bot, opens a web kiosk to record goals and assists during the match, and on finish the results are persisted and the Telegram callup messages are updated with the final score and buttons removed.

---

## 1. Domain Model

Two new value objects added to `pyball/domain/meetup/models.py`:

```python
@dataclass(frozen=True)
class GoalEvent(ValueObject):
    scorer_id: PlayerId
    assistant_id: PlayerId | None
    team: str               # "A" or "B"
    timestamp: datetime

@dataclass(frozen=True)
class MatchResult(ValueObject):
    score_a: int
    score_b: int
    events: tuple[GoalEvent, ...]
```

`Meetup` gains one field and two methods:

```python
result: MatchResult | None = None

def set_result(self, result: MatchResult) -> None:
    """Attach the match result. Requires teams to exist."""
    if self.teams is None:
        raise ValueError("Cannot set result without teams")
    self.result = result

def is_closed(self) -> bool:
    """True if the match result has been recorded."""
    return self.result is not None
```

The existing JSON repository serialization is extended to handle the `result` field using the same strategy already used for `teams`.

---

## 2. Application Layer

### 2.1 `StartMatch` use case

Invoked by the bot when `/start_match <date> <time>` is received.

Steps:
1. Look up the meetup by date in `MeetupRepository`.
2. Verify it has teams (`meetup.teams is not None`).
3. Resolve each `PlayerId` in both teams to player names via `PlayerRepository`.
4. Build the URL using `urllib.parse.urlencode`:
   ```
   https://<host>/?token=<match_token>&date=2026-04-11T20:00&teamA=Name1,Name2&teamB=Name3,Name4
   ```
5. Return the URL string for the bot handler to send.

`match_token` is a static secret from `settings.pyball.match_token` — not per-match.

### 2.2 `FinishMatch` use case

Invoked by the HTTP endpoint `POST /api/match/finish`.

Request body (sent by the frontend):
```json
{
  "meetup_date": "2026-04-11T20:00",
  "events": [
    {"scorer": "Dani", "assistant": "Rafa", "team": "A", "timestamp": "..."},
    {"scorer": "Luis", "assistant": null, "team": "B", "timestamp": "..."}
  ],
  "finalScore": {"A": 3, "B": 2}
}
```

Steps:
1. Validate Bearer token against `settings.pyball.match_token`; return 401 if invalid.
2. Look up the meetup by `meetup_date` in `MeetupRepository`.
3. Verify meetup has teams and is not already closed (`not meetup.is_closed()`).
4. Resolve each scorer and assistant name to a `PlayerId` using the existing fuzzy match in `PlayerRepository`. If a name cannot be resolved, return 422 with details.
5. Build `MatchResult` from the resolved `GoalEvent` list.
6. Call `meetup.set_result(result)` and save via `MeetupRepository`.
7. Return `{"meetup_date": ..., "score_a": ..., "score_b": ...}` — the HTTP handler uses this to trigger the Telegram message edit.

---

## 3. Backend Server (FastAPI + asyncio)

`pyball/__main__.py` is refactored to run both the Telegram bot and the HTTP server under the same asyncio event loop:

```python
async def main():
    await application.initialize()
    await application.start()
    await application.updater.start_polling()

    config = uvicorn.Config(fastapi_app, host="0.0.0.0", port=8000, log_level="info")
    server = uvicorn.Server(config)
    await server.serve()  # blocks until shutdown

    await application.updater.stop()
    await application.stop()
    await application.shutdown()
```

**FastAPI app** lives at `pyball/infrastructure/http/app.py`:
- Mounts `StaticFiles` at `/` serving the `static/` directory.
- Defines `POST /api/match/finish` protected by `HTTPBearer`.
- Receives the DI container at construction time to access repositories and the Telegram bot instance.

**New dependencies:** `fastapi`, `uvicorn[standard]` added via poetry.

**New config field:** `settings.pyball.match_token` — a static secret string used both by the bot (URL generation) and the API (Bearer auth).

---

## 4. Bot Command and Post-Match Message Editing

### 4.1 `/start_match` command

Handler added to `pyball/bot/handlers/meetup.py`:
- Decorated with `@authorized` — admin only.
- Calls `StartMatch` use case.
- Replies with an inline-clickable URL in the admin chat.

### 4.2 Post-match Telegram edit

After `FinishMatch` persists the result, the HTTP endpoint calls a bot helper function that:
1. Retrieves both `MessageTracking` entries (regular + substitute) from `TelegramMessageStore` for the meetup date.
2. Rebuilds the message text by calling `format_main_message` / `format_subs_message` — these already branch on `meetup.result is not None`.
3. Calls `bot.edit_message_text()` with `reply_markup=None` to remove join/leave buttons.
4. If a message no longer exists (deleted manually), silently ignores the `telegram.error.BadRequest`.

### 4.3 `format_main_message` — result branch

When `meetup.result is not None`, the teams section renders as:

```
*Claro (5):*
\- jugador1
\- jugador2

*Oscuro (3):*
\- jugador4
\- jugador5
```

Score values come from `meetup.result.score_a` and `meetup.result.score_b`. Same pattern extended to `format_subs_message`.

---

## 5. Frontend (`static/index.html`)

The file is already functionally complete. Changes required:

1. **Remove `fetchLineups()`** — no API call at startup; teams come from URL params only.
2. **Update `initializeApp()`:**
   - If `localStorage` has a saved state (mid-match reload), restore it.
   - Otherwise, read from URL:
     ```js
     const params = new URLSearchParams(window.location.search);
     teamA = params.get('teamA').split(',');
     teamB = params.get('teamB').split(',');
     meetupDate = params.get('date');
     localStorage.setItem('pyball_teams', JSON.stringify({ teamA, teamB, meetupDate }));
     ```
3. **Add `meetup_date` to `finishMatch()` POST body:**
   ```js
   body: JSON.stringify({
       meetup_date: meetupDate,
       events: [...appState.events].reverse(),
       finalScore: { A: appState.goalsA, B: appState.goalsB }
   })
   ```

No other frontend changes needed.

---

## 6. Error Handling

| Scenario | Response |
|----------|----------|
| Invalid token | HTTP 401 |
| Meetup not found | HTTP 404 |
| Meetup already closed | HTTP 409 |
| Player name cannot be resolved | HTTP 422 with unresolved names |
| Telegram message gone (deleted) | Silently ignored |

---

## 7. Testing

- **Unit:** `MatchResult` and `GoalEvent` construction; `Meetup.set_result()` and `is_closed()`; `format_main_message` with result branch.
- **Integration:** `FinishMatch` use case with real repositories; `StartMatch` URL generation.
- **No new integration tests for HTTP layer** — the endpoint logic is thin; use case tests cover the domain.

---

## 8. Out of Scope

- Per-match tokens (JWT/HMAC) — static secret is sufficient for now.
- Cloudflare tunnel setup — infrastructure concern, handled outside this codebase.
- Goal/assist statistics aggregation — future feature.
- Undo/edit events from the web UI.
