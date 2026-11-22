"""Tests for settings loading and validation."""

import pytest

from pyball.settings import (
    COLOR_PALETTE,
    AppSettings,
    PyballConfig,
    SettingsValidationError,
    TelegramAlerts,
    _parse_team_colors,
    load_app_settings,
)

_FULL_CORE = """\
[pyball.core]
location = "Test Park"
name = "Test Park FC"
default_week_day = "wednesday"
default_hour = "20:00"
base_url = "http://localhost:8000"
team_colors = ["blanco", "negro"]
locale = "en_US.UTF-8"
display_date_format = "%Y-%m-%d %H:%M"
data_dir = "data"
api_port = 8000
"""


def _write(tmp_path, content: str):
    f = tmp_path / "config.toml"
    f.write_text(content)
    return f


class TestLocaleSettings:
    """Tests for LocaleSettings defaults and customisation."""

    def test_default_locale(self):
        """Default locale is en_US.UTF-8."""
        settings = PyballConfig()
        assert settings.locale == "en_US.UTF-8"

    def test_custom_locale(self):
        """A custom locale value is stored as-is."""
        settings = PyballConfig(locale="es_ES.UTF-8")
        assert settings.locale == "es_ES.UTF-8"

    def test_default_display_date_format(self):
        """Default display_date_format is %Y-%m-%d %H:%M."""
        settings = PyballConfig()
        assert settings.display_date_format == "%Y-%m-%d %H:%M"

    def test_custom_display_date_format(self):
        """A custom display_date_format value is stored as-is."""
        settings = PyballConfig(display_date_format="%d/%b/%Y %H:%M")
        assert settings.display_date_format == "%d/%b/%Y %H:%M"


class TestLoadAppSettings:
    """Tests for load_app_settings — all core fields are required."""

    def test_load_from_config_file(self, tmp_path):
        """Loads pyball.core section with all required fields present."""
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.location == "Test Park"
        assert isinstance(settings, AppSettings)

    def test_missing_config_file_raises(self, tmp_path):
        """Missing config.toml raises SettingsValidationError immediately."""
        with pytest.raises(SettingsValidationError, match="No se encontró"):
            load_app_settings(tmp_path / "nonexistent.toml")

    def test_missing_location_raises(self, tmp_path):
        """Absent location raises SettingsValidationError."""
        config = _FULL_CORE.replace('location = "Test Park"\n', "")
        with pytest.raises(SettingsValidationError, match="core.location"):
            load_app_settings(_write(tmp_path, config))

    def test_missing_any_field_raises(self, tmp_path):
        """Absent required field raises SettingsValidationError listing the key."""
        config = _FULL_CORE.replace('default_week_day = "wednesday"\n', "")
        with pytest.raises(SettingsValidationError, match="core.default_week_day"):
            load_app_settings(_write(tmp_path, config))

    def test_env_override_location(self, tmp_path, monkeypatch):
        """PYBALL_CORE_LOCATION env var counts as providing the field."""
        config = _FULL_CORE.replace('location = "Test Park"\n', "")
        monkeypatch.setenv("PYBALL_CORE_LOCATION", "Env Park")
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.location == "Env Park"

    def test_team_colors_required(self, tmp_path):
        """Omitting team_colors raises SettingsValidationError."""
        config = _FULL_CORE.replace('team_colors = ["blanco", "negro"]\n', "")
        with pytest.raises(SettingsValidationError, match="core.team_colors"):
            load_app_settings(_write(tmp_path, config))

    def test_team_colors_from_config(self, tmp_path):
        """team_colors is loaded from config and resolved correctly."""
        config = _FULL_CORE.replace(
            'team_colors = ["blanco", "negro"]',
            'team_colors = ["amarillo", "negro", "azul"]',
        )
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.team_colors == ("amarillo", "negro", "azul")
        assert settings.pyball.team_emojis == ("🟡", "⚫", "🔵")
        assert settings.pyball.team_hex_bg == ("#fbbf24", "#27272a", "#1d4ed8")

    def test_two_team_colors_from_config_are_honoured(self, tmp_path):
        """A 2-color team_colors list is used as configured, not silently replaced."""
        config = _FULL_CORE.replace(
            'team_colors = ["blanco", "negro"]',
            'team_colors = ["amarillo", "negro"]',
        )
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.team_colors == ("amarillo", "negro", "blanco")
        assert settings.pyball.team_emojis == ("🟡", "⚫", "⚪")

    def test_invalid_team_colors_length_raises_at_load(self, tmp_path):
        """A 1-element team_colors list fails loudly at startup."""
        config = _FULL_CORE.replace(
            'team_colors = ["blanco", "negro"]',
            'team_colors = ["amarillo"]',
        )
        with pytest.raises(SettingsValidationError, match="2 o 3 colores"):
            load_app_settings(_write(tmp_path, config))

    def test_display_date_format_from_config(self, tmp_path):
        """display_date_format is read from config when set."""
        config = _FULL_CORE.replace(
            'display_date_format = "%Y-%m-%d %H:%M"',
            'display_date_format = "%d/%m/%Y %H:%M"',
        )
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.pyball.display_date_format == "%d/%m/%Y %H:%M"


