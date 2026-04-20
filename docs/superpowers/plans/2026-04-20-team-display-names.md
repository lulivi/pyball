# Team Display Names Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Make team display names ("Claro" / "Oscuro") configurable via `config.toml` instead of hardcoded in HTML and formatters.

**Architecture:** Add `team_display_names: tuple[str, str]` to `PyballSettings`. Pass those names into `format_main_message`, `format_match_result_message`, and `StartMatch` from the bot handlers and container. The HTML reads display names from URL query params (`nameA` / `nameB`) set by `start_match.py`. Internal domain identifiers ("A" / "B") are untouched.

**Tech Stack:** Python 3.12, pytest-asyncio, Telegram Bot API (python-telegram-bot), FastAPI, vanilla JS

---

## File Map

| File | Change |
|------|--------|
| `pyball/settings.py` | Add `team_display_names` field to `PyballSettings`; parse from config + env |
| `example.config.toml` | Document the new optional `team_display_names` key |
| `pyball/bot/formatters.py` | Add `team_display_names` param to `format_main_message` and `format_match_result_message` |
| `pyball/application/meetup/start_match.py` | Accept `team_display_names`; add `nameA`/`nameB` to URL |
| `pyball/application/container.py` | Inject `team_display_names` into `StartMatch` |
| `pyball/bot/handlers/meetup.py` | Pass `settings.pyball.team_display_names` to every `format_main_message` call and `format_match_result_message` call |
| `static/index.html` | Remove hardcoded "Claro"/"Oscuro"; read `nameA`/`nameB` from URL params |
| `tests/unit/test_settings.py` | Tests for new field default + custom value + env-var override |
| `tests/unit/bot/test_formatters.py` | Update all existing formatter tests; add assertions on display names |
| `tests/unit/application/test_meetup_use_cases.py` | Update `StartMatch` tests; assert `nameA`/`nameB` in URL |

---

### Task 1: Add `team_display_names` to settings

**Files:**
- Modify: `pyball/settings.py`
- Modify: `example.config.toml`
- Modify: `tests/unit/test_settings.py`

- [ ] **Step 1: Write failing tests**

Add to `tests/unit/test_settings.py` inside `class TestLoadSettings`:

```python
def test_team_display_names_default(self, tmp_path):
    """team_display_names defaults to ('Claro', 'Oscuro') when not set."""
    config_content = """
[pyball]
location = "Test Park"

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    settings = load_settings(config_file)

    assert settings.pyball.team_display_names == ("Claro", "Oscuro")


def test_team_display_names_custom(self, tmp_path):
    """team_display_names is loaded from config when set."""
    config_content = """
[pyball]
location = "Test Park"
team_display_names = ["Blancos", "Negros"]

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)

    settings = load_settings(config_file)

    assert settings.pyball.team_display_names == ("Blancos", "Negros")


def test_team_display_names_env_override(self, tmp_path, monkeypatch):
    """PYBALL_PYBALL_TEAM_DISPLAY_NAMES env var overrides config."""
    config_content = """
[pyball]
location = "Test Park"
team_display_names = ["Blancos", "Negros"]

[telegram]
bot_token = "test_token"
admins_ids = [111]

[telegram.regulars]
chat_id = -1001234567890

[telegram.substitutes]
chat_id = -1001234567891
"""
    config_file = tmp_path / "config.toml"
    config_file.write_text(config_content)
    monkeypatch.setenv("PYBALL_PYBALL_TEAM_DISPLAY_NAMES", "Rojos,Azules")

    settings = load_settings(config_file)

    assert settings.pyball.team_display_names == ("Rojos", "Azules")
```

- [ ] **Step 2: Run to verify failure**

```bash
nox -e test -- tests/unit/test_settings.py -k "team_display_names" -v
```

Expected: 3 failures — `AttributeError: 'PyballSettings' has no attribute 'team_display_names'`

- [ ] **Step 3: Add field to `PyballSettings` and parse in `load_settings`**

In `pyball/settings.py`, add the field to `PyballSettings`:

```python
@dataclass
class PyballSettings:
    """PyBall-specific configuration."""

    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
    base_url: str = "http://localhost:8000"
    team_display_names: tuple[str, str] = ("Claro", "Oscuro")
```

Add a helper at module level (after `_parse_chat_id`):

