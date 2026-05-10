"""Reaction helper for bot command handlers."""
import telegram
from telegram import Bot, Message, ReactionTypeEmoji


async def react_ok(bot: Bot, message: Message) -> None:
    """React ✅ to message; fall back to reply_text if reactions are unsupported."""
    try:
        await bot.set_message_reaction(
            chat_id=message.chat_id,
            message_id=message.message_id,
            reaction=[ReactionTypeEmoji("✅")],
        )
    except telegram.error.TelegramError:
        await message.reply_text("✅")
