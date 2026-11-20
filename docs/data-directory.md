# Data Directory

🇬🇧 English | 🇪🇸 [Español](data-directory.es.md)

This document describes the workspace layout `--bootstrap` creates and the JSON file
formats PyBall reads and writes. Useful if you want to back up your data, inspect it
directly, or migrate it somewhere else.

## Workspace layout

After running `--bootstrap` (see [docs/setup.md](setup.md)), your workspace directory
looks like this:

```
pyball/
├── config.toml       # your settings
├── compose.yaml       # docker compose service definition
├── .env               # UID/GID/PORT/TAG
├── README.md          # short pointer back to docs/setup.md
├── data/
│   ├── players.json   # every player, regardless of meetup
│   ├── legacy_stats.json   # optional — historical assists imported from before PyBall
│   ├── meetups/
│   │   ├── 2026-04-15T20:00.json
│   │   ├── 2026-04-22T20:00.json
│   │   └── ...         # one file per meetup, named after its date/time
│   ├── signup/
│   │   └── codes.json   # only when enable_web_signup is set — see below
│   └── bot/
│       └── messages.json   # pyball-telegram only — see below
└── logs/
    └── ...             # application log files
```

Every file is plain JSON, written with 2-space indentation, safe to read (or even hand-
edit, carefully) with any text editor.

## `data/players.json`

One shared file listing every player ever created, independent of any meetup:

```json
{
  "players": [
    { "id": "11111111-1111-4111-8111-111111111111", "name": "Juan Pérez", "group": "regular", "position": "defensa" },
    { "id": "22222222-2222-4222-8222-222222222222", "name": "Manu García", "group": "substitute", "position": null }
  ]
}
```

