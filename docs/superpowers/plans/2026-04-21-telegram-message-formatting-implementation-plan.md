# Telegram Message Formatting Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Improve format_main_message and format_subs_message with emojis, timestamps in events, and improved formatting for teams and results.

**Architecture:** Modify formatters.py to add emoji prefixes and format events with timestamps. Update existing tests to match new format.

**Tech Stack:** Python, pytest, Telegram Bot API

---

## File Structure

- Modify: `pyball/bot/formatters.py:60-133` (format_main_message and format_subs_message)
- Modify: `tests/unit/bot/test_formatters.py` (update existing test assertions)

---

### Task 1: Update format_main_message header emojis and location

**Files:**
- Modify: `pyball/bot/formatters.py:60-101`
- Test: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing tests for new header format**

```python
def test_format_main_message_header_emoji_no_result():
    """When there's no result, header should show 📅 Convocatoria."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    player_names = {str(p1.value): "Luis"}
    text = format_main_message(meetup, player_names)

    assert "📅 *Convocatoria:*" in text


def test_format_main_message_header_emoji_with_result():
    """When there's a result, header should show 🎉 Partido terminado."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.set_teams([Team.create("A", [p1])])
    meetup.set_result(MatchResult(score_a=1, score_b=0, events=()))
    player_names = {str(p1.value): "Luis"}
    text = format_main_message(meetup, player_names)

    assert "🎉 *Partido terminado:*" in text


def test_format_main_message_location_emoji():
    """Location should have 📍 prefix."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    player_names = {str(p1.value): "Luis"}
    text = format_main_message(meetup, player_names)

    assert "📍 *Lugar:* Parque Central" in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "header_emoji or location_emoji"`
Expected: FAIL (assertion errors showing missing emojis)

- [ ] **Step 3: Update format_main_message header logic**

In `pyball/bot/formatters.py`, modify lines 72-78:

```python
date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
if meetup.result is not None:
    header = rf"🎉 *Partido terminado:* `{date_str}`"
else:
    header = rf"📅 *Convocatoria:* `{date_str}`"
lines = [header]

if meetup.location:
    lines.append(f"📍 *Lugar:* {_escape_mdv2(meetup.location)}")
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "header_emoji or location_emoji"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: add header emojis and location emoji to format_main_message"
```

---

### Task 2: Add team emojis (⚪/⚫) to format_main_message

**Files:**
- Modify: `pyball/bot/formatters.py:88-99`
- Test: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing test for team emojis**

```python
def test_format_main_message_team_emojis():
    """Teams should show ⚪ and ⚫ emojis."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names, team_display_names=("Claro", "Oscuro"))

    assert "⚪" in text
    assert "⚫" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "team_emojis"`
Expected: FAIL (assertion error showing no emojis)

- [ ] **Step 3: Add team emojis in format_main_message**

In `pyball/bot/formatters.py`, after line 88 where teams are displayed:

```python
team_emojis = ("⚪", "⚫")
# ... existing code ...
for i, team in enumerate(meetup.teams):
    display_name = team_display_names[i] if i < len(team_display_names) else team.name
    score = None
    if meetup.result is not None:
        score = meetup.result.score_a if i == 0 else meetup.result.score_b
    escaped = _escape_mdv2(display_name)
    emoji = team_emojis[i] if i < len(team_emojis) else ""
    header = rf"{emoji} *{escaped} \({score}\):*" if score is not None else f"\n{emoji} *{escaped}:*"
    lines.append(header)
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "team_emojis"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: add team emojis to format_main_message"
```

---

### Task 3: Add events section with timestamps in format_main_message when result exists

**Files:**
- Modify: `pyball/bot/formatters.py:88-101`
- Test: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing test for events section**

```python
def test_format_main_message_with_result_shows_events():
    """When there's a result, show goals section with timestamps."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]

    event1 = GoalEvent(
        scorer_id=p1,
        assistant_id=p2,
        team="A",
        timestamp=datetime(2026, 4, 12, 20, 10),  # 10 minutes
    )
    event2 = GoalEvent(
        scorer_id=p2,
        assistant_id=None,
        team="B",
        timestamp=datetime(2026, 4, 12, 20, 25),  # 25 minutes
    )
    meetup.set_result(MatchResult(score_a=1, score_b=1, events=(event1, event2)))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_main_message(meetup, player_names, team_display_names=("Claro", "Oscuro"))

    assert "⏱️ *Goles:*" in text
    assert "⚽ 10' Dani (Rafa)" in text
    assert "⚽ 25' Rafa" in text
```

- [ ] **Step 2: Run test to verify it fails**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "with_result_shows_events"`
Expected: FAIL (assertion error showing no events section)

- [ ] **Step 3: Add events section after teams in format_main_message**

In `pyball/bot/formatters.py`, after the teams loop (after line 99):

```python
if meetup.result is not None and meetup.result.events:
    lines.append("")
    lines.append(r"⏱️ *Goles:*")
    for event in meetup.result.events:
        scorer = _escape_mdv2(player_names.get(str(event.scorer_id.value), "?"))
        minute = event.timestamp.strftime("%-M")  # Remove leading zero
        if event.assistant_id:
            assistant = _escape_mdv2(player_names.get(str(event.assistant_id.value), "?"))
            lines.append(rf"- ⚽ {minute}' {scorer} ({assistant})")
        else:
            lines.append(rf"- ⚽ {minute}' {scorer}")