```python
def _parse_team_display_names(value) -> tuple[str, str]:
    """Parse team_display_names from config list or comma-separated env string."""
    if isinstance(value, list) and len(value) == 2:
        return (str(value[0]), str(value[1]))
    if isinstance(value, str):
        parts = [p.strip() for p in value.split(",") if p.strip()]
        if len(parts) == 2:
            return (parts[0], parts[1])
    return ("Claro", "Oscuro")
```

In `load_settings`, inside the `pyball = PyballSettings(...)` block, add:

```python
    pyball = PyballSettings(
        location=_get_env_override("pyball", "location", pyball_cfg.get("location", "")),
        default_week_day=_get_env_override(
            "pyball", "default_week_day", pyball_cfg.get("default_week_day", "wednesday")
        ),
        default_hour=_get_env_override(
            "pyball", "default_hour", pyball_cfg.get("default_hour", "20:00")
        ),
        base_url=_get_env_override(
            "pyball", "base_url", pyball_cfg.get("base_url", "http://localhost:8000")
        ),
        team_display_names=_parse_team_display_names(
            _get_env_override(
                "pyball",
                "team_display_names",
                pyball_cfg.get("team_display_names", ["Claro", "Oscuro"]),
            )
        ),
    )
```

- [ ] **Step 4: Run to verify passing**

```bash
nox -e test -- tests/unit/test_settings.py -k "team_display_names" -v
```

Expected: 3 PASSED

- [ ] **Step 5: Document in `example.config.toml`**

Add under the `[pyball]` section, after `base_url`:

```toml
# Optional: Display names for the two teams (shown in Telegram messages and the match UI)
# Override with PYBALL_PYBALL_TEAM_DISPLAY_NAMES (comma-separated, e.g. "Claro,Oscuro")
team_display_names = ["Claro", "Oscuro"]
```

- [ ] **Step 6: Run full test suite and lint**

```bash
nox -e test
nox -e lint
```

Expected: all pass, pylint 10.00/10

- [ ] **Step 7: Commit**

```bash
git add pyball/settings.py example.config.toml tests/unit/test_settings.py
git commit -m "feat: add team_display_names setting to PyballSettings"
```

---

### Task 2: Thread display names through formatters

**Files:**
- Modify: `pyball/bot/formatters.py`
- Modify: `tests/unit/bot/test_formatters.py`

- [ ] **Step 1: Write failing tests**

In `tests/unit/bot/test_formatters.py`, add the import at the top:

```python
from pyball.bot.formatters import (
    _escape_mdv2,
    format_main_message,
    format_match_result_message,
    format_subs_message,
)
```

Replace the existing `test_format_main_message_with_teams` test and add new tests:

```python
def test_format_main_message_with_teams():
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names, team_display_names=("Claro", "Oscuro"))

    assert "*Equipos:*" in text
    assert "Claro" in text
    assert "Oscuro" in text
    assert "Luis" in text or "Carlos" in text


def test_format_main_message_with_teams_shows_custom_display_names():
    """format_main_message uses team_display_names instead of internal 'A'/'B'."""
    meetup = Meetup.create(datetime(2024, 1, 15, 20, 0), "Parque Central")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.add_player(p1)
    meetup.add_player(p2)
    meetup.set_teams([Team.create("A", [p1]), Team.create("B", [p2])])

    player_names = {str(p1.value): "Luis", str(p2.value): "Carlos"}
    text = format_main_message(meetup, player_names, team_display_names=("Blancos", "Negros"))

    assert "Blancos" in text
    assert "Negros" in text
    assert "*A:*" not in text
    assert "*B:*" not in text


def test_format_match_result_message_uses_display_names():
    """format_match_result_message uses team_display_names for score line."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    p1 = PlayerId.generate()
    p2 = PlayerId.generate()
    meetup.teams = [Team.create("A", [p1]), Team.create("B", [p2])]
    meetup.set_result(MatchResult(score_a=2, score_b=1, events=()))

    player_names = {str(p1.value): "Dani", str(p2.value): "Rafa"}
    text = format_match_result_message(
        meetup, player_names, team_display_names=("Claro", "Oscuro")
    )

    assert "Claro" in text
    assert "Oscuro" in text
    assert "*A*" not in text
    assert "*B*" not in text
```

Also update the two existing tests that use `format_main_message` with teams to pass the new parameter:

