# PWA + Mobile Layout Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Convert `static/index.html` into an installable PWA optimised for the Pocophone F2 5G, fixing the `nameA`/`nameB` URL param bug in the process.

**Architecture:** The page is split into two zones: `.above-fold` (always `100dvh` tall, contains date header + scoreboard + player buttons filling remaining space with `flex:1`) and `.below-fold` (normal flow, accessible by scrolling, contains event log + save button). A `manifest.json` and `sw.js` alongside two PNG icons enable Android PWA installation with `display: standalone`.

**Tech Stack:** Vanilla HTML/CSS/JS, Web App Manifest, Service Worker API, Python/Pillow (icon generation).

**Spec:** `docs/superpowers/specs/2026-04-26-pwa-mobile-design.md`

---

## File map

| File | Action | Responsibility |
|------|--------|---------------|
| `.gitignore` | Modify | Exclude `.superpowers/` |
| `static/icons/icon-192.png` | Create | PWA home screen icon |
| `static/icons/icon-512.png` | Create | PWA splash screen icon |
| `static/manifest.json` | Create | PWA metadata — name, icons, display mode |
| `static/sw.js` | Create | Service worker — cache-first GET, passthrough POST |
| `static/index.html` | Rewrite | Layout, bug fix, PWA bootstrap |

---

## Task 1: Gitignore + generate icons

**Files:**
- Modify: `.gitignore`
- Create: `static/icons/icon-192.png`
- Create: `static/icons/icon-512.png`

- [ ] **Step 1: Add `.superpowers/` to `.gitignore`**

Open `.gitignore` and add this line after the `# Claude` section at the bottom:

```
.superpowers/
```

- [ ] **Step 2: Generate icons with Python**

Run the following command from the project root. `qrcode[pil]` is already a dependency so Pillow is available:

```bash
uv run python - << 'EOF'
from PIL import Image, ImageDraw
import os

os.makedirs('static/icons', exist_ok=True)

for size in [192, 512]:
    img = Image.new('RGB', (size, size), color=(15, 23, 42))      # #0f172a
    draw = ImageDraw.Draw(img)
    pad = size // 8
    draw.ellipse(
        [pad, pad, size - pad, size - pad],
        fill=(30, 58, 138),               # #1e3a8a
        outline=(96, 165, 250),           # #60a5fa
        width=max(4, size // 32),
    )
    img.save(f'static/icons/icon-{size}.png')
    print(f'Generated static/icons/icon-{size}.png')
EOF
```

Expected output:
```
Generated static/icons/icon-192.png
Generated static/icons/icon-512.png
```

- [ ] **Step 3: Verify files exist**

```bash
ls -lh static/icons/
```

Expected:
```
total ...
-rw-r--r-- 1 ... icon-192.png
-rw-r--r-- 1 ... icon-512.png
```

- [ ] **Step 4: Commit**

```bash
git add .gitignore static/icons/
git commit -m "feat: add PWA icons and ignore .superpowers/"
```

---

## Task 2: Create manifest.json and sw.js

**Files:**
- Create: `static/manifest.json`
- Create: `static/sw.js`

- [ ] **Step 1: Create `static/manifest.json`**

```json
{
    "name": "PyBall - Muro de Partido",
    "short_name": "PyBall",
    "start_url": "/",
    "display": "standalone",
    "background_color": "#0f172a",
    "theme_color": "#0f172a",
    "icons": [
        {
            "src": "/icons/icon-192.png",
            "sizes": "192x192",
            "type": "image/png"
        },
        {
            "src": "/icons/icon-512.png",
            "sizes": "512x512",
            "type": "image/png"
        }
    ]
}
```

- [ ] **Step 2: Create `static/sw.js`**

