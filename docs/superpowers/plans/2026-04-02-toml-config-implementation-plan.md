# TOML Config Migration Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Replace manual `.env` parsing with TOML config using Python's built-in `tomllib`.

**Architecture:** Load config from `config.toml` (fallback to `example.config.toml`), override with OS environment variables using `PYBALL_` prefix pattern.

**Tech Stack:** Python 3.11+ `tomllib`, TOML 1.0.0

---

## Task 1: Update pyproject.toml Python Version

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Update Python version requirement**

Modify `pyproject.toml`:

```toml
[tool.poetry.dependencies]
python = ">=3.11,<4.0"
```

Run: `grep -A1 "^python" pyproject.toml`
Expected: `python = ">=3.11,<4.0"`

- [ ] **Step 2: Commit**

```bash
git add pyproject.toml
git commit -m "chore: bump Python requirement to 3.11+ for tomllib"
```

---

## Task 2: Create example.config.toml

**Files:**
- Create: `example.config.toml`

- [ ] **Step 1: Create example.config.toml**

Create `example.config.toml`:

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

- [ ] **Step 2: Commit**

```bash
git add example.config.toml
git commit -m "feat: add example.config.toml"
```

---

## Task 3: Rewrite settings.py with TOML Support

**Files:**
- Modify: `pyball/settings.py`

- [ ] **Step 1: Rewrite settings.py**

Replace the entire `pyball/settings.py` with:

```python
"""Application settings."""

import os
import tomllib
from dataclasses import dataclass, field
from pathlib import Path


class SettingsValidationError(ValueError):
    """Raised when required settings are missing or invalid."""
    pass


@dataclass
class Paths:
    data_dir: Path = field(default_factory=lambda: Path("data"))
    players_file: Path = field(init=False)
    meetups_dir: Path = field(init=False)
    mappings_file: Path = field(init=False)

    def __post_init__(self) -> None:
        self.players_file = self.data_dir / "players.json"
        self.meetups_dir = self.data_dir / "meetups"
        self.mappings_file = self.data_dir / "bot" / "mappings.json"


def _get_env_override(section: str, key: str, default):
    """Get environment variable override for config value.
    
    Env var format: PYBALL_<SECTION>_<KEY>
    Example: PYBALL_TELEGRAM_BOT_TOKEN
    """
    env_key = f"PYBALL_{section.upper()}_{key.upper()}"
    env_value = os.environ.get(env_key)
    if env_value is None:
        return default
    return env_value


def _parse_admins_ids(value) -> tuple[int, ...]:
    """Parse admins_ids from config or env override."""
    if isinstance(value, list):
        return tuple(int(x) for x in value)
    if isinstance(value, str):
        return tuple(int(x.strip()) for x in value.split(",") if x.strip())
    return ()


@dataclass
class TelegramSettings:
    bot_token: str = ""
    admins_ids: tuple[int, ...] = ()

    def is_authorized(self, user_id: int) -> bool:
        """Check if user ID is in the admin list."""
        return user_id in self.admins_ids


@dataclass
class LocaleSettings:
    value: str = "en_US.UTF-8"


@dataclass
class Settings:
    telegram: TelegramSettings = field(default_factory=TelegramSettings)
    locale: LocaleSettings = field(default_factory=LocaleSettings)
    paths: Paths = field(default_factory=Paths)


def load_settings(config_path: Path = Path("config.toml")) -> Settings:
    """Load settings from TOML config file with env var overrides.
    
    Args:
        config_path: Path to config.toml (defaults to project root)
    
    Returns:
        Settings instance with loaded configuration
    
    Raises:
        SettingsValidationError: If required settings are missing
    """
    example_path = Path("example.config.toml")
    
    if config_path.exists():
        with open(config_path, "rb") as f:
            config = tomllib.load(f)
    elif example_path.exists():
        with open(example_path, "rb") as f:
            config = tomllib.load(f)
    else:
        config = {}

    telegram_cfg = config.get("telegram", {})
    locale_cfg = config.get("locale", {})

    telegram = TelegramSettings(
        bot_token=_get_env_override("telegram", "bot_token", telegram_cfg.get("bot_token", "")),
        admins_ids=_parse_admins_ids(
            _get_env_override("telegram", "admins_ids", telegram_cfg.get("admins_ids", []))
        ),
    )

    if not telegram.bot_token:
        raise SettingsValidationError("bot_token is required but not set")

    locale = LocaleSettings(
        value=_get_env_override("locale", "value", locale_cfg.get("value", "en_US.UTF-8")),
    )

    return Settings(telegram=telegram, locale=locale)
```

- [ ] **Step 2: Run tests to verify**

Run: `poetry run pytest tests/unit/test_settings.py -v`
Expected: Tests may fail - need to update tests

- [ ] **Step 3: Commit**

```bash
git add pyball/settings.py
git commit -m "refactor: rewrite settings with TOML support using tomllib"
```

