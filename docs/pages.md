# Page Reference

🇬🇧 English | 🇪🇸 [Español](pages.es.md)

This document is a structural tour of PyBall's two web pages — what tabs or screens
each one has and what each shows. It doesn't repeat the step-by-step behavior already
covered in [docs/workflow.md](workflow.md), or how each page is protected, covered in
[docs/setup.md's Access tokens section](setup.md#6-access-tokens) — it links to both
instead.

## `/manage`

The admin page. Three tabs:

### Jugadores

The player database: search, add, edit, or remove a player.

### Convocatoria actual

The active meetup, if one exists: pasting and recognizing a callup
([step 1](workflow.md#1-create-a-meetup)), managing the roster
([step 2](workflow.md#2-manage-the-roster)), including its capacity and the substitute
search, generating or editing teams
([step 3](workflow.md#3-generate-teams)), destroying teams,
canceling the match, copying the match link, and — for a triangular —
closing the session ([step 5](workflow.md#5-close-a-triangular-session)). Empty if no
meetup is active.

### Convocatorias

History of every closed meetup, newest first, each expandable into its summary — see
[step 6](workflow.md#6-view-stats).

## `/match`

The scoreboard page, opened on whichever device is tracking the live match.

After 20 seconds without a touch the page switches to an idle screen: the current
minute of the hour in big digits (e.g. `47'`), the countdown to the next goalkeeper
change if the rotation timer is running, and the score in each team's colour. Tap
anywhere to go back. It never shows while editing a past result.

Below the match date, three tabs:

### Tiempo

A rotation countdown for peñas that swap goalkeepers on a timer. Pick a shift length
(1–15 minutes, default 6) and tap "Iniciar cronómetro"; it counts down, plays a sound
and flashes the screen at zero, then restarts on its own for the next shift — no need to
touch it between rotations. A small 🔊 button next to "Iniciar cronómetro" and
"Activar aviso" plays that alarm's sound so you can check the volume before starting;
it disappears once they are active. The first tap is also what unlocks sound on mobile,
and the timer keeps the screen awake while it runs. It is device-local (not shared with
other `/match` devices) and survives a page reload. Hidden while editing a past result.
While it runs, a small countdown pill sits next to the match date on the other tabs —
tap it to jump back here. A page reload re-locks audio (a browser rule); the pill then
shows 🔇 until any tap re-enables the sound.

### Jugadores

The scoreboard plus the tap-to-score grid: tap a player to register a goal, optionally
picking an assist — see [step 4](workflow.md#4-track-the-match).

### Resultados

The chronological event log for the current match (edit or delete a previously recorded goal here),
and the "Finalizar partido" action to close out the match with a final score.

## Related documentation

- [docs/workflow.md](workflow.md) — the step-by-step behavior behind these pages.
- [docs/setup.md](setup.md) — access tokens and how each page is protected.