class TestPyballConfigColors:
    """Unit tests for PyballConfig team color resolution."""

    def test_default_team_colors(self):
        """Default team_colors is ('blanco', 'negro', 'rojo')."""
        s = PyballConfig()
        assert s.team_colors == ("blanco", "negro", "rojo")

    def test_default_resolves_emojis(self):
        """Default colors resolve to white, black and red circle emojis."""
        s = PyballConfig()
        assert s.team_emojis == ("⚪", "⚫", "🔴")

    def test_default_resolves_hex_bg(self):
        """Default colors resolve to correct background hex values."""
        s = PyballConfig()
        assert s.team_hex_bg == ("#e4e4e7", "#27272a", "#b91c1c")

    def test_default_resolves_hex_text(self):
        """Default colors resolve to correct text hex values."""
        s = PyballConfig()
        assert s.team_hex_text == ("#27272a", "#e4e4e7", "#fff1f2")

    def test_custom_colors_resolve_correctly(self):
        """Custom team_colors resolve to the correct palette values."""
        s = PyballConfig(team_colors=("amarillo", "negro", "azul"))
        assert s.team_emojis == ("🟡", "⚫", "🔵")
        assert s.team_hex_bg == ("#fbbf24", "#27272a", "#1d4ed8")
        assert s.team_hex_text == ("#422006", "#e4e4e7", "#eff6ff")

    def test_two_colors_auto_fill_a_distinct_third(self):
        """Listing 2 colors keeps them and appends the first unused palette color."""
        s = PyballConfig(team_colors=("amarillo", "negro"))
        assert s.team_colors == ("amarillo", "negro", "blanco")
        assert s.team_emojis == ("🟡", "⚫", "⚪")

    def test_default_two_colors_fill_with_rojo(self):
        """The classic ('blanco', 'negro') pair fills its third slot with 'rojo'."""
        assert PyballConfig(team_colors=("blanco", "negro")).team_colors == (
            "blanco",
            "negro",
            "rojo",
        )

    def test_wrong_number_of_colors_raises(self):
        """A single color (or 4+) raises rather than being silently accepted."""
        with pytest.raises(ValueError, match="2 o 3 colores"):
            PyballConfig(team_colors=("blanco",))

    def test_invalid_color_raises_value_error(self):
        """An unknown color name raises ValueError at construction time."""
        with pytest.raises(ValueError, match="inventado"):
            PyballConfig(team_colors=("azul", "inventado"))

    def test_all_palette_colors_are_valid(self):
        """Every color in COLOR_PALETTE can be used without raising."""
        for color in COLOR_PALETTE:
            PyballConfig(team_colors=(color, "negro"))

    def test_team_colors_defaults_to_three_colors(self):
        """Default team_colors has three entries with fully resolved derived tuples."""
        config = PyballConfig()
        assert config.team_colors == ("blanco", "negro", "rojo")
        assert len(config.team_emojis) == 3
        assert len(config.team_hex_bg) == 3
        assert len(config.team_hex_text) == 3

    def test_parse_team_colors_from_toml_list_of_three(self):
        """A three-element TOML list is parsed and lower-cased."""
        assert _parse_team_colors(["Blanco", "Negro", "Azul"]) == ("blanco", "negro", "azul")

    def test_parse_team_colors_from_env_string_of_three(self):
        """A three-element comma-separated env string is parsed correctly."""
        assert _parse_team_colors("blanco,negro,verde") == ("blanco", "negro", "verde")

    def test_parse_team_colors_from_toml_list_of_two(self):
        """A two-element TOML list is kept as-is (the third is filled in later)."""
        assert _parse_team_colors(["Amarillo", "Negro"]) == ("amarillo", "negro")

    def test_parse_team_colors_from_env_string_of_two(self):
        """A two-element comma-separated env string is kept as-is."""
        assert _parse_team_colors("amarillo,negro") == ("amarillo", "negro")

    def test_parse_team_colors_raises_on_wrong_length(self):
        """A list or string with a length other than 2 or 3 raises, never falls back."""
        with pytest.raises(SettingsValidationError, match="2 o 3 colores"):
            _parse_team_colors(["blanco"])
        with pytest.raises(SettingsValidationError, match="2 o 3 colores"):
            _parse_team_colors("blanco,negro,verde,azul")

    def test_parse_team_colors_raises_on_non_sequence(self):
        """A non-list/non-string value raises instead of silently defaulting."""
        with pytest.raises(SettingsValidationError, match="lista de 2 o 3"):
            _parse_team_colors(42)


