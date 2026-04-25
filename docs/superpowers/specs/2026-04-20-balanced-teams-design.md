# Balanced Teams Design

**Date:** 2026-04-20
**Feature:** Replace random team creation with a history-aware balanced team algorithm

## Overview

Replace the current `create_random_teams()` (pure shuffle) with an optimization-based
algorithm that produces balanced teams using historical match data: goals, assists, win
rate, and winning player pairs. Each invocation of `/create_teams` produces a different
but equally balanced result.

## Player Scoring

Each player in the current meetup receives a normalized score `[0.0, 1.0]`.

### Data source (priority order)

1. **Current season** — if the player has ≥ 3 finished matches since season start (Sep 1)
2. **Full history** — if the player has matches but below the season threshold
3. **Group average** — if the player has no match history at all

### Raw score formula

```
raw_score = goals_per_match * 0.40
          + assists_per_match * 0.30
          + win_rate * 0.30
```

Each component (goals_per_match, assists_per_match, win_rate) is first normalized
independently to `[0, 1]` across all players in the current meetup before combining,
so no single metric dominates by scale.

### Winning pair bonus

For each pair of players assigned to the same team, a bonus proportional to their
shared win count (normalized against the maximum pair win count across all pairs) is
added to the **team score**, not the individual score. This makes the optimization
naturally account for player synergies.

## Team Score

```
team_score = sum(player_scores in team)
           + sum(winning_pair_bonuses for pairs within team)
```

Balance objective: minimize `|team_score_A - team_score_B|`.

## Optimization Algorithm

Each execution of `/create_teams`:

1. **Random initialization** — shuffle the meetup's player list and split in half
2. **Local search loop** — 500 iterations:
   - Pick two random players from different teams
   - Compute whether swapping them reduces `|score_A - score_B|`
   - Accept the swap if it improves or ties the current balance
3. **Return** the resulting teams

Since each run starts from a fresh random shuffle, repeated invocations produce
different valid balanced compositions. No state is persisted between runs.

**Performance:** for typical group sizes (10–16 players), 500 iterations complete
in under 1 ms.

## Code Structure

### New file: `pyball/application/meetup/balance.py`

Pure logic module — no I/O, no repository dependencies.

- `compute_player_scores(players, season_meetups, all_meetups) -> dict[PlayerId, float]`
  Computes normalized scores for each player using the data-source priority logic.
- `optimize_teams(player_ids, player_scores, winning_counts) -> tuple[list[PlayerId], list[PlayerId]]`
  Runs the local search and returns two player lists.

### Modified: `pyball/application/meetup/create_teams.py`

`CreateTeams.execute()` is updated to:
1. Load all finished meetups via `meetup_repository.find_all()`
2. Call `balance.compute_player_scores()` and `balance.optimize_teams()`
3. Call `meetup.set_teams()` with the result

### Modified: `pyball/domain/meetup/models.py`

Add `set_teams(teams: list[Team]) -> None` to `Meetup`.
`create_random_teams()` is kept temporarily but deprecated; removed once no
external callers remain.

### Unchanged

- `pyball/infrastructure/persistence/meetup_repository.py` — `find_all()` already exists
- Bot handlers, container, formatters — the `/create_teams` command surface is unchanged

## Testing

### Unit tests for `balance.py`

- `compute_player_scores()`:
  - Player with ≥ 3 season matches uses season data
  - Player with < 3 season matches falls back to full history
  - Player with no history receives the group average score
  - All returned scores are in `[0.0, 1.0]`
  - Winning pair bonus is applied only within the same team
- `optimize_teams()`:
  - All input players appear exactly once in the output
  - Output is split into exactly two teams
  - Different random seeds produce different team compositions

### Unit tests for `CreateTeams`

- With historical meetups available, `balance.optimize_teams()` is invoked
- Resulting meetup has non-None `teams`

### Property-based tests

- For any player list of size N ≥ 2, `optimize_teams()` returns teams whose
  score difference is ≤ that of a random split (on average over multiple runs)
- Repeated calls with the same input produce at least two distinct assignments
  across N runs (no constant output)

### Integration tests

- `CreateTeams.execute()` end-to-end with in-memory repositories and historical
  finished meetups, verifying the meetup is saved with balanced teams