---

## Task 4: Update Settings Tests

**Files:**
- Modify: `tests/unit/test_settings.py`

- [ ] **Step 1: Update tests for new Settings structure**

Replace `tests/unit/test_settings.py` with:

```python
import pytest
from unittest.mock import patch
from pathlib import Path
from pyball.settings import (
    Settings,
    TelegramSettings,
    LocaleSettings,
    load_settings,
    SettingsValidationError,
)


class TestTelegramSettings:
    def test_is_authorized_returns_true_for_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(123) is True
        assert settings.is_authorized(456) is True
        assert settings.is_authorized(789) is True

    def test_is_authorized_returns_false_for_non_admin(self):
        settings = TelegramSettings(admins_ids=(123, 456, 789))
        assert settings.is_authorized(999) is False

    def test_is_authorized_returns_false_for_empty_list(self):
        settings = TelegramSettings(admins_ids=())
        assert settings.is_authorized(123) is False


class TestLocaleSettings:
    def test_default_locale(self):
        locale = LocaleSettings()
        assert locale.value == "en_US.UTF-8"

    def test_custom_locale(self):
        locale = LocaleSettings(value="es_ES.UTF-8")
        assert locale.value == "es_ES.UTF-8"


class TestLoadSettings:
    @patch.dict("os.environ", {}, clear=True)
    def test_load_from_config_file(self, tmp_path, monkeypatch):
        """Test loading settings from config.toml file."""
        config_content = """
[telegram]
bot_token = "test_token"
admins_ids = [111, 222]

[locale]
value = "es_ES.UTF-8"
"""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        settings = load_settings(config_file)
        
        assert settings.telegram.bot_token == "test_token"
        assert settings.telegram.admins_ids == (111, 222)
        assert settings.locale.value == "es_ES.UTF-8"

    @patch.dict("os.environ", {"PYBALL_TELEGRAM_BOT_TOKEN": "env_token"}, clear=True)
    def test_env_override_bot_token(self, tmp_path, monkeypatch):
        """Test that env vars override config file values."""
        config_content = """
[telegram]
bot_token = "config_token"
admins_ids = [111]

[locale]
value = "en_US.UTF-8"
"""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        settings = load_settings(config_file)
        
        assert settings.telegram.bot_token == "env_token"

    @patch.dict("os.environ", {"PYBALL_TELEGRAM_ADMINS_IDS": "333,444,555"}, clear=True)
    def test_env_override_admins_ids_comma_separated(self, tmp_path, monkeypatch):
        """Test comma-separated env var for admins_ids."""
        config_content = """
[telegram]
bot_token = "test_token"
admins_ids = [111]

[locale]
value = "en_US.UTF-8"
"""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        settings = load_settings(config_file)
        
        assert settings.telegram.admins_ids == (333, 444, 555)

    def test_missing_bot_token_raises_error(self, tmp_path, monkeypatch):
        """Test that missing bot_token raises SettingsValidationError."""
        config_content = """
[telegram]
bot_token = ""
admins_ids = [111]

[locale]
value = "en_US.UTF-8"
"""
        monkeypatch.chdir(tmp_path)
        config_file = tmp_path / "config.toml"
        config_file.write_text(config_content)
        
        with pytest.raises(SettingsValidationError):
            load_settings(config_file)
```

- [ ] **Step 2: Run tests to verify**

Run: `poetry run pytest tests/unit/test_settings.py -v`
Expected: All tests pass

- [ ] **Step 3: Commit**

```bash
git add tests/unit/test_settings.py
git commit -m "test: update settings tests for TOML support"
```

---

## Task 5: Update .gitignore and Remove sample.env

**Files:**
- Modify: `.gitignore`
- Delete: `sample.env`

- [ ] **Step 1: Add config.toml to .gitignore**

Check current `.gitignore`:
```bash
cat .gitignore | grep -E "(config|env)"
```

Add `config.toml` to `.gitignore` if not present.

- [ ] **Step 2: Remove sample.env**

```bash
git rm sample.env
```

- [ ] **Step 3: Commit**

```bash
git add .gitignore
git rm sample.env
git commit -m "chore: add config.toml to gitignore, remove sample.env"
```

---

## Task 6: Update Bot Entrypoint

**Files:**
- Modify: `pyball/bot/entrypoint.py`

- [ ] **Step 1: Verify entrypoint works with new settings**

Check that `entrypoint.py` still works:

```bash
poetry run python -c "from pyball.bot.entrypoint import create_application; print('OK')"
```

Expected: Should fail gracefully if no config exists yet.

- [ ] **Step 2: Commit (if any changes needed)**

If changes needed, commit them.

---

## Verification

1. Run all tests: `poetry run pytest tests/ -v`
2. Verify `example.config.toml` can be copied to `config.toml` and bot starts
3. Verify env vars override config values
