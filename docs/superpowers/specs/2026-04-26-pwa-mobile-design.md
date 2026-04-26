# PWA + Mobile Layout Redesign

**Date:** 2026-04-26
**Branch:** feature/visual-fixes

## Goal

Convert the match-tracking web app (`static/index.html`) into an installable Progressive Web App optimised for the Pocophone F2 5G (1080×2400 px, DPR 3 → 360×800 CSS px). The PWA must be installable on Android and the layout must be usable during a live match without unexpected scrolling for the player buttons.

---

## Device target

- **Model:** Xiaomi Pocophone F2 5G (POCO F2 Pro)
- **CSS viewport:** 360×800 px
- **Usable height in PWA standalone mode:** ~760 px (after Android status bar and gesture nav bar)

---

## Layout

### Structure

The page is a single scroll container divided into two logical zones:

```
<div class="above-fold">      height: 100dvh — occupies exactly the visible screen
  match header                date + time of the match
  scoreboard                  team names + large score numbers
  instruction text            "¿Quién ha marcado?" / "¿Quién asistió?"
  player-grid                 flex:1 — fills all remaining space above fold
    col-a                     team A buttons, flex:1 each
    col-b                     team B buttons, flex:1 each
  scroll hint                 "↓ eventos y guardar" subtle indicator
</div>

<div class="below-fold">      normal flow, accessible via scroll
  event log                   full list of goals (no max-height cap)
  save button                 "💾 CONFIRMAR Y GUARDAR PARTIDO"
</div>
```

`100dvh` (dynamic viewport height) accounts for Android browser chrome automatically. The player grid uses `flex:1` inside `above-fold` so buttons always fill the remaining space regardless of whether there are 5, 6, or 7 players per team — no scroll needed to reach them.

### Scoreboard

- Score numbers: `clamp(3rem, 25.5vw, 6rem)` → ~92 px on the Pocophone
- Team name label: `0.75rem`, muted colour (`#cbd5e1`)
- Separator: `–` at `clamp(1.5rem, 7vw, 3rem)`
- Background card with border-radius and `border: 1px solid #334155`

### Player buttons

- `font-size: 1.1rem`, `font-weight: bold`
- `flex: 1` — stretch to fill available height
- Team A: `background: #1e3a8a` (blue)
- Team B: `background: #991b1b` (red)
- "Sin asistencia" button (step 2): `background: #ca8a04` (amber), occupies the slot vacated by the scorer

### Match date header

- Parsed from the `date` URL param (`2026-04-26T20:00`) using `Date` constructor
- Formatted in Spanish: "Sábado 26 de abril · 20:00" using `Intl.DateTimeFormat`

### Step 2 — assist selection

- Shows only the scorer's teammates (4 buttons) + "Sin asist." in the scorer's slot
- Opposing team column shows a "no asiste" placeholder (dashed border, muted text)
- Instruction text turns amber: "⚽ {scorer} marcó — ¿quién asistió?"

### No active match screen

Shown when `initializeApp()` finds neither valid `teamA`/`teamB` URL params nor a `pyball_teams` entry in localStorage. This covers: opening the PWA from the home screen icon, opening a bare `/` URL, and any first visit without a match link. Replaces the interaction panel:

```
⚽  (large emoji)
PyBall
Abre el enlace desde Telegram para empezar un partido.
```

Text centred vertically on `#0f172a` background.

---

## Bug fix

`start_match` use case generates the URL with `nameA` and `nameB` params (the configured team display names, e.g. "Blancos"/"Negros"). The current `index.html` never reads these params — team names always fall back to "A"/"B".

**Fix:** read `nameA` and `nameB` from URL params on first load, display them in the scoreboard, and persist them to localStorage alongside `teamA`, `teamB`, and `meetupDate`.

---

## PWA

### Files added

| File | Purpose |
|------|---------|
| `static/manifest.json` | PWA metadata — name, icons, display mode |
| `static/sw.js` | Service worker — cache-first for static files |
| `static/icons/icon-192.png` | App icon for Android home screen |
| `static/icons/icon-512.png` | App icon for install splash screen |

### manifest.json

```json
{
  "name": "PyBall - Muro de Partido",
  "short_name": "PyBall",
  "start_url": "/",
  "display": "standalone",
  "background_color": "#0f172a",
  "theme_color": "#0f172a",
  "icons": [
    { "src": "/icons/icon-192.png", "sizes": "192x192", "type": "image/png" },
    { "src": "/icons/icon-512.png", "sizes": "512x512", "type": "image/png" }
  ]
}
```

`display: standalone` removes the browser address bar, giving the full ~760 px of usable height.

### Service worker strategy

- **On install:** pre-cache `/`, `/manifest.json`, `/icons/icon-192.png`, `/icons/icon-512.png`
- **On fetch (GET):** cache-first — serve from cache, update cache in background if network available
- **On fetch (POST):** always network — never cache API calls
- **Offline behaviour:** static files load from cache; if the save POST fails due to no connection, an error is shown and the user retries manually (match state is preserved in localStorage)

### Icons

Generated with Python (Pillow): dark background `#0f172a`, football emoji "⚽" centred. Two sizes: 192×192 and 512×512 PNG.

### index.html changes

- Add `<link rel="manifest" href="/manifest.json">` to `<head>`
- Add `<meta name="theme-color" content="#0f172a">` to `<head>`
- Register service worker on load: `navigator.serviceWorker.register('/sw.js')`

---

## .gitignore

Add `.superpowers/` to `.gitignore` (visual companion session files).

---

## Files changed

| File | Change |
|------|--------|
| `static/index.html` | Full rewrite — layout, bug fix, PWA bootstrap |
| `static/manifest.json` | New |
| `static/sw.js` | New |
| `static/icons/icon-192.png` | New (generated) |
| `static/icons/icon-512.png` | New (generated) |
| `.gitignore` | Add `.superpowers/` |
