import asyncio
import os
import shutil
import sys
from io import BytesIO
from pathlib import Path

from telegram import InlineKeyboardButton, InlineKeyboardMarkup, Update
from telegram.ext import ApplicationBuilder, CallbackQueryHandler, CommandHandler, ContextTypes

try:
    BOT_TOKEN = os.environ["FUNNEL_BOT_TOKEN"]
    ADMIN_IDS = os.environ["FUNNEL_ADMIN_IDS"].split(",")
except KeyError:
    print("Both FUNNEL_BOT_TOKEN and FUNNEL_ADMIN_IDS must be in the environment")
    sys.exit(1)

APPS_DIR = Path(os.environ.get("FUNNEL_APPS_DIR", str(Path.home() / "pyball")))
CADDY_DIR = Path(os.environ.get("FUNNEL_CADDY_DIR", str(Path.home() / "caddy")))
TENSORES_WD = APPS_DIR / "tensores"
CUCARACHAS_WD = APPS_DIR / "cucarachas"

# Pre-built Caddyfile variants (copied from the repo on each deploy)
_CADDYFILES = {
    (True, True): CADDY_DIR / "Caddyfile.both",
    (True, False): CADDY_DIR / "Caddyfile.tensores",
    (False, True): CADDY_DIR / "Caddyfile.cucarachas",
    (False, False): CADDY_DIR / "Caddyfile.none",
}
_ACTIVE_CADDYFILE = CADDY_DIR / "Caddyfile"


def main() -> None:
    """Entry point: wires handlers and starts polling."""
    app = ApplicationBuilder().token(BOT_TOKEN).build()
    app.add_handler(CommandHandler("caddy", caddy_command))
    app.add_handler(CallbackQueryHandler(button_handler))

    print("🤖 Caddy Control Bot starting...")
    app.run_polling()


async def caddy_command(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Initializes the panel by reading the state and sending the message."""
    if str(update.effective_user.id) not in ADMIN_IDS:
        return

    status = get_status()
    await update.message.reply_text(
        format_panel_message(status), reply_markup=get_control_keyboard(), parse_mode="Markdown"
    )


async def button_handler(update: Update, context: ContextTypes.DEFAULT_TYPE):
    """Handles state mutations and re-renders the panel."""
    query = update.callback_query

    if str(query.from_user.id) not in ADMIN_IDS:
        await query.answer("⛔ Access denied.", show_alert=True)
        return

    await query.answer()
    command = query.data

    valid_commands = [
        "tensores on", "tensores off", "tensores log",
        "cucarachas on", "cucarachas off", "cucarachas log",
        "reset",
    ]
    if command not in valid_commands:
        return

    if command.endswith("log"):
        app_name = command.split()[0]
        wdir = TENSORES_WD if app_name == "tensores" else CUCARACHAS_WD
        await _send_logs(query, app_name, wdir)
        return

    await query.edit_message_text(f"⏳ Executing: `{command}`...", parse_mode="Markdown")

    current = get_status()
    if command == "reset":
        new_state = {"tensores": False, "cucarachas": False}
    else:
        app_name, action = command.split()
        new_state = {
            "tensores": current["tensores_on"],
            "cucarachas": current["cucarachas_on"],
            app_name: action == "on",
        }

    await _apply_state(new_state["tensores"], new_state["cucarachas"])

    new_status = get_status()
    await query.edit_message_text(
        format_panel_message(new_status),
        reply_markup=get_control_keyboard(),
        parse_mode="Markdown",
    )


def get_status() -> dict:
    """Derive current routing state by inspecting the active Caddyfile."""
    try:
        content = _ACTIVE_CADDYFILE.read_text()
    except FileNotFoundError:
        content = ""
    tensores_on = "@tensores" in content
    cucarachas_on = "@cucarachas" in content
    return {
        "tensores_on": tensores_on,
        "cucarachas_on": cucarachas_on,
        "tensores": "🟢 ON" if tensores_on else "🔴 OFF",
        "cucarachas": "🟢 ON" if cucarachas_on else "🔴 OFF",
    }


def get_control_keyboard() -> InlineKeyboardMarkup:
    """Generates the static inline keyboard for the control panel."""
    keyboard = [
        [
            InlineKeyboardButton("🟢 Tensores ON", callback_data="tensores on"),
            InlineKeyboardButton("🔴 Tensores OFF", callback_data="tensores off"),
            InlineKeyboardButton("📃 Logs", callback_data="tensores log"),
        ],
        [
            InlineKeyboardButton("🟢 Cucarachas ON", callback_data="cucarachas on"),
            InlineKeyboardButton("🔴 Cucarachas OFF", callback_data="cucarachas off"),
            InlineKeyboardButton("📃 Logs", callback_data="cucarachas log"),
        ],
        [InlineKeyboardButton("⚠️ RESET (cortar todo)", callback_data="reset")],
    ]
    return InlineKeyboardMarkup(keyboard)


def format_panel_message(status: dict) -> str:
    """Formats the UI text based on the active Caddyfile state."""
    return (
        "🎛 **Caddy Control Panel**\n\n"
        "📊 **Acceso web actual:**\n"
        f"🔹 Tensores (port 8000): {status['tensores']}\n"
        f"🔹 Cucarachas (port 8001): {status['cucarachas']}\n\n"
        "_Las apps siguen corriendo; solo cambia el routing de Caddy._"
    )


async def _apply_state(tensores: bool, cucarachas: bool) -> None:
    """Copy the right Caddyfile variant and reload Caddy."""
    source = _CADDYFILES[(tensores, cucarachas)]
    shutil.copy(source, _ACTIVE_CADDYFILE)
    process = await asyncio.create_subprocess_exec(
        "docker", "compose", "exec", "-T", "caddy",
        "caddy", "reload", "--config", "/etc/caddy/Caddyfile",
        cwd=CADDY_DIR,
    )
    await process.wait()


async def _send_logs(query, app: str, wdir: Path) -> None:
    """Fetches docker compose logs and sends them as a text file."""
    await query.edit_message_text(f"⏳ Fetching logs for *{app}*…", parse_mode="Markdown")

    process = await asyncio.create_subprocess_exec(
        "docker", "compose", "logs", "--tail", "100",
        stdout=asyncio.subprocess.PIPE,
        stderr=asyncio.subprocess.STDOUT,
        cwd=wdir,
    )
    stdout, _ = await process.communicate()

    await query.message.reply_document(
        document=BytesIO(stdout), filename=f"{app}-logs.txt"
    )

    status = get_status()
    await query.edit_message_text(
        format_panel_message(status),
        reply_markup=get_control_keyboard(),
        parse_mode="Markdown",
    )


if __name__ == "__main__":
    main()