```javascript
const CACHE_NAME = 'pyball-v1';
const STATIC_ASSETS = ['/', '/manifest.json', '/icons/icon-192.png', '/icons/icon-512.png'];

self.addEventListener('install', event => {
    event.waitUntil(
        caches.open(CACHE_NAME).then(cache => cache.addAll(STATIC_ASSETS))
    );
    self.skipWaiting();
});

self.addEventListener('activate', event => {
    event.waitUntil(
        caches.keys().then(keys =>
            Promise.all(keys.filter(k => k !== CACHE_NAME).map(k => caches.delete(k)))
        )
    );
    self.clients.claim();
});

self.addEventListener('fetch', event => {
    if (event.request.method !== 'GET') return;

    event.respondWith(
        caches.open(CACHE_NAME).then(cache =>
            cache.match(event.request).then(cached => {
                const networkFetch = fetch(event.request)
                    .then(response => {
                        if (response.ok) cache.put(event.request, response.clone());
                        return response;
                    })
                    .catch(() => cached);
                return cached || networkFetch;
            })
        )
    );
});
```

- [ ] **Step 3: Commit**

```bash
git add static/manifest.json static/sw.js
git commit -m "feat: add PWA manifest and service worker"
```

---

## Task 3: Rewrite index.html

**Files:**
- Rewrite: `static/index.html`

This task replaces the entire file. The JS logic (goal registration, localStorage, API call) is preserved; the HTML structure, CSS, and init flow change.

Key changes:
- **Bug fix:** reads `nameA`/`nameB` from URL params (previously ignored)
- **Layout:** `above-fold` (`100dvh`) + `below-fold` (scroll zone)
- **Date header:** formats `2026-04-26T20:00` as "Sábado 26 de abril · 20:00"
- **No-match screen:** replaces "URL inválida" error
- **Success screen:** after save, shows next-steps message
- **PWA bootstrap:** manifest link, theme-color meta, SW registration

- [ ] **Step 1: Replace `static/index.html` with the new version**

