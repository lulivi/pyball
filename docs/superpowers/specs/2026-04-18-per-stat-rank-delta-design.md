# Per-Stat Rank Delta Design

## Summary

Replace the single `rank_delta` field on `PlayerStats` with three independent delta fields
(one per stat: points, goals, assists). Each section of the stats image shows the movement
arrow based on its own ranking, not the overall classification. Players with 0 in a given
stat are excluded from that section. The `★` (new player) indicator is removed — a player
absent from the previous ranking for a stat shows `▲`.

## Data Model (`compute_stats.py`)

`PlayerStats` loses `rank_delta` and gains three fields:

```python
points_rank_delta: int | None
goals_rank_delta: int | None
assists_rank_delta: int | None
```

In `_build_scoped_report`, after building `stats_list`, three independent delta calculations
run:

1. **Points delta** — rank only players with `points > 0`. Previous rank built from
   `prev_data` filtered the same way.
2. **Goals delta** — rank only players with `goals > 0`.
3. **Assists delta** — rank only players with `assists > 0`.

For each delta:
- If the player was absent from the previous ranking (including 0 → >0 transitions),
  their delta stays `None` (renderer shows `▲`).
- If present in both, `delta = prev_position - current_position`.

Zero-stat filtering happens at two independent levels: inside `_build_scoped_report` when
computing rank positions (so deltas are based only on players who actually have that stat),
and again in `_build_html` when building the template lists (so players with 0 never appear
in the rendered image).

## Renderer (`stats_renderer.py`)

`_trend_prefix` changes signature from `PlayerStats → Markup` to `int | None → Markup`:

```python
def _trend_prefix(delta: int | None) -> Markup:
    if delta is None or delta > 0:
        return Markup('<span class="trend-up">▲</span>')
    if delta < 0:
        return Markup('<span class="trend-down">▼</span>')
    return Markup('<span class="trend-same">─</span>')
```

In `_build_html`, each list is filtered before slicing to 10:

```python
players = [p for p in scoped.players if p.points > 0][:10]
players_by_goals = sorted(
    [p for p in scoped.players if p.goals > 0], key=lambda p: p.goals, reverse=True
)[:10]
players_by_assists = sorted(
    [p for p in scoped.players if p.assists > 0], key=lambda p: p.assists, reverse=True
)[:10]
```

## Template (`stats_template.html`)

Each section passes the relevant delta field to the filter:

- Clasificación: `p.points_rank_delta | trend_prefix`
- Goles: `p.goals_rank_delta | trend_prefix`
- Asistencias: `p.assists_rank_delta | trend_prefix`

The `trend-new` CSS class and its `★` symbol are removed from the template and stylesheet.

## Testing

### Unit (`test_compute_stats.py`)

Existing `TestComputeStatsRankDelta` tests are updated to use `points_rank_delta`.

New cases added:
- `goals_rank_delta` is `None` when player had 0 goals in previous ranking (renders as `▲`)
- `assists_rank_delta` is `None` when player had no previous assists
- `goals_rank_delta` reflects movement in goals ranking independently from points ranking
- Players with 0 in a stat have that stat's delta as `None` (they are excluded from ranking)

### Integration (`test_stats_renderer.py`)

Verify the rendered HTML:
- Contains no players with 0 goals in the goals section
- Contains no players with 0 assists in the assists section
- Contains no players with 0 points in the classification section
