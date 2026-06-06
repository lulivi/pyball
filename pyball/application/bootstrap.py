# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Shared bootstrap logic for all application topologies."""

import locale
import logging
from pathlib import Path

from pyball import __version__
from pyball.application.container import Container
from pyball.logger import config_logging
from pyball.settings import AppSettings, load_app_settings

logger = logging.getLogger(__name__)


def bootstrap_core(config_path: Path = Path("config.toml")) -> tuple[AppSettings, Container]:
    """Initialise shared application components common to all topologies.

    Loads pyball.core settings, configures logging, sets locale, and builds
    the DI container. Integration-specific setup (Telegram, logging handlers,
    etc.) is the caller's responsibility.

    Args:
        config_path: Path to the TOML config file.

    Returns:
        Tuple of (AppSettings, Container).
    """
    settings = load_app_settings(config_path)
    container = Container(settings)
    config_logging()
    locale.setlocale(locale.LC_ALL, settings.pyball.locale)
    _log_startup_info(settings, container)
    return settings, container


def _log_startup_info(settings: AppSettings, container: Container) -> None:
    """Log version banner at startup."""
    startup_message_lines = [
        "Starting PyBall",
        f"Version: v{__version__}",
        f"URL: {container.instance_url}",
    ]
    if settings.pyball.match_token:
        startup_message_lines.append(
            f"    Match url: {container.instance_url}"
            f"/match?token={settings.pyball.match_token}"
        )
    if settings.pyball.manage_token:
        startup_message_lines.append(
            f"    Manage url: {container.instance_url}"
            f"/manage?token={settings.pyball.manage_token}"
        )

    logger.info("*" * 40)
    logger.info("\n* ".join(startup_message_lines))
    logger.info("*" * 40)
