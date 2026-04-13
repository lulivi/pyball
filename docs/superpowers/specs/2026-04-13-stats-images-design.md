# Post-Match Statistics Images Design

**Date:** 2026-04-13
**Branch:** feature/pyball-v4

## Goal

After every match finishes, automatically post two statistics images to the regulars
Telegram group in a dedicated stats topic. One image covers the current season
(September–September), the other covers all-time history. Both images show the same
three charts: goal & assist ranking, points ranking, and top chemistry duos. Player names
in the rankings include a trend indicator showing whether they moved up, dropped, or are
new compared to the previous match.

---

## Config Changes

### Rename `thread_id` → `meetups_thread_id`

The existing `thread_id` field on `TelegramChatSettings` (used by both regulars and
substitutes) is renamed to `meetups_thread_id` for clarity. All references in
`settings.py`, `example.config.toml`, and `bot/handlers/meetup.py` are updated.

Env var override: `PYBALL_TELEGRAM_REGULARS_MEETUPS_THREAD_ID` /
`PYBALL_TELEGRAM_SUBSTITUTES_MEETUPS_THREAD_ID`.

### New `stats_thread_id` (regulars only)

A new `stats_thread_id: str | int = ""` field is added **only to the regulars chat
settings**. Because regulars and substitutes differ in capability, `TelegramChatSettings`
is split into a base class and a `RegularsChatSettings` subclass:

```
TelegramChatSettings     — chat_id, meetups_thread_id, has_meetups_thread()
  └── RegularsChatSettings — stats_thread_id, has_stats_thread()
```

`TelegramSettings.regulars` becomes a `RegularsChatSettings` instance.

`example.config.toml` additions under `[telegram.regulars]`:

```toml
# Optional: The forum topic thread for meetup callup messages
meetups_thread_id = ""

# Optional: The forum topic thread where post-match statistics are posted
stats_thread_id = ""
```

Env var override: `PYBALL_TELEGRAM_REGULARS_STATS_THREAD_ID`.

---

## Application Layer: `ComputeStats` use case

**File:** `pyball/application/meetup/compute_stats.py`

### Data structures

```python
@dataclass
class PlayerStats:
    player_id: str          # str(UUID)
    player_name: str
    goals: int
    assists: int
    matches_played: int
    wins: int
    draws: int
    losses: int
    rank_delta: int | None  # positive = moved up, negative = dropped, None = new entry

    @property
    def points(self) -> int:
        return self.wins * 3 + self.draws

@dataclass
class ChemistryPair:
    scorer_name: str
    assistant_name: str
    count: int

@dataclass
class StatsScopedReport:
    players: list[PlayerStats]      # all players, sorted by points desc
    chemistry: list[ChemistryPair]  # top 10 pairs, sorted by count desc

@dataclass
class StatsReport:
    season: StatsScopedReport
    all_time: StatsScopedReport
```

### Season definition

Current season = September 1 of the most recent past September to today. Example: on
2026-04-13, the current season spans 2025-09-01 to today. A meetup belongs to the
current season if `meetup.date >= season_start`.

### Use case behaviour

`ComputeStats(meetup_repo, player_repo).execute() -> StatsReport`

1. Load all meetups from `meetup_repo`.
2. Resolve all player names once from `player_repo` into a `{str(uuid): name}` dict.
3. For each meetup **with a result set** (`meetup.result is not None`):
   - For each `GoalEvent` in `meetup.result.goals`:
     - Increment scorer's goals and the (scorer, assistant) pair count if assistant present.
     - Increment assistant's assists if present.
   - Determine each player's outcome: look up their team name ("A" or "B") in
     `meetup.teams`, then compare `result.score_a` vs `result.score_b`. Team A wins if
     `score_a > score_b`; Team B wins if `score_b > score_a`; draw if equal. Increment
     matches_played for every player in `meetup.teams` (regardless of goals).
4. Build `StatsScopedReport` for all-time and for season (filter meetups by date).
5. Sort players by points desc; sort chemistry pairs by count desc, keep top 10.
6. Compute `rank_delta` for each scope independently:
   - Re-run aggregation excluding the most recently finished meetup (by date) to get the
     previous ranking.
   - For each player in the current ranking, `rank_delta = previous_position - current_position`
     (positive means moved up; e.g. was 3rd, now 1st → delta = +2).
   - Players absent from the previous ranking get `rank_delta = None` (new entry).