```html
<!DOCTYPE html>
<html lang="es">
<head>
    <meta charset="UTF-8">
    <meta name="viewport" content="width=device-width, initial-scale=1.0, viewport-fit=cover">
    <meta name="theme-color" content="#0f172a">
    <meta name="mobile-web-app-capable" content="yes">
    <link rel="manifest" href="/manifest.json">
    <title>PyBall - Muro de Partido</title>
    <style>
        :root { --color-a: #1e3a8a; --color-b: #991b1b; --bg: #0f172a; --text: #f8fafc; }

        *, *::before, *::after { box-sizing: border-box; }

        html, body {
            height: 100%;
            margin: 0;
            background-color: var(--bg);
            color: var(--text);
            font-family: system-ui, sans-serif;
            overflow-y: auto;
        }

        /* ── ABOVE FOLD ──────────────────────────────────── */
        .above-fold {
            height: 100dvh;
            display: flex;
            flex-direction: column;
            padding: 8px 12px 4px;
        }

        .match-date {
            text-align: center;
            font-size: 0.75rem;
            color: #64748b;
            padding: 2px 0 4px;
            flex-shrink: 0;
        }

        .scoreboard {
            background: #1e293b;
            border-radius: 10px;
            border: 1px solid #334155;
            padding: 8px 12px;
            display: flex;
            justify-content: space-evenly;
            align-items: center;
            flex-shrink: 0;
            margin-bottom: 6px;
        }

        .team-score { display: flex; flex-direction: column; align-items: center; flex: 1; }

        .team-name {
            font-size: 0.75rem;
            color: #cbd5e1;
            margin-bottom: 2px;
            white-space: nowrap;
            overflow: hidden;
            text-overflow: ellipsis;
            max-width: 100%;
            text-align: center;
        }

        .score-number {
            font-size: clamp(3rem, 25.5vw, 6rem);
            font-weight: bold;
            line-height: 1;
        }

        .score-a { color: #60a5fa; }
        .score-b { color: #f87171; }

        .score-separator {
            font-size: clamp(1.5rem, 7vw, 3rem);
            font-weight: bold;
            color: #64748b;
            padding: 0 8px;
        }

        .instruction {
            font-size: 0.9rem;
            color: #cbd5e1;
            text-align: center;
            margin: 0 0 6px;
            flex-shrink: 0;
        }

        .instruction.assist { color: #fbbf24; }

        .player-grid { display: flex; gap: 8px; flex: 1; min-height: 0; }

        .team-col { flex: 1; display: flex; flex-direction: column; gap: 6px; }

        .team-col.waiting {
            align-items: center;
            justify-content: center;
            background: rgba(30, 41, 59, 0.4);
            border-radius: 6px;
            border: 1px dashed #334155;
        }

        .waiting-text { font-size: 0.8rem; color: #64748b; text-align: center; padding: 8px; }

        .player-btn {
            flex: 1;
            display: flex;
            align-items: center;
            justify-content: center;
            font-size: 1.1rem;
            font-weight: bold;
            color: white;
            border: none;
            border-radius: 6px;
            cursor: pointer;
            padding: 0;
            min-height: 44px;
        }

        .btn-a { background: var(--color-a); }
        .btn-b { background: var(--color-b); }
        .btn-noassist { background: #ca8a04; }

        .scroll-hint {
            text-align: center;
            font-size: 0.65rem;
            color: #475569;
            padding: 4px 0 2px;
            flex-shrink: 0;
        }

        /* ── BELOW FOLD ──────────────────────────────────── */
        .below-fold { padding: 12px 12px 24px; }

        .events-label {
            font-size: 0.7rem;
            color: #94a3b8;
            text-transform: uppercase;
            letter-spacing: 0.05em;
            margin-bottom: 6px;
        }

        #event-list {
            background: #1e293b;
            border-radius: 8px;
            border: 1px solid #334155;
            padding: 6px 10px;
            margin-bottom: 12px;
        }

        .event-log {
            font-size: 0.85rem;
            color: #f8fafc;
            border-bottom: 1px solid #334155;
            padding: 6px 0;
            display: flex;
            justify-content: space-between;
            align-items: center;
        }

        .event-log:last-child { border-bottom: none; }

        .event-time { font-size: 0.75rem; color: #64748b; flex-shrink: 0; margin-left: 8px; }

        .save-btn {
            display: block;
            width: 100%;
            padding: 14px;
            font-size: 1.1rem;
            font-weight: bold;
            color: white;
            background: #16a34a;
            border: none;
            border-radius: 8px;
            cursor: pointer;
        }

        .save-btn:disabled { background: #475569; cursor: not-allowed; }

        /* ── NO MATCH / SUCCESS ──────────────────────────── */
        .no-match {
            height: 100dvh;
            display: flex;
            flex-direction: column;
            align-items: center;
            justify-content: center;
            text-align: center;
            padding: 32px;
            gap: 12px;
        }

        .no-match-icon { font-size: 3rem; }
        .no-match-title { font-size: 1.4rem; font-weight: bold; }
        .no-match-msg { font-size: 1rem; color: #64748b; line-height: 1.6; }

        .success-banner {
            background: #15803d;
            border-radius: 10px;
            padding: 16px;
            margin-bottom: 8px;
            font-size: 1rem;
            font-weight: bold;
        }
    </style>
</head>
<body>
<div id="app"></div>
<script>
    // ── STATE ──────────────────────────────────────────��──
    let teamA = [], teamB = [];
    let nameA = 'A', nameB = 'B';
    let meetupDate = '';

    let appState = {
        goalsA: 0, goalsB: 0,
        events: [],
        currentStep: 1,
        tempScorer: null, tempScorerTeam: null
    };

    // ── DATE FORMAT ───────────────────────────────────────
    function formatMatchDate(dateStr) {
        if (!dateStr) return '';
        const d = new Date(dateStr);
        if (isNaN(d.getTime())) return '';
        const day = d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
        const time = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
        return day.charAt(0).toUpperCase() + day.slice(1) + ' · ' + time;
    }

    // ── INIT ──────────────────────────────────────────────
    function initializeApp() {
        const savedState = localStorage.getItem('pyball_current_match');
        const savedTeams = localStorage.getItem('pyball_teams');

        if (savedState && savedTeams) {
            appState = JSON.parse(savedState);
            const teams = JSON.parse(savedTeams);
            teamA = teams.teamA;
            teamB = teams.teamB;
            nameA = teams.nameA || 'A';
            nameB = teams.nameB || 'B';
            meetupDate = teams.meetupDate;
            renderApp();
            return;
        }

        const params = new URLSearchParams(window.location.search);
        const teamAParam = params.get('teamA');
        const teamBParam = params.get('teamB');
        meetupDate = params.get('date') || '';
        nameA = params.get('nameA') || 'A';
        nameB = params.get('nameB') || 'B';

        if (!teamAParam || !teamBParam) {
            renderNoMatch();
            return;
        }

        teamA = teamAParam.split(',');
        teamB = teamBParam.split(',');
        localStorage.setItem('pyball_teams', JSON.stringify({ teamA, teamB, nameA, nameB, meetupDate }));
        renderApp();
    }

    // ── GOAL REGISTRATION ─────────────────────────────────
    function selectPlayer(playerName, teamId) {
        if (appState.currentStep === 1) {
            appState.tempScorer = playerName;
            appState.tempScorerTeam = teamId;
            appState.currentStep = 2;
        } else {
            registerGoal(playerName);
            return;
        }
        renderApp();
    }

    function registerGoal(assistantName) {
        appState.events.unshift({
            type: 'gol',
            scorer: appState.tempScorer,
            assistant: assistantName || null,
            team: appState.tempScorerTeam,
            timestamp: new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' })
        });
        if (appState.tempScorerTeam === 'A') appState.goalsA++;
        if (appState.tempScorerTeam === 'B') appState.goalsB++;
        appState.currentStep = 1;
        appState.tempScorer = null;
        appState.tempScorerTeam = null;
        localStorage.setItem('pyball_current_match', JSON.stringify(appState));
        renderApp();
    }

    // ── RENDERING ─────────────────────────────────────────
    function renderNoMatch() {
        document.getElementById('app').innerHTML =
            '<div class="no-match">' +
            '<div class="no-match-icon">⚽</div>' +
            '<div class="no-match-title">PyBall</div>' +
            '<div class="no-match-msg">Abre el enlace desde<br>Telegram para empezar un partido.</div>' +
            '</div>';
    }

    function renderApp() {
        const step = appState.currentStep;
        const scorer = appState.tempScorer;
        const scorerTeam = appState.tempScorerTeam;

        const instructionText = step === 1
            ? '¿Quién ha marcado gol?'
            : '⚽ ' + scorer + ' marcó — ¿quién asistió?';

        let colAHtml = '', colBHtml = '';
        let colAClass = 'team-col', colBClass = 'team-col';

        if (step === 1) {
            colAHtml = teamA.map(p =>
                '<button class="player-btn btn-a" onclick="selectPlayer(\'' + p + '\', \'A\')">' + p + '</button>'
            ).join('');
            colBHtml = teamB.map(p =>
                '<button class="player-btn btn-b" onclick="selectPlayer(\'' + p + '\', \'B\')">' + p + '</button>'
            ).join('');
        } else if (scorerTeam === 'A') {
            colAHtml = teamA.filter(p => p !== scorer).map(p =>
                '<button class="player-btn btn-a" onclick="selectPlayer(\'' + p + '\', \'A\')">' + p + '</button>'
            ).join('') + '<button class="player-btn btn-noassist" onclick="registerGoal(null)">Sin asist.</button>';
            colBHtml = '<div class="waiting-text">Equipo ' + nameB + '<br>no asiste</div>';
            colBClass = 'team-col waiting';
        } else {
            colBHtml = teamB.filter(p => p !== scorer).map(p =>
                '<button class="player-btn btn-b" onclick="selectPlayer(\'' + p + '\', \'B\')">' + p + '</button>'
            ).join('') + '<button class="player-btn btn-noassist" onclick="registerGoal(null)">Sin asist.</button>';
            colAHtml = '<div class="waiting-text">Equipo ' + nameA + '<br>no asiste</div>';
            colAClass = 'team-col waiting';
        }

        const eventsHtml = appState.events.length > 0
            ? appState.events.map(e =>
                '<div class="event-log"><span>⚽ <strong>' + e.scorer + '</strong> ' +
                (e.assistant ? '(Asist: ' + e.assistant + ')' : '(Sin asist.)') +
                '</span><span class="event-time">' + e.timestamp + '</span></div>'
              ).join('')
            : '<div class="event-log" style="color:#64748b;justify-content:center;"><em>No hay eventos aún...</em></div>';

        document.getElementById('app').innerHTML =
            '<div class="above-fold">' +
            '<div class="match-date">' + formatMatchDate(meetupDate) + '</div>' +
            '<div class="scoreboard">' +
            '<div class="team-score"><div class="team-name">' + nameA + '</div>' +
            '<div class="score-number score-a">' + appState.goalsA + '</div></div>' +
            '<div class="score-separator">–</div>' +
            '<div class="team-score"><div class="team-name">' + nameB + '</div>' +
            '<div class="score-number score-b">' + appState.goalsB + '</div></div>' +
            '</div>' +
            '<p class="instruction' + (step === 2 ? ' assist' : '') + '">' + instructionText + '</p>' +
            '<div class="player-grid">' +
            '<div class="' + colAClass + '">' + colAHtml + '</div>' +
            '<div class="' + colBClass + '">' + colBHtml + '</div>' +
            '</div>' +
            '<div class="scroll-hint">↓ eventos y guardar</div>' +
            '</div>' +
            '<div class="below-fold">' +
            '<div class="events-label">Eventos del partido</div>' +
            '<div id="event-list">' + eventsHtml + '</div>' +
            '<button id="save-btn" class="save-btn" onclick="finishMatch()">💾 CONFIRMAR Y GUARDAR PARTIDO</button>' +
            '</div>';
    }

    // ── API ───────────────────────────────────────────────
    async function finishMatch() {
        if (!confirm('¿Seguro que quieres guardar el partido y enviarlo al Bot?')) return;
        const saveBtn = document.getElementById('save-btn');
        saveBtn.disabled = true;
        saveBtn.textContent = 'Enviando datos...';
        try {
            const response = await fetch('/api/match/finish', {
                method: 'POST',
                headers: { 'Content-Type': 'application/json' },
                body: JSON.stringify({
                    meetup_date: meetupDate,
                    events: [...appState.events].reverse(),
                    finalScore: { A: appState.goalsA, B: appState.goalsB }
                })
            });
            if (response.ok) {
                localStorage.removeItem('pyball_current_match');
                localStorage.removeItem('pyball_teams');
                document.getElementById('app').innerHTML =
                    '<div class="no-match">' +
                    '<div class="success-banner">✅ Partido guardado y enviado a Telegram</div>' +
                    '<div class="no-match-icon">⚽</div>' +
                    '<div class="no-match-title">PyBall</div>' +
                    '<div class="no-match-msg">Abre el enlace desde<br>Telegram para el próximo partido.</div>' +
                    '</div>';
            } else {
                const err = await response.json();
                alert('❌ Error del servidor: ' + (err.detail || response.statusText));
                saveBtn.disabled = false;
                saveBtn.textContent = '💾 CONFIRMAR Y GUARDAR PARTIDO';
            }
        } catch {
            alert('❌ Error de red. Revisa la conexión e inténtalo de nuevo.');
            saveBtn.disabled = false;
            saveBtn.textContent = '💾 CONFIRMAR Y GUARDAR PARTIDO';
        }
    }

    // ── SERVICE WORKER ────────────────────────────────────
    if ('serviceWorker' in navigator) {
        navigator.serviceWorker.register('/sw.js').catch(err =>
            console.warn('SW registration failed:', err)
        );
    }

    initializeApp();
</script>
</body>
</html>
```