```python
# test_format_main_message_with_result_shows_score — update call:
text = format_main_message(meetup, player_names, team_display_names=("A", "B"))
# assertions stay the same (they check for "A (3)" etc.)
```

- [ ] **Step 2: Run to verify failure**

```bash
nox -e test -- tests/unit/bot/test_formatters.py -v
```

Expected: failures on tests that call `format_main_message` with the new `team_display_names` kwarg

- [ ] **Step 3: Update `format_main_message` signature and body**

In `pyball/bot/formatters.py`, change `format_main_message`:

```python
def format_main_message(
    meetup: Meetup,
    player_names: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
) -> str:
    """Format message for main (regulars) chat.

    Format varies:
    - Before teams: player list sorted by name
    - After teams: teams only
    - After results: teams + results
    """
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
    lines = [f"*Convocatoria:* `{date_str}`"]

    if meetup.location:
        lines.append(f"*Lugar:* {_escape_mdv2(meetup.location)}")

    lines.append("")

    if meetup.teams is None:
        player_names_list = [player_names.get(str(p.value), "") for p in meetup.players]
        sorted_names = sorted(player_names_list, key=functools.cmp_to_key(locale.strcoll))
        max_players = 10
        lines.append(rf"*Jugadores \({len(meetup.players)}/{max_players}\):*")
        for name in sorted_names:
            lines.append(rf"\- {_escape_mdv2(name)}")
    else:
        lines.append("*Equipos:*")
        for i, team in enumerate(meetup.teams):
            display_name = team_display_names[i] if i < len(team_display_names) else team.name
            score = None
            if meetup.result is not None:
                score = meetup.result.score_a if i == 0 else meetup.result.score_b
            escaped = _escape_mdv2(display_name)
            header = (
                rf"*{escaped} \({score}\):*"
                if score is not None
                else f"\n*{escaped}:*"
            )
            lines.append(header)
            for player in team.players:
                name = _escape_mdv2(player_names.get(str(player.value), "Unknown"))
                lines.append(rf"\- {name}")

    return "\n".join(lines)
```

- [ ] **Step 4: Update `format_match_result_message` signature and body**

In `pyball/bot/formatters.py`, change `format_match_result_message`:

```python
def format_match_result_message(
    meetup: Meetup,
    player_names: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
) -> str:
    """Format a match-finished announcement message.

    Intended to be sent as a new message (not an edit) after the match ends.
    """
    date_str = meetup.date.strftime("%Y/%m/%d %H:%M")
    assert meetup.result is not None
    assert meetup.teams is not None

    score_a = meetup.result.score_a
    score_b = meetup.result.score_b
    name_a = _escape_mdv2(team_display_names[0])
    name_b = _escape_mdv2(team_display_names[1])

    lines = [
        rf"⚽ *Partido terminado* — `{date_str}`",
        "",
        rf"*{name_a}* {score_a} \- {score_b} *{name_b}*",
    ]

    if meetup.result.events:
        lines.append("")
        lines.append(r"📋 *Goles:*")
        for event in meetup.result.events:
            scorer = _escape_mdv2(player_names.get(str(event.scorer_id.value), "?"))
            team = _escape_mdv2(event.team)
            if event.assistant_id:
                assistant = _escape_mdv2(player_names.get(str(event.assistant_id.value), "?"))
                lines.append(rf"\- ⚽ {scorer} \(asist: {assistant}\) \[{team}\]")
            else:
                lines.append(rf"\- ⚽ {scorer} \[{team}\]")

    return "\n".join(lines)
```

- [ ] **Step 5: Run tests to verify passing**

```bash
nox -e test -- tests/unit/bot/test_formatters.py -v
```

Expected: all PASSED

- [ ] **Step 6: Run full test suite and lint**

```bash
nox -e test
nox -e lint
```

Expected: all pass, pylint 10.00/10

- [ ] **Step 7: Commit**

```bash
git add pyball/bot/formatters.py tests/unit/bot/test_formatters.py
git commit -m "feat: add team_display_names param to message formatters"
```

---

