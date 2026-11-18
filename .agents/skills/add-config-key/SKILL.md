---
name: add-config-key
description: Add, rename or remove a PyBall config.toml key. Use whenever a change touches PyballConfig, TelegramSettings or any [pyball.*] section, so the key's three documentation places stay in sync.
---

# Add a config key

A config key is documented in exactly three places, and each one drifts if only another is
updated. A change to any key — adding, renaming, removing, or changing its default —
touches all of them in the same commit.

## Steps

1. **Settings.** Add the field and its loading in the loader for its section:
   - `[pyball.core]`: a `PyballConfig` field, plus the key in `core_keys` in
     `load_app_settings()` (`pyball/settings.py`). An optional key gets its default
     there, beside `theme_color`'s; any other key missing from the file is reported as
     missing.
   - `[pyball.telegram]` and its sub-sections: `TelegramSettings` (or its chat config
     classes) and `load_telegram_app_settings()` in
     `pyball/infrastructure/telegram/settings.py`.

   Read the value through the module's `_get_env_override()`, so it can be overridden by
   the env var `PYBALL_<SECTION>_<KEY>`: the `pyball.` prefix dropped, dots turned into
   underscores, upper-cased (`pyball.core.location` → `PYBALL_CORE_LOCATION`,
   `pyball.telegram.regulars.meetups.chat_id` →
   `PYBALL_TELEGRAM_REGULARS_MEETUPS_CHAT_ID`). Parse and validate it beside the
   existing `_parse_*` helpers, raising `SettingsValidationError` for bad values.
2. **Template.** Add the key, with its default and a one-line comment, to the
   `config.toml` template in `pyball/application/init_workspace.py`: `_CORE_CONFIG` for
   core keys, `_TG_CONFIG_EXTRA` for Telegram keys.
3. **Docs.** Add a row to the section's table in `docs/setup.md` and the same row,
   translated, in `docs/setup.es.md`.
4. **Tests.** Cover the default, a `config.toml` value and the env override in
   `tests/unit/test_settings.py` or `tests/unit/infrastructure/test_telegram_settings.py`.

Done when the key appears in the settings class, the template and both setup tables, and
`make lint` and `make test` pass.
