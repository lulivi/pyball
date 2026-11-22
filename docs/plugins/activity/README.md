# activity

🇬🇧 English | 🇪🇸 [Español](README.es.md)

activity posts the meetup activity feed to a Telegram chat: who joins or leaves a
meetup, and each meetup created, closed or cancelled. It is a
[bundled plugin](../README.md#bundled-plugins): every PyBall image includes it, and it
runs once you declare it, with or without the Telegram bot.

## The messages

One message per event, in Spanish:

| Event | Message |
|---|---|
| A player signs up | ✅ **Alta** — `Ana` se apunta como titular a la convocatoria del `2026-11-25 20:00`. |
| A player leaves | ❌ **Baja** — `Ana` se desapunta como suplente de la convocatoria del `2026-11-25 20:00`. |
| A meetup is created | 🆕 **Convocatoria creada** — nueva convocatoria para el `2026-11-25 20:00`. |
| A meetup is closed | 🏁 **Convocatoria cerrada** — la convocatoria del `2026-11-25 20:00` ha finalizado. |
| A meetup is cancelled | 🚫 **Convocatoria cancelada** — se ha cancelado la convocatoria del `2026-11-25 20:00`. |

Every message is posted once and in order. If activity is stopped, or Telegram cannot be
reached, it posts what it missed when it runs again: a message that fails stops the
plugin, PyBall starts it again (see
[How PyBall runs a plugin](../README.md#how-pyball-runs-a-plugin)) and it retries from
that message. Each of those restarts is also an
[alert](../../setup.md#pyballalertstelegram--alerts-all-topologies).

The very first start posts only what happens from then on, not the meetups before it.

## Enable it

Add its table to `config.toml` and restart PyBall:

```toml
[pyball.plugins.activity]
command = ["activity"]
scopes = ["meetups:read"]
telegram_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id = -1001234567890
```

| Key | Description | Default |
|---|---|---|
| `command`, `scopes` | As above: how PyBall starts it and what it may do | — |
| `telegram_bot_token` | Bot that posts the feed; it may be the same bot as PyBall's | none |
| `telegram_chat_id` | Chat for the feed (negative for groups) | none |
| `telegram_message_thread_id` | Forum topic for the feed (`0` or empty = the main chat) | none |
| `date_format` | How the meetup date is written, as `display_date_format` | `%Y-%m-%d %H:%M` |

Without `telegram_bot_token` and `telegram_chat_id`, the feed goes to PyBall's log
instead. These keys have no env overrides.

## Its data

`data/plugins/activity/last_event_id` holds the last event activity posted, where it
resumes after a restart.