### Task 3: Thread display names through handlers

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`

No new tests needed — handler behaviour is covered by integration tests that already exist and by the formatter unit tests above. This task just wires settings into the existing call sites.

- [ ] **Step 1: Pass `team_display_names` to every `format_main_message` call**

There are four call sites in `pyball/bot/handlers/meetup.py`. In each, fetch display names from settings and pass them:

**`close_match_messages` (line ~76):**
The function signature already receives no settings. Settings are available in all callers. Change the function signature to accept `team_display_names`:

```python
async def close_match_messages(
    bot,
    message_store,
    meetup,
    player_names: dict,
    player_groups: dict,
    team_display_names: tuple[str, str] = ("A", "B"),
) -> None:
```

Inside, change the `format_main_message` call to:

```python
text = format_main_message(meetup, player_names, team_display_names=team_display_names)
```

**`pyball/infrastructure/http/app.py` — caller of `close_match_messages` (line ~123):**

`settings` is already a parameter of `create_app`, so pass it through the closure:

```python
await close_match_messages(
    bot,
    message_store,
    meetup,
    player_names,
    player_groups,
    team_display_names=settings.pyball.team_display_names,
)
```

**`create_teams_handler` (line ~414):**

```python
settings = context.bot_data["settings"]
# already retrieved above as 'settings'
text = format_main_message(
    meetup, player_names, team_display_names=settings.pyball.team_display_names
)
```

**`_send_callup_messages` (line ~233):**
The function receives `settings` as a parameter. Change the `format_main_message` call:

```python
text = format_main_message(
    meetup, player_names, team_display_names=settings.pyball.team_display_names
)
```

**`_refresh_callup_messages` (line ~630):**
The function receives `settings`. Change the `format_main_message` call:

```python
text = format_main_message(
    meetup, player_names, team_display_names=settings.pyball.team_display_names
)
```

- [ ] **Step 2: Run full test suite and lint**

```bash
nox -e test
nox -e lint
```

Expected: all pass, pylint 10.00/10

- [ ] **Step 3: Commit**

```bash
git add pyball/bot/handlers/meetup.py pyball/infrastructure/http/app.py
git commit -m "feat: pass team_display_names from settings to formatters in handlers"
```

---

### Task 4: Add `nameA`/`nameB` to `StartMatch` URL

**Files:**
- Modify: `pyball/application/meetup/start_match.py`
- Modify: `pyball/application/container.py`
- Modify: `tests/unit/application/test_meetup_use_cases.py`

- [ ] **Step 1: Write failing test**

In `tests/unit/application/test_meetup_use_cases.py`, inside `class TestStartMatch`, update `setup_method`:

```python
def setup_method(self):
    """Set up StartMatch use case with fake repositories."""
    # pylint: disable=attribute-defined-outside-init
    self.meetup_repo = FakeMeetupRepository()
    self.player_repo = FakePlayerRepository()
    self.use_case = StartMatch(
        self.meetup_repo,
        self.player_repo,
        "http://pyball:8000",
        team_display_names=("Claro", "Oscuro"),
    )
```

Add a new test to `TestStartMatch`:

```python
def test_url_contains_name_params(self):
    """StartMatch URL contains nameA and nameB query params with display names."""
    meetup = Meetup.create(datetime(2026, 4, 12, 20, 0), "Campo Norte")
    self._add_players_and_teams(meetup)

    url = self.use_case.execute("2026/04/12 20:00")

    assert "nameA=Claro" in url or "nameA=Claro" in urllib.parse.unquote(url)
    assert "nameB=Oscuro" in url or "nameB=Oscuro" in urllib.parse.unquote(url)
