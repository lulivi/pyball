# Config Validation Design

## Overview

Add startup validation to ensure required configuration parameters are present and valid before the application runs. Add a `[pyball]` section for application-level settings.

## Section 1: New Config Structure

```toml
[pyball]
# Required: Default location for meetups
location = "someplace"

# Optional: Default datetime for meetups
default_week_day = "wednesday"
default_hour = "20:00"

[telegram]
# Required: Telegram bot token
bot_token = ""

# Required: Regulars and substitutes chat IDs
[telegram.regulars]
chat_id = ""

[telegram.substitutes]
chat_id = ""
```

## Section 2: Required Parameters

The following parameters must be non-empty:
- `telegram.bot_token` - Telegram bot token
- `telegram.regulars.chat_id` - Regulars chat ID  
- `telegram.substitutes.chat_id` - Substitutes chat ID
- `pyball.location` - Default meetup location

## Section 3: Settings Classes

Add new `PyballSettings` dataclass in `settings.py`:

```python
@dataclass
class PyballSettings:
    location: str = ""
    default_week_day: str = "wednesday"
    default_hour: str = "20:00"
```

Add to `Settings`:
```python
@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    pyball: PyballSettings = field(default_factory=PyballSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)
```

## Section 4: Validation Implementation

In `load_settings()`, validate required params:

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

## Section 5: Default Meetup Values

When creating a meetup via `/callup` without explicit parameters:
- No location provided → use `pyball.location`
- No date/time provided → use `pyball.default_week_day` + `pyball.default_hour`

## Section 6: Error Handling

If validation fails:
- Raise `SettingsValidationError` with message listing missing parameters
- Error message includes hint to copy example.config.toml