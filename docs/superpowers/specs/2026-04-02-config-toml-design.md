# Config Format Migration - TOML

## Overview

Replace manual `.env` parsing with TOML config using Python's built-in `tomllib`. Support OS environment variable overrides.

## Architecture

```
config.toml (gitignored)     example.config.toml (committed)
├── telegram                 ├── telegram
│   ├── bot_token = ""      │   ├── bot_token = ""  # Required
│   └── admins_ids = [...]  │   └── admins_ids = [123, 456]
└── locale                  └── locale
    └── value = "en_US"         └── value = "en_US.UTF-8"
```

**Config loading order:**
1. Load `config.toml` (with fallback to `example.config.toml` for defaults)
2. Override with OS environment variables if set

**Env override pattern:** `SECTION_KEY` → `PYBALL_SECTION_KEY`
- `telegram.bot_token` → `PYBALL_TELEGRAM_BOT_TOKEN`
- `telegram.admins_ids` → `PYBALL_TELEGRAM_ADMINS_IDS`
- `locale.value` → `PYBALL_LOCALE_VALUE`

## Files

### Create: `example.config.toml`

```toml
# PyBall Configuration
# Copy this file to config.toml and fill in your values
# Environment variables can override any value using PYBALL_<SECTION>_<KEY> pattern

[telegram]
# Required: Telegram bot token
# Override with PYBALL_TELEGRAM_BOT_TOKEN
bot_token = ""

# Required: List of authorized Telegram user IDs
# Override with PYBALL_TELEGRAM_ADMINS_IDS (comma-separated)
admins_ids = [123456789, 987654321]

[locale]
# Player names locale for sorting
# Override with PYBALL_LOCALE_VALUE
value = "en_US.UTF-8"
```

### Modify: `pyball/settings.py`

- Use `tomllib.load()` to parse config
- Support env variable overrides with `PYBALL_` prefix
- Keep dataclass structure for type safety

### Delete: `sample.env`

### Modify: `.gitignore`

Add `config.toml`

## Tech Stack

- Python 3.11+ (built-in `tomllib`)
- TOML 1.0.0 format

## Testing

- Unit tests for TOML parsing
- Unit tests for env override logic
- Integration test for full config loading