```

Also add the import at the top of the test file if not present:

```python
import urllib.parse
```

- [ ] **Step 2: Run to verify failure**

```bash
nox -e test -- tests/unit/application/test_meetup_use_cases.py::TestStartMatch -v
```

Expected: `TypeError: StartMatch.__init__() got an unexpected keyword argument 'team_display_names'`

- [ ] **Step 3: Update `StartMatch`**

In `pyball/application/meetup/start_match.py`, update `__init__` and `execute`:

```python
class StartMatch:
    """Use case for generating a match tracking URL."""

    def __init__(
        self,
        meetup_repository: MeetupRepository,
        player_repository: PlayerRepository,
        base_url: str,
        team_display_names: tuple[str, str] = ("A", "B"),
    ):
        """Initialize with repositories, the base URL, and team display names."""
        self.meetup_repository = meetup_repository
        self.player_repository = player_repository
        self.base_url = base_url
        self.team_display_names = team_display_names

    def execute(self, date_str: str) -> str:
        """Generate the match tracking URL for the given meetup date."""
        try:
            meetup_date = datetime.strptime(date_str, "%Y/%m/%d %H:%M")
        except ValueError as exc:
            raise ValueError("Invalid date format. Use: YYYY/MM/DD HH:MM") from exc

        meetup = self.meetup_repository.find_by_date(meetup_date.date())
        if meetup is None:
            raise MeetupNotFoundError(date_str)

        if meetup.teams is None:
            raise MeetupHasNoTeamsError("Meetup has no teams. Run /create_teams first.")

        all_players = self.player_repository.find_all()
        player_names = {str(p.id.value): p.name for p in all_players}

        team_a_names = [player_names[str(pid.value)] for pid in meetup.teams[0].players]
        team_b_names = [player_names[str(pid.value)] for pid in meetup.teams[1].players]

        params = urllib.parse.urlencode(
            {
                "date": meetup_date.strftime("%Y-%m-%dT%H:%M"),
                "teamA": ",".join(team_a_names),
                "teamB": ",".join(team_b_names),
                "nameA": self.team_display_names[0],
                "nameB": self.team_display_names[1],
            }
        )
        return f"{self.base_url}/?{params}"
```

- [ ] **Step 4: Update `Container.start_match()` to inject display names**

In `pyball/application/container.py`, change `start_match`:

```python
def start_match(self) -> StartMatch:
    """Create a new StartMatch use case."""
    return StartMatch(
        self.meetup_repository,
        self.player_repository,
        self._settings.pyball.base_url,
        team_display_names=self._settings.pyball.team_display_names,
    )
```

- [ ] **Step 5: Run tests to verify passing**

```bash
nox -e test -- tests/unit/application/test_meetup_use_cases.py::TestStartMatch -v
```

Expected: all PASSED

- [ ] **Step 6: Run full test suite and lint**

```bash
nox -e test
nox -e lint
```

Expected: all pass, pylint 10.00/10

- [ ] **Step 7: Commit**

```bash
git add pyball/application/meetup/start_match.py pyball/application/container.py \
        tests/unit/application/test_meetup_use_cases.py
git commit -m "feat: include nameA/nameB display names in StartMatch URL"
```

---

### Task 5: Remove hardcoded names from `static/index.html`

**Files:**
- Modify: `static/index.html`

No unit test — the HTML is a single-file frontend with no test infrastructure.

- [ ] **Step 1: Replace hardcoded `<div class="team-name">` contents**

Find (around line 49):
```html
            <div class="team-name">Claro</div>
```
Replace with:
```html
            <div class="team-name" id="name-a">—</div>
```

Find (around line 54):
```html
            <div class="team-name">Oscuro</div>
```
Replace with:
```html
            <div class="team-name" id="name-b">—</div>
```

- [ ] **Step 2: Read `nameA`/`nameB` from URL params in `initializeApp`**

In the JS `initializeApp` function, after:
```js
teamA = teamAParam.split(',');
teamB = teamBParam.split(',');
localStorage.setItem('pyball_teams', JSON.stringify({ teamA, teamB, meetupDate }));
```

Add the following lines to also store and apply the display names:

```js
const nameA = params.get('nameA') || 'A';
const nameB = params.get('nameB') || 'B';
document.getElementById('name-a').innerText = nameA;
document.getElementById('name-b').innerText = nameB;
localStorage.setItem('pyball_teams', JSON.stringify({ teamA, teamB, meetupDate, nameA, nameB }));
```

Also update the restore-from-localStorage branch (the `if (savedState && savedTeams)` block) to restore display names:

```js
if (savedState && savedTeams) {
    appState = JSON.parse(savedState);
    const teams = JSON.parse(savedTeams);
    teamA = teams.teamA;
    teamB = teams.teamB;
    meetupDate = teams.meetupDate;
    document.getElementById('name-a').innerText = teams.nameA || 'A';
    document.getElementById('name-b').innerText = teams.nameB || 'B';
    updateUI();
    return;
}
```

- [ ] **Step 3: Run full test suite**

```bash
nox -e test
nox -e lint
```

Expected: all pass

- [ ] **Step 4: Commit**

```bash
git add static/index.html
git commit -m "feat: read team display names from URL params in match UI"
```