class TestTokenSettings:
    """Tests for optional match_token / manage_token config fields."""

    def test_tokens_default_to_empty_string(self):
        """PyballConfig defaults both tokens to empty string."""
        settings = PyballConfig()
        assert settings.match_token == ""
        assert settings.manage_token == ""

    def test_tokens_load_from_config(self, tmp_path):
        """Tokens present in config.toml are loaded correctly."""
        content = _FULL_CORE + 'match_token = "abc"\nmanage_token = "xyz"\n'
        f = _write(tmp_path, content)
        settings = load_app_settings(f)
        assert settings.pyball.match_token == "abc"
        assert settings.pyball.manage_token == "xyz"

    def test_tokens_absent_from_config_default_to_empty(self, tmp_path):
        """Absent token fields do not cause a validation error."""
        f = _write(tmp_path, _FULL_CORE)
        settings = load_app_settings(f)
        assert settings.pyball.match_token == ""
        assert settings.pyball.manage_token == ""

    def test_tokens_env_var_override(self, tmp_path, monkeypatch):
        """Env vars PYBALL_CORE_MATCH_TOKEN / PYBALL_CORE_MANAGE_TOKEN override config."""
        f = _write(tmp_path, _FULL_CORE)
        monkeypatch.setenv("PYBALL_CORE_MATCH_TOKEN", "env-match")
        monkeypatch.setenv("PYBALL_CORE_MANAGE_TOKEN", "env-manage")
        settings = load_app_settings(f)
        assert settings.pyball.match_token == "env-match"
        assert settings.pyball.manage_token == "env-manage"


class TestWebSignupSetting:
    """Tests for the enable_web_signup config field."""

    def test_defaults_to_false(self):
        """PyballConfig defaults enable_web_signup to False."""
        settings = PyballConfig()
        assert settings.enable_web_signup is False

    def test_loads_true_from_config(self, tmp_path):
        """enable_web_signup = true in config.toml is loaded as a Python bool."""
        content = _FULL_CORE + "enable_web_signup = true\n"
        f = _write(tmp_path, content)
        settings = load_app_settings(f)
        assert settings.pyball.enable_web_signup is True

    def test_absent_from_config_defaults_to_false(self, tmp_path):
        """Absent enable_web_signup does not raise and defaults to False."""
        f = _write(tmp_path, _FULL_CORE)
        settings = load_app_settings(f)
        assert settings.pyball.enable_web_signup is False

    def test_env_var_override_true(self, tmp_path, monkeypatch):
        """PYBALL_CORE_ENABLE_WEB_SIGNUP=true overrides an absent config value."""
        f = _write(tmp_path, _FULL_CORE)
        monkeypatch.setenv("PYBALL_CORE_ENABLE_WEB_SIGNUP", "true")
        settings = load_app_settings(f)
        assert settings.pyball.enable_web_signup is True

    def test_env_var_override_false_string(self, tmp_path, monkeypatch):
        """PYBALL_CORE_ENABLE_WEB_SIGNUP=false parses to False, not a truthy string."""
        content = _FULL_CORE + "enable_web_signup = true\n"
        f = _write(tmp_path, content)
        monkeypatch.setenv("PYBALL_CORE_ENABLE_WEB_SIGNUP", "false")
        settings = load_app_settings(f)
        assert settings.pyball.enable_web_signup is False