- [ ] **Step 2: Verify the file looks correct**

```bash
grep -n "nameA\|nameB\|100dvh\|manifest\|serviceWorker" static/index.html
```

Expected output (line numbers will vary):
```
...  <link rel="manifest" href="/manifest.json">
...  height: 100dvh;
...  height: 100dvh;
...  nameA = teams.nameA || 'A';
...  nameB = teams.nameB || 'B';
...  nameA = params.get('nameA') || 'A';
...  nameB = params.get('nameB') || 'B';
...  navigator.serviceWorker.register('/sw.js')
```

- [ ] **Step 3: Start the app and verify manually**

```bash
make up
```

Open `http://localhost:8000` in a browser and verify:

1. **No-match screen** — opening `http://localhost:8000/` (no params) shows the "Abre el enlace desde Telegram" message
2. **Match screen** — open `http://localhost:8000/?teamA=Luis,Marcos,Pablo,Jorge,Rub%C3%A9n&teamB=Carlos,Miguel,Sergio,%C3%81lvaro,David&nameA=Blancos&nameB=Negros&date=2026-04-26T20%3A00`
   - Scoreboard shows "Blancos" and "Negros" (not "A"/"B")
   - Date header shows "Sábado 26 de abril · 20:00"
   - All 10 player buttons visible without scrolling
   - Scrolling down shows the event log and save button
