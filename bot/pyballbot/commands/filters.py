from telegram.ext import filters

from pyballbot.settings import ADMINS_IDS, REGULARS_ID

ADMIN_USERS_FILTER = ~filters.UpdateType.EDITED_MESSAGE & filters.User(ADMINS_IDS)
ALLOWED_CHATS_FILTER = ~filters.UpdateType.EDITED_MESSAGE & filters.Chat(
    {*ADMINS_IDS, REGULARS_ID}
)  # Add all main players ids and admins
BASE_CONVERSATIONS_FILTER = ~filters.COMMAND & ADMIN_USERS_FILTER