Players with zero recorded stats are excluded from both scopes.

---

## Infrastructure Layer: `StatsImageRenderer`

**File:** `pyball/infrastructure/images/stats_renderer.py`
**Package:** `pyball/infrastructure/images/__init__.py` (empty)

`StatsImageRenderer.render(report: StatsReport) -> tuple[bytes, bytes]`

Returns `(season_png, all_time_png)` — raw PNG bytes for each scope.

### Image layout

Each image is a single `matplotlib` figure with **3 vertically stacked subplots** (tall
portrait orientation, suitable for mobile Telegram). Top 10 players per chart.

| Subplot | Type | Sort |
|---------|------|------|
| Goals & assists | Horizontal grouped bar chart | Goals desc |
| Points ranking | Table (MP, W, D, L, Pts) | Points desc |
| Chemistry duos | Horizontal bar chart (count) | Count desc |

Player name labels in the goal/assist and points subplots include a trend prefix:
`▲ Messi` (moved up), `▼ Ronaldo` (dropped), `─ Neymar` (no change), `★ Mbappé` (new
entry, `rank_delta is None`). Chemistry duo labels are not prefixed (pairs don't have a
meaningful rank delta).

A consistent color scheme is applied across both images. Subplot titles are in Spanish
(e.g. "Goles y asistencias", "Clasificación", "Parejas más frecuentes"). Figure titles
distinguish scope: "Esta temporada" / "Histórico".

`matplotlib` is added as a project dependency in `pyproject.toml`.

---

## Bot Integration

### Trigger

In `pyball/bot/handlers/meetup.py`, the existing `finish_match` flow already calls
`close_match_messages()`. After that call, stats generation is launched as an
`asyncio.create_task` so the handler returns immediately without blocking:

```python
asyncio.create_task(_post_match_stats(context, meetup_date))
```

`_post_match_stats` is a private async helper in the same module that:
1. Calls `ComputeStats(container.meetup_repository, container.player_repository).execute()`
2. Calls `StatsImageRenderer().render(report)`
3. Sends both PNGs to `settings.telegram.regulars.chat_id` with
   `message_thread_id=settings.telegram.regulars.stats_thread_id` (skipped if not
   configured).

### Error handling

If stats generation fails (e.g. matplotlib error), the exception is caught, logged, and
silently dropped — it must never prevent the match-finish flow from completing.

---

## Testing

| Layer | File | What to test |
|-------|------|--------------|
| Application | `tests/unit/application/test_compute_stats.py` | Season boundary, goal/assist/W-D-L aggregation, chemistry pairs, players with no stats excluded, empty meetup list, rank_delta computation (moved up, dropped, new entry, no change) |
| Infrastructure | `tests/unit/infrastructure/test_stats_renderer.py` | `render()` returns two non-empty `bytes` objects; does not raise with minimal/empty input |
| Settings | `tests/unit/test_settings.py` | `meetups_thread_id` rename, `stats_thread_id` parsing, `RegularsChatSettings.has_stats_thread()` |

Bot handler integration is not unit-tested for the stats task — the asyncio background
task pattern is covered by existing handler tests for the finish flow.

---

## File Map

| Action | File | Purpose |
|--------|------|---------|
| Modify | `pyball/settings.py` | Rename `thread_id` → `meetups_thread_id`; add `RegularsChatSettings` with `stats_thread_id` |
| Modify | `example.config.toml` | Rename field; add `stats_thread_id` |
| Modify | `pyball/bot/handlers/meetup.py` | Update all `thread_id` refs to `meetups_thread_id`; add `_post_match_stats` task |
| Create | `pyball/application/meetup/compute_stats.py` | `StatsReport`, `ComputeStats` use case |
| Modify | `pyball/application/meetup/__init__.py` | Export `ComputeStats` |
| Create | `pyball/infrastructure/images/__init__.py` | Package marker |
| Create | `pyball/infrastructure/images/stats_renderer.py` | `StatsImageRenderer` |
| Modify | `pyproject.toml` | Add `matplotlib` dependency |
| Create | `tests/unit/application/test_compute_stats.py` | Unit tests for `ComputeStats` |
| Create | `tests/unit/infrastructure/test_stats_renderer.py` | Unit tests for `StatsImageRenderer` |
| Modify | `tests/unit/test_settings.py` | Tests for renamed/new settings fields |
