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

"""Telegram bot that switches each club's Caddy routing on or off.

A club is a directory under ``APPS_DIR``. It is routed while ``enabled/<club>``
exists in ``CADDY_DIR``, holding ``import club <club> <port>`` with the ``PORT``
of the club's ``.env``. The apps keep running: only the routing changes.
"""

from __future__ import annotations

import asyncio
import html
import os
import sys
from io import BytesIO
from pathlib import Path

from telegram import CallbackQuery, InlineKeyboardButton, InlineKeyboardMarkup, Message, Update
from telegram.constants import ParseMode
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

APPS_DIR = Path(os.environ.get("FUNNEL_APPS_DIR", str(Path.home() / "pyball")))
CADDY_DIR = Path(os.environ.get("FUNNEL_CADDY_DIR", str(Path.home() / "caddy")))


def main() -> None:
    """Read the bot settings from the environment, wire the handlers and start polling."""
    try:
        token = os.environ["FUNNEL_BOT_TOKEN"]
        admin_ids = os.environ["FUNNEL_ADMIN_IDS"].split(",")
    except KeyError:
        print("Both FUNNEL_BOT_TOKEN and FUNNEL_ADMIN_IDS must be in the environment")
        sys.exit(1)

    app = ApplicationBuilder().token(token).build()
    app.bot_data["admin_ids"] = admin_ids
    app.add_handler(CommandHandler("caddy", caddy_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Caddy Control Bot starting...")
    app.run_polling()


async def caddy_command(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Send the control panel to an admin."""
    if update.message is None or not _is_admin(update, context):
        return
    await update.message.reply_text(
        format_panel_message(), reply_markup=get_control_keyboard(), parse_mode=ParseMode.HTML
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE) -> None:
    """Run a panel button's command and re-render the panel."""
    query = update.callback_query
    if query is None:
        return
    if not _is_admin(update, context):
        await query.answer("⛔ Acceso denegado.", show_alert=True)
        return
    await query.answer()

    command = parse_command(query.data or "")
    if command is None:
        return
    club, action = command

    if action == "log":
        await _send_logs(query, club)
        return

    await query.edit_message_text(
        f"⏳ Ejecutando: <code>{html.escape(query.data or '')}</code>…",
        parse_mode=ParseMode.HTML,
    )
    if action == "reset":
        error = await reset()
    elif action == "on":
        error = await switch_on(club)
    else:
        error = await switch_off(club)

    text = format_panel_message()
    if error:
        text = f"⚠️ {html.escape(error)}\n\n{text}"
    await query.edit_message_text(
        text, reply_markup=get_control_keyboard(), parse_mode=ParseMode.HTML
    )


def parse_command(data: str) -> tuple[str, str] | None:
    """Return ``(club, action)`` for a button's callback data, or None if it is not valid.

    ``reset`` gives an empty club; every other command names a club that exists.
    """
    if data == "reset":
        return "", "reset"
    club, _, action = data.rpartition(" ")
    if action not in ("on", "off", "log") or club not in list_clubs():
        return None
    return club, action


def list_clubs() -> list[str]:
    """Return the club names: the non-hidden directories under ``APPS_DIR``, sorted."""
    return sorted(
        path.name for path in APPS_DIR.iterdir() if path.is_dir() and not path.name.startswith(".")
    )


def read_port(club: str) -> str | None:
    """Return the ``PORT`` in the club's ``.env``, or None if it is missing or not a number."""
    try:
        lines = (APPS_DIR / club / ".env").read_text().splitlines()
    except FileNotFoundError:
        return None
    for line in lines:
        key, _, value = line.partition("=")
        if key.strip() == "PORT":
            value = value.strip()
            return value if value.isdigit() else None
    return None


def enabled_clubs() -> set[str]:
    """Return the clubs currently routed by Caddy."""
    enabled = _enabled_dir()
    if not enabled.is_dir():
        return set()
    return {path.name for path in enabled.iterdir() if path.is_file()}


async def switch_on(club: str) -> str | None:
    """Route the club to its port; return an error message on failure."""
    port = read_port(club)
    if port is None:
        return f"{club} no tiene un PORT válido en su .env."
    return await _apply({_enabled_dir() / club: f"import club {club} {port}\n"})


async def switch_off(club: str) -> str | None:
    """Stop routing the club; return an error message on failure."""
    return await _apply({_enabled_dir() / club: None})


async def reset() -> str | None:
    """Stop routing every club, including leftovers of removed clubs."""
    return await _apply({_enabled_dir() / club: None for club in enabled_clubs()})


def get_control_keyboard() -> InlineKeyboardMarkup:
    """Build one row of buttons per club, then the reset button."""
    keyboard = [
        [
            InlineKeyboardButton(f"🟢 {club.capitalize()} ON", callback_data=f"{club} on"),
            InlineKeyboardButton(f"🔴 {club.capitalize()} OFF", callback_data=f"{club} off"),
            InlineKeyboardButton("📃 Logs", callback_data=f"{club} log"),
        ]
        for club in list_clubs()
    ]
    keyboard.append([InlineKeyboardButton("⚠️ RESET (cortar todo)", callback_data="reset")])
    return InlineKeyboardMarkup(keyboard)


def format_panel_message() -> str:
    """Describe each club's port and routing state, as Telegram HTML."""
    enabled = enabled_clubs()
    lines = [
        f"🔹 {html.escape(club.capitalize())} (port {read_port(club) or '?'}): "
        f"{'🟢 ON' if club in enabled else '🔴 OFF'}"
        for club in list_clubs()
    ]
    clubs = "\n".join(lines)
    return (
        "🎛 <b>Panel de control de Caddy</b>\n\n"
        f"📊 <b>Acceso web actual:</b>\n{clubs}\n\n"
        "<i>Las apps siguen corriendo; solo cambia el routing de Caddy.</i>"
    )


def _is_admin(update: Update, context: ContextTypes.DEFAULT_TYPE) -> bool:
    user = update.effective_user
    return user is not None and str(user.id) in context.bot_data["admin_ids"]


def _enabled_dir() -> Path:
    return CADDY_DIR / "enabled"


async def _apply(changes: dict[Path, str | None]) -> str | None:
    """Write each file's new content (None deletes it) and reload Caddy.

    If the reload fails, every file gets its previous content back, so the files
    keep describing what Caddy serves. Returns an error message on failure.
    """
    previous = {path: _read(path) for path in changes}
    for path, content in changes.items():
        _write(path, content)
    if await _reload_caddy():
        return None
    for path, content in previous.items():
        _write(path, content)
    return "Caddy no pudo recargar la configuración; no se ha cambiado nada."


def _read(path: Path) -> str | None:
    try:
        return path.read_text()
    except FileNotFoundError:
        return None


def _write(path: Path, content: str | None) -> None:
    if content is None:
        path.unlink(missing_ok=True)
        return
    path.parent.mkdir(exist_ok=True)
    path.write_text(content)


async def _reload_caddy() -> bool:
    process = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "exec",
        "-T",
        "caddy",
        "caddy",
        "reload",
        "--config",
        "/etc/caddy/Caddyfile",
        cwd=CADDY_DIR,
    )
    return await process.wait() == 0


async def _send_logs(query: CallbackQuery, club: str) -> None:
    """Send the club's last 100 log lines as a text file."""
    await query.edit_message_text(
        f"⏳ Obteniendo los logs de <b>{html.escape(club)}</b>…", parse_mode=ParseMode.HTML
    )
    process = await asyncio.create_subprocess_exec(
        "docker",
        "compose",
        "logs",
        "--tail",
        "100",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=APPS_DIR / club,
    )
    stdout, _ = await process.communicate()
    if isinstance(query.message, Message):
        await query.message.reply_document(document=BytesIO(stdout), filename=f"{club}-logs.txt")
    await query.edit_message_text(
        format_panel_message(), reply_markup=get_control_keyboard(), parse_mode=ParseMode.HTML
    )


if __name__ == "__main__":
    main()
