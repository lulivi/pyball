# Config Validation Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add startup validation for required config params and use telegram.location as default for meetups

**Architecture:** Validate settings at load time, add location field to TelegramSettings, update /callup handler

**Tech Stack:** Python, pytest

---

## Task 1: Add location field to TelegramSettings

**Files:**
- Modify: `pyball/settings.py:60-70`

- [ ] **Step 1: Read TelegramSettings class**

```python
@dataclass
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()
    location: str = ""
    regulars: TelegramChatSettings = field(default_factory=TelegramChatSettings)
    substitutes: TelegramChatSettings = field(default_factory=TelegramChatSettings)
```

- [ ] **Step 2: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 3: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: add location field to TelegramSettings"
```

---

## Task 2: Load location from config

**Files:**
- Modify: `pyball/settings.py:130-137`

- [ ] **Step 1: Read load_settings function around line 130**

- [ ] **Step 2: Add location loading**

Find:
```python
telegram = TelegramSettings(
    bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
    admins_ids=_parse_admins_ids(
        _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
    ),
    regulars=regulars,
    substitutes=substitutes,
)
```

Replace with:
```python
telegram = TelegramSettings(
    bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
    admins_ids=_parse_admins_ids(
        _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
    ),
    location=_get_env_override("telegram", "location", telegram_cfg.get("location", "")),
    regulars=regulars,
    substitutes=substitutes,
)
```

- [ ] **Step 3: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 4: Commit**

```bash
git add pyball/settings.py
git commit -m "feat: load location from config"
```

---

## Task 3: Add validation for required settings

**Files:**
- Modify: `pyball/settings.py:139-141`

- [ ] **Step 1: Read current validation around line 139**

Current code:
```python
if not telegram.bot_token:
    raise SettingsValidationError("bot_token is required but not set")
```

- [ ] **Step 2: Extend validation**

Replace with:
```python
missing = []
if not telegram.bot_token:
    missing.append("telegram.bot_token")
if not telegram.location:
    missing.append("telegram.location")
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

## Task 4: Update /callup handler to use settings.location as default

**Files:**
- Modify: `pyball/bot/handlers/meetup.py:231`

- [ ] **Step 1: Read meetup.py around line 223-231**

```python
settings = load_settings()

if not context.args:
    await update.message.reply_text("Usage: /callup YYYY-MM-DD HH:MM [location]")
    return

date_str = " ".join(context.args[:-1]) if len(context.args) > 2 else context.args[0]
time_str = context.args[1] if len(context.args) > 1 else "20:00"
location = context.args[2] if len(context.args) > 2 else "Park"
```

- [ ] **Step 2: Change default location**

Replace:
```python
location = context.args[2] if len(context.args) > 2 else "Park"
```

With:
```python
location = context.args[2] if len(context.args) > 2 else settings.telegram.location
```

- [ ] **Step 3: Remove unnecessary chat_id check (line 240-242)**

Since validation now happens at startup, the check at line 240-242 is redundant:
```python
if not settings.telegram.regulars.chat_id:
    await update.message.reply_text("Regulars chat not configured.")
    return
```

Remove this block.

- [ ] **Step 4: Run existing tests**

Run: `pytest tests/ -v`
Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/handlers/meetup.py
git commit -m "feat: use settings.telegram.location as default for meetups"
```

---

## Task 5: Verify startup validation works

**Files:**
- Test: Run the application

- [ ] **Step 1: Run with missing config**

Run: `python -c "from pyball.settings import load_settings; load_settings()"`
Expected: SettingsValidationError with message about missing params

- [ ] **Step 2: Run with valid config**

Run: `python -c "from pyball.settings import load_settings; s = load_settings(); print(s.telegram.location)"`
Expected: Print location value from config (or empty if not set)