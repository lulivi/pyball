# telegram

🇬🇧 English | 🇪🇸 [Español](README.es.md)

telegram is PyBall's Telegram bot: it posts each meetup's callup to the regulars chat
with "✔ Unirse" / "✖ Salir" buttons, calls the substitutes when a substitute search
opens, keeps both messages up to date, posts the result and the stats after each match,
and answers the admin commands. It is a [bundled plugin](../README.md#bundled-plugins):
the PyBall image includes it, and it runs once you declare it. Everything it does can
also be done from `/manage` and `/match`.

## What it posts

- **Regulars callup** — when a meetup is created: its date, location and players, with
  the join/leave buttons. It is edited on every change: the teams, each team's latest
  score, and once closed the result summary `/manage` copies. The buttons go away once
  teams exist.
- **Substitutes callup** — when a substitute search opens: the substitutes signed up and
  the buttons, while the search stays open.
- **Cancellation** — a cancelled meetup's messages are marked 🚫 *CANCELADO*.
- **Corrected result** — a result edited after the meetup closed is posted as a new
  message.
- **Stats** — after each match, and after each corrected result, the season stats image
  goes to the stats chat, if one is set.

The buttons work for players linked to their Telegram user with `/player_link`. If the
plugin is stopped, it catches up on what it missed when it runs again; its very first
start acts only on what happens from then on.

## Commands

Each `player_` and `meetup_` command also answers to a short alias: `p_link`, `m_show`, ...

| Command | Who | What it does |
|---|---|---|
| `/help` | Anyone | Lists the commands |
| `/player_link <name>, <telegram_id>` | Admins | Links a Telegram user to a player, matching the name loosely |
| `/player_unlink <name>` | Admins | Removes the player's link |
| `/meetup_show [date]` | Admins | Posts the callup again, of the active meetup or of the one at that date (written in `display_date_format`) |
| `/meetup_stats temporada\|historico` | Admins | Sends the season or all-time stats image to the chat |

## Enable it

Add its table to `config.toml` and restart PyBall:

```toml
[pyball.plugins.telegram]
command = ["telegram"]
scopes = ["players:read", "meetups:read", "meetups:write"]
bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
admins_ids = [123456789]

[pyball.plugins.telegram.regulars.meetups]
chat_id = -1001234567890

[pyball.plugins.telegram.regulars.stats]
chat_id = -1001234567890
message_thread_id = 2

[pyball.plugins.telegram.substitutes.meetups]
chat_id = -1009876543210
```

| Key | Description | Required |
|---|---|---|
| `command`, `scopes` | As above: how PyBall starts it and what it may do | **Yes** |
| `bot_token` | Bot token from [@BotFather](https://t.me/BotFather) | **Yes** |
| `admins_ids` | Telegram user IDs allowed to run admin commands | **Yes** |
| `regulars.meetups.chat_id` | Chat for the regulars callup and corrected results (negative for groups) | **Yes** |
| `regulars.meetups.message_thread_id` | Forum topic for those messages (empty = none) | No |
| `regulars.stats.chat_id` | Chat for the stats after each match (`0` or none = no stats posts) | No |
| `regulars.stats.message_thread_id` | Forum topic for the stats (empty = none) | No |
| `substitutes.meetups.chat_id` | Chat for the substitutes callup (negative for groups) | **Yes** |
| `substitutes.meetups.message_thread_id` | Forum topic for the substitutes callup (empty = none) | No |

To find a chat ID: add the bot to the group, send any message, then check
`https://api.telegram.org/bot<TOKEN>/getUpdates` for the `chat.id` field. Each chat can
be the same group or a different one. These keys have no env overrides. Dates are
written with the club's `display_date_format`, and names sorted by its `locale`.

## Its data

In `data/plugins/telegram/`:

- `messages.json` — which message shows each meetup in each chat, so it can be edited:
  `{"2026-04-15T20:00": {"regular": {"chat_id": -100..., "thread_id": null, "message_id": 4521}}}`.
  A meetup's entries are dropped once it is closed or cancelled.
- `telegram-uuid.json` — the links made with `/player_link`, Telegram user ID to player
  ID: `{"123456789": "11111111-..."}`.
- `last_event_id` — the last event handled, where it resumes after a restart.