class TestNameSettings:
    """Tests for the required pyball.core.name field."""

    def test_name_loaded_from_config(self, tmp_path):
        """name is read from config and stored on PyballConfig."""
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.name == "Test Park FC"

    def test_missing_name_raises(self, tmp_path):
        """Absent name raises SettingsValidationError."""
        config = _FULL_CORE.replace('name = "Test Park FC"\n', "")
        with pytest.raises(SettingsValidationError, match="core.name"):
            load_app_settings(_write(tmp_path, config))

    def test_empty_name_raises(self, tmp_path):
        """Empty name raises SettingsValidationError."""
        config = _FULL_CORE.replace('name = "Test Park FC"', 'name = ""')
        with pytest.raises(SettingsValidationError, match=r"core\.name \(está vacío\)"):
            load_app_settings(_write(tmp_path, config))

    def test_env_var_overrides_name(self, tmp_path, monkeypatch):
        """PYBALL_CORE_NAME env var overrides config value."""
        monkeypatch.setenv("PYBALL_CORE_NAME", "Los Tensores")
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.name == "Los Tensores"


class TestInstanceIdentitySettings:
    """Tests for the per-instance theme_color and icons_dir settings."""

    def test_theme_color_and_icons_dir_defaults(self, tmp_path):
        """theme_color defaults to #0f172a and icons_dir to empty."""
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.theme_color == "#0f172a"
        assert settings.pyball.icons_dir == ""

    def test_theme_color_env_override(self, tmp_path, monkeypatch):
        """PYBALL_CORE_THEME_COLOR overrides the config value."""
        monkeypatch.setenv("PYBALL_CORE_THEME_COLOR", "#112233")
        settings = load_app_settings(_write(tmp_path, _FULL_CORE))
        assert settings.pyball.theme_color == "#112233"


class TestMeetupCapacitySetting:
    """Tests for the meetup_capacity setting."""

    def test_defaults_to_ten(self, tmp_path):
        """meetup_capacity defaults to 10."""
        assert load_app_settings(_write(tmp_path, _FULL_CORE)).pyball.meetup_capacity == 10

    def test_config_value(self, tmp_path):
        """meetup_capacity is read from [pyball.core]."""
        config = _FULL_CORE.replace("[pyball.core]", "[pyball.core]\nmeetup_capacity = 14")
        assert load_app_settings(_write(tmp_path, config)).pyball.meetup_capacity == 14

    def test_env_override(self, tmp_path, monkeypatch):
        """PYBALL_CORE_MEETUP_CAPACITY overrides the config value."""
        monkeypatch.setenv("PYBALL_CORE_MEETUP_CAPACITY", "12")
        assert load_app_settings(_write(tmp_path, _FULL_CORE)).pyball.meetup_capacity == 12

    @pytest.mark.parametrize("value", ["0", "1", "diez"])
    def test_invalid_value_raises(self, tmp_path, monkeypatch, value):
        """A capacity below two or not a number is rejected."""
        monkeypatch.setenv("PYBALL_CORE_MEETUP_CAPACITY", value)
        with pytest.raises(SettingsValidationError, match="meetup_capacity"):
            load_app_settings(_write(tmp_path, _FULL_CORE))


class TestPluginsSetting:
    """Tests for the [pyball.plugins.<name>] tables."""

    def test_no_plugins_by_default(self, tmp_path):
        """Without plugin tables there are no plugins."""
        assert not load_app_settings(_write(tmp_path, _FULL_CORE)).plugins

    def test_plugin_table(self, tmp_path):
        """A plugin table gives its name, command and scopes."""
        plugin_table = (
            '[pyball.plugins.example]\ncommand = ["./plugins/example-plugin", "--verbose"]\n'
            'scopes = ["players:read", "meetups:write"]\n'
        )
        config = f"{_FULL_CORE}\n{plugin_table}"
        (plugin,) = load_app_settings(_write(tmp_path, config)).plugins
        assert plugin.name == "example"
        assert plugin.command == ("./plugins/example-plugin", "--verbose")
        assert plugin.scopes == {"players:read", "meetups:write"}

    @pytest.mark.parametrize(
        "table, match",
        [
            ("command = []", "command"),
            ('command = "./x"', "command"),
            ('command = ["./x"]\nscopes = ["admin"]', "scopes"),
        ],
    )
    def test_invalid_plugin_table_raises(self, tmp_path, table, match):
        """An empty command or an unknown scope is rejected."""
        config = _FULL_CORE + f"\n[pyball.plugins.bad]\n{table}\n"
        with pytest.raises(SettingsValidationError, match=match):
            load_app_settings(_write(tmp_path, config))


