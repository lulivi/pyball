"""The telegram plugin: polls Telegram for commands and buttons while it follows PyBall's
event stream to keep the callups up to date.
"""

from __future__ import annotations

import asyncio
import locale
import logging
import signal
import sys
from pathlib import Path

from pyball_client import Api
from pyball_client.plugin import PluginError, api_token, api_url, load_event_id, save_event_id
from telegram.ext import Application, CallbackQueryHandler

from pyball_telegram import config as plugin_config
from pyball_telegram.api import EVENTS, SETTINGS
from pyball_telegram.callbacks import button_pressed
from pyball_telegram.callups import Callups
from pyball_telegram.commands import register_commands, setup_commands

logger = logging.getLogger("telegram_plugin")


def main() -> None:
    """Run the plugin until PyBall stops it; a fatal error exits non-zero to be restarted."""
    logging.basicConfig(level=logging.INFO, format="%(levelname)s %(name)s: %(message)s")
    logging.getLogger("httpx").setLevel(logging.WARNING)  # one line per Telegram poll otherwise
    try:
        asyncio.run(run(Path("config.toml")))
    except PluginError as exc:
        print(f"error: {exc}", file=sys.stderr)
        sys.exit(1)


async def run(config_path: Path) -> None:
    """Load the config, start polling Telegram and follow the event stream until SIGTERM."""
    config = plugin_config.load(config_path)
    api = Api(api_url(), api_token())
    settings = await api.call(SETTINGS)
    _set_locale(settings.locale)

    application = Application.builder().token(config.bot_token).concurrent_updates(False).build()
    callups = Callups(application.bot, api, config, settings)
    application.bot_data["callups"] = callups
    setup_commands(application)
    application.add_handler(CallbackQueryHandler(button_pressed))

    follower = asyncio.current_task()
    assert follower is not None
    asyncio.get_running_loop().add_signal_handler(signal.SIGTERM, follower.cancel)

    async with application:
        await register_commands(application.bot)
        await application.start()
        assert application.updater is not None
        await application.updater.start_polling()
        logger.info("Polling Telegram; following PyBall's events")
        try:
            await follow_events(callups)
        except asyncio.CancelledError:
            logger.info("Stopping")
        finally:
            await application.updater.stop()
            await application.stop()
            await api.aclose()


async def follow_events(callups: Callups) -> None:
    """Handle every event after the last one handled, reconnecting when the stream ends.

    With no event handled yet, it starts with the next one: replaying the whole log would
    post every callup in history again.
    """
    id_file = callups.config.event_id_file
    while True:
        async for event in callups.api.events(EVENTS, load_event_id(id_file)):
            await callups.handle(event)
            save_event_id(id_file, event.id)
        logger.info("PyBall closed the event stream; reconnecting")
        await asyncio.sleep(1)


def _set_locale(name: str) -> None:
    """Sort names as the club's locale does; keep the default if it is not installed."""
    try:
        locale.setlocale(locale.LC_ALL, name)
    except locale.Error:
        logger.warning("Locale %s is not installed: names sort in the default order", name)
