# siesta

🇬🇧 English | 🇪🇸 [Español](README.es.md)

siesta decides, fairly, who sits out when more players sign up than a meetup can take,
and builds the teams. It is a [bundled plugin](../README.md#bundled-plugins): every PyBall
image includes it, and it runs once you declare it.

## The rule

Players are ordered by how many times they have already sat out, fewest first, with a
random order among equals. The first ones needed sit out and get +1 on the siesta list.

So a regular who already sat out is shielded until everyone else signed up that week has
sat out as many times. When everyone is level it is a plain random draw, but the counts
are never reset. A regular new to the list starts at the current lowest count, so they
don't sit out week after week until they catch up. Only `regular` players are shown on
the list.

## The weekly draw

At the scheduled time (Monday 10:00, Europe/Madrid, by default) siesta draws on the
active meetup, against the meetup's capacity:

- **More signed up than the capacity:** the excess sits out by the rule above, and the
  rest get their teams.
- **Exactly the capacity:** nobody sits out; the teams are made (teams already made by
  hand are kept).
- **Fewer than the capacity:** siesta opens the substitute search. When the search closes
  with the roster full, siesta makes the teams; nobody has to run anything.

Each draw is posted to Telegram: who sits out, the teams and the siesta list.

A meetup is drawn at most once. If PyBall or siesta was down at the scheduled time, the
draw runs when siesta starts again; it never runs twice. On the very first start siesta
only remembers the latest scheduled time, so installing it never draws on the spot: run
`siesta draw` for that. A meetup created after the scheduled time waits for the next one.

## Enable it

Add its table to `config.toml` and restart PyBall:

```toml
[pyball.plugins.siesta]
command = ["siesta", "run"]
scopes = ["players:read", "meetups:read", "meetups:write"]
telegram_bot_token = "123456789:ABCdefGHIjklMNOpqrsTUVwxyz"
telegram_chat_id = -1001234567890
```

| Key | Description | Default |
|---|---|---|
| `command`, `scopes` | As above: how PyBall starts it and what it may do | — |
| `weekday` | Day of the draw, in English: `monday` ... `sunday` | `monday` |
| `time` | Time of the draw, `HH:MM` | `10:00` |
| `timezone` | Time zone of `weekday` and `time`, an IANA name | `Europe/Madrid` |
| `team_algorithm` | How teams are made: `balanceado` or `random` | `balanceado` |
| `telegram_bot_token` | Bot that posts the draw; it may be the same bot as PyBall's | none |
| `telegram_chat_id` | Chat for the draw (negative for groups) | none |
| `telegram_message_thread_id` | Forum topic for the draw (`0` or empty = the main chat) | none |

Without `telegram_bot_token` and `telegram_chat_id`, the message goes to PyBall's log
instead. These keys have no env overrides.

## Commands

Besides `run`, which PyBall starts, siesta has commands to run by hand inside the
container, from the workspace. They talk to the plugin API with the manage token:

```bash
docker compose exec -e PYBALL_API_TOKEN=<manage_token> pyball siesta status
```

(The service is `bot` in a `pyball-telegram` workspace.)

| Command | What it does |
|---|---|
| `status` | Print the siesta list and the last draw. |
| `draw [--dry-run]` | Draw on the active meetup now. `--dry-run` shows the message and changes nothing. |
| `reinstate <player> --instead-of <who>` | Someone dropped out: `<who>` leaves the meetup and the left-out `<player>` takes the spot, getting their +1 back. Teams are rebuilt and the group is told. Omit `--instead-of` if the drop-out already left. |
| `set <player> <n>` | Set a regular's count by hand. |

Names match ignoring case and accents, and a unique start of a name is enough
(`reinstate ivan --instead-of jose m`).

## Its data

siesta keeps its list in `data/plugins/siesta/state.json`: each regular's count, every
draw, and where it left off in the schedule and the event stream. It holds player and
meetup IDs only; names always come from PyBall, so renaming a player changes nothing.
