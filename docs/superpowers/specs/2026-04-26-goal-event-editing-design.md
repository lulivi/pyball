# Goal Event Editing — Design Spec

**Date:** 2026-04-26
**Scope:** `static/index.html` only — no backend or domain changes

## Summary

Two UX improvements to the in-progress match tracking UI:

1. A **Cancel button** during goal registration so accidental scorer taps can be undone.
2. **Inline editing** of goal events in the event list: scorer and assistant are tappable chips that open a compact player picker; a delete button removes the goal entirely.

Both features operate exclusively on `appState` (in-memory + localStorage) before the match is saved. Once `POST /api/match/finish` is called, the result is immutable.

---

## State model

Add one field to `appState`:

```js
editingEvent: null  // or { eventIndex: number, field: 'scorer' | 'assistant' }
```

The existing event shape `{ scorer, assistant, team, timestamp }` is unchanged.

---

## Cancel button

- Rendered in **step 2** (assistant selection), above the player grid.
- Label: `← Cancelar`
- Action: sets `currentStep = 1`, `tempScorer = null`, `tempScorerTeam = null`, calls `renderApp()`.
- No confirmation needed — nothing has been written yet at this point.

---

## Inline event editing

### Rendering

Each event row in the event list renders:

- `⚽` icon
- Scorer as a `<button class="player-chip">Name ▼</button>`
- Assistant as a `<button class="player-chip">Name ▼</button>` (or "Sin asist." chip)
- Timestamp (right-aligned)
- 🗑 delete button

### Picker behaviour

- Tapping a chip sets `editingEvent = { eventIndex: i, field: 'scorer'|'assistant' }` and re-renders.
- The open picker renders as a `<div>` directly below the chip.
  - **Scorer picker**: shows all players from the event's team (`event.team`), consistent with the goal being assigned to that team.
  - **Assistant picker**: shows all players from the same team minus the current scorer, plus "Sin asistente".
- Selecting a player updates `appState.events[i][field]`, sets `editingEvent = null`, persists to localStorage, and re-renders.
- Only one picker can be open at a time — opening a new one closes the previous.
- A `document` click listener closes any open picker when the user taps outside it.

### Delete behaviour

- `deleteEvent(i)` splices the event from `appState.events`.
- `goalsA` and `goalsB` are recomputed from scratch: `events.filter(e => e.team === 'A').length` (and `'B'`), preventing any counter drift.
- State is persisted to localStorage and the UI re-renders.

---

## Edge cases

| Case | Handling |
|---|---|
| Scorer picker | Shows only players from the event's team (team field unchanged) |
| Scorer is from team A → picker for assistant | Shows team A players (minus scorer) + "Sin asistente" |
| Many players → picker overflow | `max-height` + `overflow-y: auto` on dropdown |
| Tap outside open picker | `document` click listener closes `editingEvent` |
| All goals deleted | `goalsA = goalsB = 0`, event list shows empty state |

---

## Out of scope

- Editing the **team** field of an existing event (changing which team a goal belongs to is not supported).
- Editing events after the match has been saved (`POST /api/match/finish` already called).
- Any backend or domain layer changes.