class TestAlertsSetting:
    """Tests for the [pyball.alerts.telegram] section."""

    def test_off_by_default(self, tmp_path):
        """Without the section alerts are off."""
        assert load_app_settings(_write(tmp_path, _FULL_CORE)).alerts is None

    def test_off_when_chat_id_zero(self, tmp_path):
        """chat_id = 0 turns alerts off, even with a token."""
        config = _FULL_CORE + '\n[pyball.alerts.telegram]\nbot_token = "t"\nchat_id = 0\n'
        assert load_app_settings(_write(tmp_path, config)).alerts is None

    def test_section_values(self, tmp_path):
        """bot_token, chat_id and message_thread_id load from the file."""
        config = _FULL_CORE + (
            '\n[pyball.alerts.telegram]\nbot_token = "t"\nchat_id = -100\n'
            'message_thread_id = "7"\n'
        )
        alerts = load_app_settings(_write(tmp_path, config)).alerts
        assert alerts == TelegramAlerts("t", -100, 7)

    def test_empty_thread_is_none(self, tmp_path):
        """An empty message_thread_id means no topic."""
        config = _FULL_CORE + (
            '\n[pyball.alerts.telegram]\nbot_token = "t"\nchat_id = -100\n'
            'message_thread_id = ""\n'
        )
        alerts = load_app_settings(_write(tmp_path, config)).alerts
        assert alerts is not None and alerts.message_thread_id is None

    def test_env_overrides(self, tmp_path, monkeypatch):
        """PYBALL_ALERTS_TELEGRAM_* override the file, and enable alerts without it."""
        monkeypatch.setenv("PYBALL_ALERTS_TELEGRAM_BOT_TOKEN", "envtok")
        monkeypatch.setenv("PYBALL_ALERTS_TELEGRAM_CHAT_ID", "-200")
        monkeypatch.setenv("PYBALL_ALERTS_TELEGRAM_MESSAGE_THREAD_ID", "3")
        alerts = load_app_settings(_write(tmp_path, _FULL_CORE)).alerts
        assert alerts == TelegramAlerts("envtok", -200, 3)

    def test_chat_without_token_raises(self, tmp_path):
        """A chat with no bot token is rejected instead of silently sending nothing."""
        config = _FULL_CORE + "\n[pyball.alerts.telegram]\nchat_id = -100\n"
        with pytest.raises(SettingsValidationError, match="bot_token"):
            load_app_settings(_write(tmp_path, config))

    def test_non_numeric_chat_id_raises(self, tmp_path):
        """A chat_id that is not a number is rejected."""
        config = _FULL_CORE + '\n[pyball.alerts.telegram]\nbot_token = "t"\nchat_id = "x"\n'
        with pytest.raises(SettingsValidationError, match="chat_id"):
            load_app_settings(_write(tmp_path, config))

    def test_old_telegram_logging_section_is_not_read(self, tmp_path):
        """[pyball.telegram.management.logging] no longer turns alerts on."""
        config = _FULL_CORE + "\n[pyball.telegram.management.logging]\nchat_id = -100\n"
        assert load_app_settings(_write(tmp_path, config)).alerts is None


class TestWorkspacePaths:
    """Relative paths resolve against the folder holding config.toml, not the current one."""

    def test_relative_paths_follow_the_config_file(self, tmp_path, monkeypatch):
        """data_dir, icons_dir and logs/ hang off the config's folder wherever PyBall runs."""
        workspace = tmp_path / "club"
        workspace.mkdir()
        config = _FULL_CORE.replace("[pyball.core]", '[pyball.core]\nicons_dir = "icons"')
        config_path = _write(workspace, config)
        monkeypatch.chdir(tmp_path)

        settings = load_app_settings(config_path)

        assert settings.paths.workspace == workspace.resolve()
        assert settings.paths.meetups_dir == workspace.resolve() / "data" / "meetups"
        assert settings.paths.logs_dir == workspace.resolve() / "logs"
        assert settings.pyball.icons_dir == str(workspace.resolve() / "icons")

    def test_absolute_data_dir_stays_absolute(self, tmp_path):
        """An absolute data_dir is used as given."""
        elsewhere = tmp_path / "elsewhere"
        config = _FULL_CORE.replace('data_dir = "data"', f'data_dir = "{elsewhere}"')
        settings = load_app_settings(_write(tmp_path, config))
        assert settings.paths.data_dir == elsewhere