3. **Tap a player** — scoreboard updates, instruction turns amber, 4 teammates + "Sin asist." visible
4. **Tap "Sin asist."** — goal registered, step resets to 1, event appears in log after scroll

- [ ] **Step 4: Check PWA manifest in DevTools**

Open Chrome DevTools → Application → Manifest. Verify:
- Name: "PyBall - Muro de Partido"
- Short name: "PyBall"
- Icons: both 192 and 512 listed
- Display: standalone

- [ ] **Step 5: Commit**

```bash
git add static/index.html
git commit -m "feat: rewrite index.html — PWA bootstrap, mobile layout, fix nameA/nameB params"
```

---

## Self-review

**Spec coverage check:**

| Spec requirement | Task |
|-----------------|------|
| Bug fix: read `nameA`/`nameB` from URL params | Task 3 — `initializeApp()` reads both params |
| Layout: above-fold fills 100dvh | Task 3 — `.above-fold { height: 100dvh }` |
| Player buttons fill remaining space with flex:1 | Task 3 — `.player-btn { flex: 1 }` inside `.team-col { flex: 1 }` |
| Date header in Spanish | Task 3 — `formatMatchDate()` uses `Intl.DateTimeFormat` via `toLocaleDateString` |
| "No match" screen when no params | Task 3 — `renderNoMatch()` |
| Scroll hint indicator | Task 3 — `.scroll-hint` div |
| Event log below fold (no max-height) | Task 3 — `#event-list` has no max-height cap |
| Save button below fold | Task 3 — inside `.below-fold` |
| manifest.json | Task 2 |
| sw.js — cache-first GET, passthrough POST | Task 2 |
| Icons 192 + 512 | Task 1 |
| `.gitignore` add `.superpowers/` | Task 1 |

**Placeholder scan:** None found. All steps contain exact code.

**Type/name consistency:** `nameA`/`nameB` used consistently across `initializeApp`, `renderApp`, `localStorage.setItem`. `appState` shape unchanged from original. `registerGoal(null)` call matches function signature `registerGoal(assistantName)`.
