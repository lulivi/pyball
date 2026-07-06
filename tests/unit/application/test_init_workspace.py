"""Unit tests for init_workspace."""

import os

import pytest

from pyball.application.init_workspace import init_workspace


class TestInitWorkspaceWeb:
    """Tests for web topology workspace initialisation."""

    def test_creates_all_files_and_dirs(self, tmp_path):
        """Web bootstrap generates config.toml, compose.yaml, .env, README.md and dirs."""
        init_workspace("web", tmp_path / "config.toml")

        assert (tmp_path / "config.toml").exists()
        assert (tmp_path / "compose.yaml").exists()
        assert (tmp_path / ".env").exists()
        assert (tmp_path / "README.md").exists()
        assert (tmp_path / "data").is_dir()
        assert (tmp_path / "data" / "meetups").is_dir()
        assert (tmp_path / "logs").is_dir()

    def test_config_excludes_telegram_section(self, tmp_path):
        """Web config.toml must not contain the [pyball.telegram] section."""
        init_workspace("web", tmp_path / "config.toml")

        content = (tmp_path / "config.toml").read_text()
        assert "[pyball.telegram]" not in content

    def test_compose_references_web_image(self, tmp_path):
        """Web compose.yaml references the pyball-web image."""
        init_workspace("web", tmp_path / "config.toml")

        content = (tmp_path / "compose.yaml").read_text()
        assert "pyball-web" in content

    def test_env_contains_uid_gid(self, tmp_path):
        """.env is pre-populated with the current process UID and GID."""
        init_workspace("web", tmp_path / "config.toml")

        content = (tmp_path / ".env").read_text()
        assert f"UID={os.getuid()}" in content
        assert f"GID={os.getgid()}" in content

    def test_env_contains_port_and_tag(self, tmp_path):
        """.env includes PORT and TAG defaults."""
        init_workspace("web", tmp_path / "config.toml")

        content = (tmp_path / ".env").read_text()
        assert "PORT=8000" in content
        assert "TAG=latest" in content


class TestInitWorkspaceTg:
    """Tests for Telegram topology workspace initialisation."""

    def test_config_includes_telegram_section(self, tmp_path):
        """Telegram config.toml contains the [pyball.telegram] section."""
        init_workspace("tg", tmp_path / "config.toml")

        content = (tmp_path / "config.toml").read_text()
        assert "[pyball.telegram]" in content

    def test_compose_references_tg_image(self, tmp_path):
        """Telegram compose.yaml references the pyball-telegram image."""
        init_workspace("tg", tmp_path / "config.toml")

        content = (tmp_path / "compose.yaml").read_text()
        assert "pyball-telegram" in content


class TestInitWorkspaceErrors:
    """Tests for blocking-error behaviour."""

    def test_fails_if_config_exists(self, tmp_path):
        """Exits with code 1 when config.toml already exists."""
        (tmp_path / "config.toml").touch()

        with pytest.raises(SystemExit) as exc_info:
            init_workspace("web", tmp_path / "config.toml")

        assert exc_info.value.code == 1

    def test_fails_if_compose_exists(self, tmp_path):
        """Exits with code 1 when compose.yaml already exists."""
        (tmp_path / "compose.yaml").touch()

        with pytest.raises(SystemExit) as exc_info:
            init_workspace("web", tmp_path / "config.toml")

        assert exc_info.value.code == 1

    def test_fails_if_env_exists(self, tmp_path):
        """Exits with code 1 when .env already exists."""
        (tmp_path / ".env").touch()

        with pytest.raises(SystemExit) as exc_info:
            init_workspace("web", tmp_path / "config.toml")

        assert exc_info.value.code == 1

    def test_skips_readme_if_exists(self, tmp_path, capsys):
        """Does not overwrite README.md if it already exists; prints a warning."""
        readme = tmp_path / "README.md"
        readme.write_text("existing content", encoding="utf-8")

        init_workspace("web", tmp_path / "config.toml")

        assert readme.read_text() == "existing content"
        assert "Skipped  README.md" in capsys.readouterr().out

    def test_reports_all_blocking_errors_at_once(self, tmp_path, capsys):
        """All three blocking files are checked before exiting."""
        (tmp_path / "config.toml").touch()
        (tmp_path / "compose.yaml").touch()
        (tmp_path / ".env").touch()

        with pytest.raises(SystemExit):
            init_workspace("web", tmp_path / "config.toml")

        err = capsys.readouterr().err
        assert "config.toml" in err
        assert "compose.yaml" in err
        assert ".env" in err


class TestInitWorkspaceDirectory:
    """Tests for config_path directory handling."""

    def test_respects_config_path_directory(self, tmp_path):
        """Files are created in the parent dir of config_path, not hardcoded CWD."""
        subdir = tmp_path / "deploy"
        subdir.mkdir()

        init_workspace("web", subdir / "config.toml")

        assert (subdir / "config.toml").exists()
        assert (subdir / "compose.yaml").exists()
        assert not (tmp_path / "config.toml").exists()