```

Note: The `%-M` format may not work on Windows. Use this alternative:

```python
minutes = (event.timestamp.hour * 60 + event.timestamp.minute) - \
           (meetup.date.hour * 60 + meetup.date.minute)
lines.append(rf"- ⚽ {minutes}' {scorer} ({assistant})")
```

- [ ] **Step 4: Run test to verify it passes**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "with_result_shows_events"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: add events section with timestamps to format_main_message"
```

---

### Task 4: Update format_subs_message with team assignment

**Files:**
- Modify: `pyball/bot/formatters.py:104-133`
- Test: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing tests for subs with teams**

```python
def test_format_subs_message_with_teams_shows_team_assignment():
    """When there's teams, show substitutes with their team color."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    p3 = PlayerId.generate()  # substitute
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.add_player(p3)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {
        str(p1.value): "Luis",
        str(p2.value): "Carlos",
        str(p3.value): "Pedro",
    }
    player_groups = {
        str(p1.value): "regular",
        str(p2.value): "regular",
        str(p3.value): "substitute",
    }
    text = format_subs_message(meetup, player_names, player_groups)

    assert "⚪" in text
    assert "⚫" in text


def test_format_subs_message_with_result_simple():
    """When there's a result, show simple 'Partido terminated'."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.set_teams([Team.create("A", [p1])])
    meetup.set_result(MatchResult(score_a=1, score_b=0, events=()))

    player_names = {str(p1.value): "Luis"}
    player_groups = {str(p1.value): "regular"}
    text = format_subs_message(meetup, player_names, player_groups)

    assert "*Partido terminado*" in text
    assert "Suplentes" not in text
```

- [ ] **Step 2: Run tests to verify they fail**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "subs_with_teams or subs_with_result_simple"`
Expected: FAIL

- [ ] **Step 3: Update format_subs_message logic**

In `pyball/bot/formatters.py`, rewrite `format_subs_message` function:

```python
def format_subs_message(meetup: Meetup, player_names: dict, player_groups: dict) -> str:
    """Format message for substitutes chat - shows substitutes only."""
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")

    if meetup.result is not None:
        return rf"*Partido terminado*"

    suplentes = []
    for player_id in meetup.players:
        player_group = player_groups.get(str(player_id.value), "regular")
        if player_group != "regular":
            name = player_names.get(str(player_id.value), "Unknown")
            suplentes.append((player_id, name))

    if meetup.teams is not None and suplentes:
        team_map = {}
        for i, team in enumerate(meetup.teams):
            for player in team.players:
                team_map[str(player.value)] = i

        team_emojis = ("⚪", "⚫")
        team_display = ("Equipo Claro:", "Equipo Oscuro:")
        subs_by_team = {}
        for player_id, name in suplentes:
            team_idx = team_map.get(str(player_id.value), -1)
            if team_idx not in subs_by_team:
                subs_by_team[team_idx] = []
            subs_by_team[team_idx].append(name)

        lines = [rf"*Convocatoria* `{date_str}` \- Suplentes"]
        lines.append(f"Jugadores apuntados {len(meetup.players)}/10")
        lines.append("")

        for team_idx in sorted(subs_by_team.keys()):
            emoji = team_emojis[team_idx] if team_idx < len(team_emojis) else ""
            display_name = team_display[team_idx] if team_idx < len(team_display) else f"Equipo {team_idx}:"
            names = ", ".join(sorted(subs_by_team[team_idx]))
            lines.append(rf"{emoji} {display_name} {names}")

        return "\n".join(lines)

    sorted_suplentes = sorted([name for _, name in suplentes], key=functools.cmp_to_key(locale.strcoll))

    lines = [rf"*Convocatoria* `{date_str}` \- Suplentes"]
    lines.append(f"Jugadores apuntados {len(meetup.players)}/10")
    lines.append("")

    if sorted_suplentes:
        lines.append(rf"*Suplentes \({len(sorted_suplentes)}\):*")
        for name in sorted_suplentes:
            lines.append(rf"\- {_escape_mdv2(name)}")
    else:
        lines.append("*No hay suplentes*")

    return "\n".join(lines)
```

- [ ] **Step 4: Run tests to verify they pass**

Run: `pytest tests/unit/bot/test_formatters.py -v -k "subs_with_teams or subs_with_result_simple"`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: update format_subs_message with team assignment"
```

---

### Task 5: Run full test suite and lint

**Files:**
- Verify: `tests/unit/bot/test_formatters.py`
- Verify: `pyball/bot/formatters.py`

- [ ] **Step 1: Run full test suite**

Run: `pytest tests/unit/bot/test_formatters.py -v`
Expected: ALL PASS

- [ ] **Step 2: Run linter**

Run: `make lint`
Expected: ALL PASS

- [ ] **Step 3: Commit**

```bash
git commit -m "test: update formatters tests for new message format"
```

---

## Execution Handoff

Plan complete and saved to `docs/superpowers/plans/2026-04-21-telegram-message-formatting-implementation-plan.md`. Two execution options:

**1. Subagent-Driven (recommended)** - I dispatch a fresh subagent per task, review between tasks, fast iteration

**2. Inline Execution** - Execute tasks in this session using executing-plans, batch execution with checkpoints

**Which approach?**