- `id` — a UUID, generated when the player is created.
- `name` — display name, used everywhere (UI, Telegram messages, callup fuzzy-matching).
- `group` — `"regular"` or `"substitute"`, the default group used when parsing a callup.
- `position` — `"portero"`, `"defensa"`, `"centrocampista"`, `"delantero"`, or `null` if
  unset. A loose, typical position, not a rigid assignment — used only as a signal by
  the balanced team-generation algorithm (see
  [docs/workflow.md](workflow.md#3-generate-teams)).

## `data/meetups/<date>.json`

One file per meetup, named after its date and time in `YYYY-MM-DDTHH:MM` format (colons
in the time are kept as-is, this is a filename, not a URL). Its shape depends on whether
teams have been assigned yet, and whether it's a classic or triangular meetup — but it's
always the same schema, just with more populated fields as the meetup progresses.

A finished **triangular** (3-team) meetup, after 3 rounds and closed:

```json
{
  "id": "a1b2c3d4-0000-4000-8000-000000000001",
  "date": "2026-07-08T20:00:00",
  "location": "Parque Central",
  "players": ["11111111-...", "22222222-...", "..."],
  "teams": [
    { "name": "A", "players": ["11111111-...", "22222222-...", "33333333-..."], "goalkeeper": "11111111-..." },
    { "name": "B", "players": ["44444444-...", "55555555-...", "66666666-..."], "goalkeeper": null },
    { "name": "C", "players": ["77777777-...", "88888888-...", "99999999-..."], "goalkeeper": null }
  ],
  "matches": [
    {
      "teams_playing": ["A", "B"],
      "result": {
        "score_a": 2,
        "score_b": 0,
        "events": [
          {
            "scorer_id": "11111111-...",
            "assistant_id": "22222222-...",
            "team": "A",
            "timestamp": "20:03:00",
            "is_own_goal": false
          }
        ]
      }
    },
    { "teams_playing": ["A", "C"], "result": { "score_a": 1, "score_b": 1, "events": [] } },
    { "teams_playing": ["C", "B"], "result": { "score_a": 2, "score_b": 1, "events": [] } }
  ],
  "closed": true,
  "capacity": 10,
  "substitute_search": false
}
```

Field notes:

- `players` — everyone convoked to this meetup, regardless of whether they ended up on
  a team (a substitute who was never assigned to a team still appears here).
- `teams` — `null` until teams are generated. A list of 2 (classic) or 3 (triangular)
  named teams. Names are always `"A"`, `"B"`, and (for triangulars) `"C"` — these are
  positional labels, not the display color names configured in `team_colors`. Each
  team's `goalkeeper` is the id of that team's designated goalkeeper for the whole
  session, or `null` if none was set — see
  [docs/workflow.md](workflow.md#3-generate-teams).
- `matches` — starts as `[]`. Each entry is one played (or in-progress) match between
  exactly 2 of the meetup's teams. `teams_playing` references team names, not indices,
  so reordering `teams` never breaks a match's team references. `result` is `null` while
  the match is still in progress (no result recorded yet); a meetup always has at most
  one match with `result: null` at a time — the one currently shown on `/match`.
  - A **classic** meetup only ever has one entry in `matches`.
  - A **triangular** meetup accumulates one entry per round played, in order, and the
    pair of teams in `teams_playing` rotates automatically per the ruleset described in
    [docs/workflow.md](workflow.md#the-triangular-ruleset).
- `events` — one entry per goal, in the order they were scored. `team` is `"A"` or
  `"B"` **relative to this match's `teams_playing`**, not to the meetup's overall
  `teams` list (this matters for a triangular, where a team playing as the "B" side in
  one round might play as "A" in the next).
- `closed` — `true` once the meetup is fully done. A classic meetup closes itself the
  moment its one match gets a result; a triangular stays open across multiple rounds
  until explicitly closed (see
  [docs/workflow.md](workflow.md#5-close-a-triangular-session)).
- `capacity` — how many players this meetup plays with. A new meetup takes
  `meetup_capacity` from `config.toml`; a file without the field loads with it too.
- `substitute_search` — `true` while a substitute search is open (see
  [docs/workflow.md](workflow.md#2-manage-the-roster)); a file without the field loads
  with it closed.

## `data/legacy_stats.json` (optional)

Only needed if your group tracked assists before adopting PyBall and wants that history
folded into season stats. Missing entirely is fine — PyBall treats that the same as an
empty file:

```json
{
  "players": {
    "11111111-1111-4111-8111-111111111111": {
      "assists_by_match": [
        { "date": "2026-04-15T20:00:00", "count": 2 }
      ]
    }
  }
}
```

## Web signup is opt-in via `enable_web_signup`

The `data/signup/` directory below only exists when `enable_web_signup` is set to
`true` in `config.toml`. With it left at the default `false`, or on `pyball-telegram`,
nothing reads or writes it.

### `data/signup/codes.json`

One entry per player who's been issued a personal signup code, keyed by player id:

```json
{
  "11111111-1111-4111-8111-111111111111": {
    "salt": "3f9c2a1b8e7d4f605a3c9b8e1d7f6042",
    "hash": "8e1a9c3f7b2d6e405c1a8f9b3d7e6042c1a8f9b3d7e6042c1a8f9b3d7e60428e"
  }
}
```

- `salt` — random per-player bytes (hex), generated fresh every time a code is set.
- `hash` — the PBKDF2-HMAC-SHA256 hash of the code with that salt (200,000 iterations).

Codes are never stored in plaintext, so an existing code can never be recovered from
this file — only regenerated (the "Regenerar código" button on a player's row in
`/manage`, or automatically the first time a player is created while `enable_web_signup`
is set; see [docs/workflow.md](workflow.md)). This file is created automatically the
first time it's needed and is safe to delete: doing so just invalidates every player's
existing code, forcing everyone to be issued a new one.

## Telegram config is bot-only

The `[pyball.telegram]` section in `config.toml`, and the `data/bot/` directory below,
only exist for the `pyball-telegram` topology. Running `pyball` (with or without
`enable_web_signup`) never reads or writes either of them — that deployment has no
`data/bot/` directory at all.

### `data/bot/messages.json`

Tracks which Telegram message (in the regulars/substitutes chats) corresponds to each
meetup's callup, so PyBall can edit or delete it later (e.g. when the roster changes, or
when the meetup closes):

```json
{
  "2026-04-15T20:00": {
    "regular": { "chat_id": -1000000000000, "thread_id": null, "message_id": 4821 },
    "substitute": { "chat_id": -1000000000001, "thread_id": null, "message_id": 512 }
  }
}
```

The key is the meetup's date/time (`YYYY-MM-DDTHH:MM`, matching the meetup filename
without the `.json` extension). `thread_id` is `null` unless the chat uses forum topics
(see `telegram.regulars.meetups.message_thread_id` in [docs/setup.md](setup.md); the
`substitute` entry likewise picks up `telegram.substitutes.meetups.message_thread_id`).

## Related documentation

- [docs/setup.md](setup.md) — installing, configuring, and running PyBall.
- [docs/workflow.md](workflow.md) — the meetup lifecycle these files record.
