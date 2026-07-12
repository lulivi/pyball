# Application Workflow

🇬🇧 English | 🇪🇸 [Español](workflow.es.md)

This document walks through the full life of a meetup in PyBall: creating it, building
teams, playing, and closing it out — covering both match formats PyBall supports. Every
step can be done from the `/manage` and `/match` web pages; where a Telegram bot command
exists too (only if you're running the `pyball-telegram` topology), it's noted alongside.

## The two match formats

Every meetup uses one of two formats, decided when you generate teams:

- **Classic (2 teams):** one team plays another in a single ~1-hour match. This is the
  traditional format — team A vs. team B, one final score.
- **Triangular (3 teams):** three teams share a session of repeated short matches with
  an automatic "winner stays on" ruleset (details in
  [The triangular ruleset](#the-triangular-ruleset) below). PyBall computes who plays
  next after every result — no one needs to apply the rules by hand.

Nothing else about the workflow changes based on the format — creating the meetup,
managing the roster, and viewing stats work the same way either way.

## 1. Create a meetup

A meetup is one scheduled session: a date, a time, a location, and a roster of players.

- **`/manage`:** paste the callup text (a list of confirmed and reserve players, one per
  line) into the first box and click "🔍 Reconocer jugadores". PyBall fuzzy-matches each
  name against your player database, flags anything ambiguous or unrecognized for you to
  resolve, and lets you exclude reserves. Confirming creates the meetup with that roster.
- **Telegram:** `/meetup_new <fecha> <hora>` creates an empty meetup for that date;
  `/meetup_next` creates one for the next occurrence of the configured default weekday
  and time. Either command posts a callup message to the regulars chat (and a separate
  one to the substitutes chat) with "✔ Unirse" / "✖ Salir" buttons, so players can join
  or leave the roster themselves by tapping a button — no need to add them by hand. The
  regulars message also has "🔀 Crear 2 equipos" / "🔀 Crear 3 equipos" buttons that jump straight to
  [step 3](#3-generate-teams).

## 2. Manage the roster

Before generating teams you can still adjust who's playing. On Telegram, players
usually do this themselves via the "✔ Unirse" / "✖ Salir" buttons from step 1 — these
commands are for an admin adjusting the roster directly:

- **`/manage`:** the roster list lets you remove a player or search-and-add another one.
- **Telegram:** `/meetup_add_player <fecha> <hora> <nombre>` and
  `/meetup_remove_player <fecha> <hora> <nombre>`.

## 3. Generate teams

This is where you choose the match format:

- **`/manage`:** click "⚽ Generar 2 equipos" for a classic match, or "⚽ Generar 3
  equipos" for a triangular. Teams are built with a balanced algorithm (weighted by
  recent results and legacy stats, if configured) or randomly. You can also open
  "✏️ Editar equipos" afterward to manually move, replace, add, or remove players from
  any team — the same panel works for 2 or 3 teams.
- **Telegram:** `/meetup_create_teams <fecha> <hora> [algoritmo] [n_equipos]` — omit
  `n_equipos` for a classic 2-team match, or pass `3` for a triangular. `algoritmo` can
  be `balanceado` (default), or `manual Nombre1,Nombre2;Nombre3,Nombre4` to assign teams
  by hand from Telegram.

As soon as teams are assigned, the first match is ready to track — no separate "start"
step needed.

Goalkeepers and outfield positions (see
[docs/data-directory.md](data-directory.md#dataplayersjson)) are handled automatically
by the balanced algorithm: a player positioned as `portero` is a candidate to become
their team's designated goalkeeper for the session — weighted by a historical
goals-conceded score, so a team is never guaranteed one but the strongest available
keepers tend to end up on different teams. The other three positions
(`defensa`/`centrocampista`/`delantero`) are used as a softer signal to avoid stacking
one team with every player of the same position. You can always see or override which
player is a team's goalkeeper from "✏️ Editar equipos".

## 4. Track the match

Open `/match` on whatever device is scoring the game (phone, tablet). It automatically
shows the currently pending match — no manual setup, no QR code to scan.

- Tap a player to register a goal, optionally picking an assist.
- Tap "Finalizar partido" when the match is over and enter the final score.

**For a classic meetup**, finishing the one match closes the meetup automatically — a
summary is posted (to Telegram, if configured) and the meetup moves to the "Resumen" tab
in `/manage`.

**For a triangular**, finishing a match doesn't close the meetup — PyBall computes the
next pairing per [the ruleset](#the-triangular-ruleset) and `/match` immediately shows
the next round, ready to keep tracking. Repeat step 4 for as many rounds as the session
runs.

## 5. Close a triangular session

Because a triangular has no fixed number of rounds, an admin closes it explicitly when
the session's time is up:

- **`/manage`:** the "🏁 Cerrar triangular" button appears on the Equipos tab whenever
  the active meetup is a triangular (it's hidden for classic matches, which don't need
  it).
- **Telegram:** `/meetup_close_triangular <fecha> <hora>`.

Closing posts a summary covering every round played in the session. A classic meetup
never needs this — it closes itself the moment its one match finishes.

## 6. View stats

- **`/manage` → "Resumen" tab:** the summary of the last finished match, ready to copy
  or share as an image, plus a link to correct a result if it was entered wrong. For a
  classic match, each team's roster shows every player's goals/assists/own-goals,
  followed by a chronological `*GOLES:*` events list. For a triangular, the summary
  opens with each team's roster (with session-wide per-player stats) and its
  win/draw/loss record for the session (e.g. `⚪ Blanco (1V 1E 0D)`), then each round
  shows just its score and its own events list. Telegram's post-match message uses this
  same format.
- **Telegram:** `/meetup_stats [temporada|historico]` posts season or all-time stats as
  an image.

## The triangular ruleset

PyBall applies these rules automatically after every recorded result — you never need to
work out who plays next by hand:

- Each match is timed and refereed off-app (typically 7 minutes) — PyBall only ever
  records a final score, it doesn't track a live countdown.
- Whichever team reaches 2 goals first wins immediately, regardless of the opponent's
  score (2-0 and 2-1 are both immediate wins for the team that got to 2 first).
  Otherwise, whoever is ahead when time is called wins.
- A team can play at most 3 consecutive matches before it's forced to sit out, even if
  it just won.
- **On a win:** the winner stays on to face the team that was waiting — unless the
  winner has now won 3 in a row, in which case the winner sits out instead and the team
  that just lost stays on to face the one waiting.
- **On a draw:** the team with more consecutive matches played sits out; the other team
  stays on. A draw in the very first match of the session (both teams tied) is broken by
  a random pick instead.
- Who sits out for the very first match of the session is also chosen at random.
- The session has no fixed length or match count — it runs until an admin closes it (see
  [step 5](#5-close-a-triangular-session)).

## Related documentation

- [docs/setup.md](setup.md) — installing, configuring, and running PyBall.
- [docs/data-directory.md](data-directory.md) — where meetups, players, and match
  results are stored on disk.
