# Config Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add startup validation for required config params and use pyball settings as defaults for meetups

**Architecture:** Add PyballSettings dataclass, validate at load time, update /callup handler

**Tech Stack:** Python, pytest

---

## Task 1: Add PyballSettings dataclass

**Files:**
- Modify: `pyball/settings.py:72-80`

- [ ] **Step 1: Read current Settings dataclass around line 77**

```python
@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)
```

- [ ] **Step 2: Add PyballSettings before Settings**

Add:
```python
@dataclass
class PyballSettings:
    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
```

- [ ] **Step 3: Add pyball field to Settings**

Replace:
```python
@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)
```

With:
```python
@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pyball: PyballSettings = field(default_factory=PyballSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)
```

- [ ] **Step 4: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: add PyballSettings dataclass"
```

---

## Task 2: Load pyball config section

**Files:**
- Modify: `pyball/settings.py:107-146`

- [ ] **Step 1: Read load_settings function around line 107**

After `telegram_cfg = config.get("telegram", {})`, add:
```python
pyball_cfg = config.get("pyball", {})

pyball_settings = PyballSettings(
    location=_get_env_override("pyball", "location", pyball_cfg.get("location", "")),
    default_week_day=_get_env_override("pyball", "default_week_day", pyball_cfg.get("default_week_day", "wednesday")),
    default_hour=_get_env_override("pyball", "default_hour", pyball_cfg.get("default_hour", "20:00")),
)
```

- [ ] **Step 2: Update Settings return to include pyball**

Find return statement around line 145:
```python
return Settings(telegram=telegram, locale=locale)
```

Replace with:
```python
return Settings(telegram=telegram, pyball=pyball_settings, locale=locale)
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: load pyball config section"
```

---

## Task 3: Add validation for required settings

**Files:**
- Modify: `pyball/settings.py` (after telegram validation around line 139)

- [ ] **Step 1: Read current validation around line 139**

- [ ] **Step 2: Add pyball.location validation**

Find current:
```python
if not telegram.bot_token:
    raise SettingsValidationError("bot_token is required but not set")
```

Replace with:
```python
missing = []
if not telegram.bot_token:
    missing.append("telegram.bot_token")
if not pyball_settings.location:
    missing.append("pyball.location")
if not telegram.regulars.chat_id:
    missing.append("telegram.regulars.chat_id")
if not telegram.substitutes.chat_id:
    missing.append("telegram.substitutes.chat_id")

if missing:
    raise SettingsValidationError(
        f"Faltan parámetros requeridos: {', '.join(missing)}. "
        "Copia example.config.toml a config.toml y completa los valores."
    )
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: validate required config params at startup"
```

---

## Task 4: Update example.config.toml

**Files:**
- Modify: `example.config.toml`

- [ ] **Step 1: Read example.config.toml**

- [ ] **Step 2: Replace content**

Replace current with:
```toml
# PyBall Configuration
# Copy this file to config.toml and fill in your values
# Environment variables can override any value using PYBALL_<SECTION>_<KEY> pattern

[pyball]
# Required: Default location for meetups
# Override with PYBALL_PYBALL_LOCATION
location = "Parque Central"

# Optional: Default weekday for meetups (monday, tuesday, wednesday, thursday, friday, saturday, sunday)
# Override with PYBALL_PYBALL_DEFAULT_WEEK_DAY
default_week_day = "wednesday"

# Optional: Default hour for meetups (HH:MM format)
# Override with PYBALL_PYBALL_DEFAULT_HOUR
default_hour = "20:00"

[telegram]
# Required: Telegram bot token
# Override with PYBALL_TELEGRAM_BOT_TOKEN
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"

# Required: List of authorized Telegram user IDs
# Override with PYBALL_TELEGRAM_ADMINS_IDS (comma-separated)
admins_ids = [123456789, 987654321]

[telegram.regulars]
# Required: The main chat ID (negative number for groups)
# Override with PYBALL_TELEGRAM_REGULARS_CHAT_ID
chat_id = -1001234567890

# Optional: The thread inside the group
# Override with PYBALL_TELEGRAM_REGULARS_THREAD_ID
thread_id = ""

[telegram.substitutes]
# Required: The substitutes chat ID (negative number for groups)
# Override with PYBALL_TELEGRAM_SUBSTITUTES_CHAT_ID
chat_id = -1001234567891

[locale]
# Player names locale for sorting
# Override with PYBALL_LOCALE_VALUE
value = "en_US.UTF-8"
```

- [ ] **Step 3: Commit**

```bash
git add example.config.toml
git commit -m "feat: update example.config.toml with pyball section"
```

---

## Task 5: Update /callup handler to use pyball defaults

**Files:**
- Modify: `pyball/bot/handlers/meetup.py:225-246`

- [ ] **Step 1: Read meetup.py around line 225-246**

```python
if not context.args:
    await update.message.reply_text("Usage: /callup YYYY-MM-DD HH:MM [location]")
    return

date_str = " ".join(context.args[:-1]) if len(context.args) > 2 else context.args[0]
time_str = context.args[1] if len(context.args) > 1 else "20:00"
location = context.args[2] if len(context.args) > 2 else "Park"
```

- [ ] **Step 2: Update to use pyball settings defaults**

Replace with:
```python
if not context.args:
    # Use defaults from pyball settings
    date_str = settings.pyball.default_week_day
    time_str = settings.pyball.default_hour
    location = settings.pyball.location
else:
    date_str = context.args[0]
    time_str = context.args[1] if len(context.args) > 1 else settings.pyball.default_hour
    location = context.args[2] if len(context.args) > 2 else settings.pyball.location
```

- [ ] **Step 3: Remove unnecessary chat_id check (line 240-242)**

Remove:
```python
if not settings.telegram.regulars.chat_id:
    await update.message.reply_text("Regulars chat not configured.")
    return
```

- [ ] **Step 4: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/handlers/meetup.py
git commit -m "feat: use pyball settings as defaults for /callup"
```

---

## Task 6: Verify startup validation works

**Files:**
- Test: Run the application

- [ ] **Step 1: Run with missing config**

Run: `python -c "from pyball.settings import load_settings; load_settings()"`
Expected: SettingsValidationError with message about missing params

- [ ] **Step 2: Run with valid config**

Run: `python -c "from pyball.settings import load_settings; s = load_settings(); print(s.pyball.location, s.pyball.default_week_day, s.pyball.default_hour)"`
Expected: Print values from config