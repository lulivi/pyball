# Config Validation Design

## Overview

Add startup validation to ensure required configuration parameters are present and valid before the application runs.

## Section 1: Required Parameters

The following parameters must be non-empty:
- `telegram.bot_token` - Telegram bot token
- `telegram.regulars.chat_id` - Regulars chat ID
- `telegram.substitutes.chat_id` - Substitutes chat ID
- `telegram.location` - Default meetup location

## Section 2: Validation Implementation

Add validation in `pyball/settings.py` after loading configuration:

```python
def validate_required_settings(settings: Settings) -> None:
    required = [
        ("telegram.bot_token", settings.telegram.bot_token),
        ("telegram.regulars.chat_id", settings.telegram.regulars.chat_id),
        ("telegram.substitutes.chat_id", settings.telegram.substitutes.chat_id),
        ("telegram.location", settings.telegram.location),
    ]
    missing = [name for name, value in required if not value]
    if missing:
        print(f"Error: Faltan parámetros requeridos: {', '.join(missing)}")
        print("Copia example.config.toml a config.toml y completa los valores.")
        sys.exit(1)
```

Call this function in the module or at application startup.

## Section 3: Location Default

Use `telegram.location` as the default meetup location when not provided via `/callup` command.

## Section 4: Error Handling

If validation fails:
- Display error message listing missing parameters
- Show helpful message about copying example.config.toml
- Exit with non-zero code (sys.exit(1))