# Page Reference

🇬🇧 English | 🇪🇸 [Español](pages.es.md)

This document is a structural tour of PyBall's three web pages — what tabs or screens
each one has and what each shows. It doesn't repeat the step-by-step behavior already
covered in [docs/workflow.md](workflow.md), or how each page is protected, covered in
[docs/setup.md's Access tokens section](setup.md#6-access-tokens) — it links to both
instead.

## `/manage`

The admin page. Three tabs:

### Jugadores

The player database: search, add, edit, or remove a player, and — if `enable_web_signup`
is set in `config.toml` — generate or regenerate a player's personal signup code (see
[Self-service signup via `/signup`](workflow.md#self-service-signup-via-signup)).

### Convocatoria actual

The active meetup, if one exists: pasting and recognizing a callup
([step 1](workflow.md#1-create-a-meetup)), managing the roster
([step 2](workflow.md#2-manage-the-roster)), generating or editing teams
([step 3](workflow.md#3-generate-teams)), starting the match or destroying teams,
canceling the match, copying the signup and match links, and — for a triangular —
closing the session ([step 5](workflow.md#5-close-a-triangular-session)). Empty if no
meetup is active.

### Convocatorias

History of every closed meetup, newest first, each expandable into its summary — see
[step 6](workflow.md#6-view-stats).

## `/match`

The scoreboard page, opened on whichever device is tracking the live match. Below the
match date, two tabs:

### Jugadores

The scoreboard plus the tap-to-score grid: tap a player to register a goal, optionally
picking an assist — see [step 4](workflow.md#4-track-the-match).

### Eventos y Resultados

The chronological event log for the current match (edit or delete a previously recorded goal here),
and the "Finalizar partido" action to close out the match with a final score.

## `/signup`

The self-service page for players, only reachable when `enable_web_signup` is set in
`config.toml` — see
[Self-service signup via `/signup`](workflow.md#self-service-signup-via-signup) for the
full behavior. Two states rather than tabs:

### Code entry

The initial screen: just a field for the player's personal code.

### Logged in

Once a valid code is entered, either:
- the open-roster view, with an "Apuntarme" / "Salir" button, while signup is still
  open; or
- the read-only teams view, with the player's own name highlighted, once teams exist.

"No soy yo" is always available to release the device for the next player, without
losing the page's own access token.

## Related documentation

- [docs/workflow.md](workflow.md) — the step-by-step behavior behind these pages.
- [docs/setup.md](setup.md) — access tokens and how each page is protected.
