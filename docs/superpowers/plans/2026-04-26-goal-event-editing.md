# Goal Event Editing Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** Add a cancel button during goal registration and inline chip-based editing (scorer / assistant) plus a delete button to the in-progress match tracking PWA.

**Architecture:** All changes are confined to `static/index.html`. New JS functions extend the existing render-on-state-change pattern (`appState` → `renderApp()`). No backend, domain, or test-suite changes.

**Tech Stack:** Vanilla JS, CSS, localStorage, HTML — no frameworks, no automated frontend tests. Verification is manual.

---

## File map

| File | Change |
|---|---|
| `static/index.html` | Add CSS, extend `appState`, add JS functions, update `renderApp()` |

---

### Task 1: Cancel button during goal registration

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add `.cancel-btn` CSS**

  Inside the `<style>` block, after the `.btn-noassist` rule, add:

  ```css
  .cancel-btn {
      display: block; width: 100%;
      padding: 9px; font-size: 0.85rem; font-weight: 600;
      color: #94a3b8; background: transparent;
      border: 1px solid #334155; border-radius: 6px;
      cursor: pointer; text-align: center; margin-bottom: 6px;
  }
  ```

- [ ] **Step 2: Add `editingEvent` to the initial `appState` declaration**

  Change:

  ```js
  let appState = {
      goalsA: 0, goalsB: 0,
      events: [],
      currentStep: 1,
      tempScorer: null, tempScorerTeam: null
  };
  ```

  To:

  ```js
  let appState = {
      goalsA: 0, goalsB: 0,
      events: [],
      currentStep: 1,
      tempScorer: null, tempScorerTeam: null,
      editingEvent: null
  };
  ```

- [ ] **Step 3: Reset `editingEvent` when restoring state from localStorage**

  In `initializeApp()`, after `appState = JSON.parse(savedState);`, add:

  ```js
  appState.editingEvent = null;
  ```

  The full block becomes:

  ```js
  if (savedState && savedTeams) {
      appState = JSON.parse(savedState);
      appState.editingEvent = null;
      const teams = JSON.parse(savedTeams);
      teamA = teams.teamA;
      teamB = teams.teamB;
      nameA = teams.nameA || 'A';
      nameB = teams.nameB || 'B';
      meetupDate = teams.meetupDate;
      renderApp();
      return;
  }
  ```

- [ ] **Step 4: Add `cancelGoal()` function**

  In the `// ── GOAL REGISTRATION` section, after `registerGoal`, add:

  ```js
  function cancelGoal() {
      appState.currentStep = 1;
      appState.tempScorer = null;
      appState.tempScorerTeam = null;
      renderApp();
  }
  ```

- [ ] **Step 5: Render the cancel button in step 2**

  In `renderApp()`, find the line that builds the `<p class="instruction...">` element and the `<div class="player-grid">` that follows it. Insert the cancel button between them:

  ```js
  '<p class="instruction' + (step === 2 ? ' assist' : '') + '">' + instructionText + '</p>' +
  (step === 2 ? '<button class="cancel-btn" onclick="cancelGoal()">← Cancelar</button>' : '') +
  '<div class="player-grid">' +
  ```

- [ ] **Step 6: Manual test**

  Open the app with valid `?teamA=...&teamB=...&date=...&nameA=...&nameB=...` params.
  - Tap any player in step 1 → you enter step 2 (assistant screen).
  - Verify `← Cancelar` button appears above the player grid.
  - Tap `← Cancelar` → verify you return to step 1 (goleador screen), score unchanged.
  - Register a goal normally → verify cancel does NOT appear in step 1.

- [ ] **Step 7: Commit**

  ```bash
  git add static/index.html
  git commit -m "feat: add cancel button to goal registration step 2"
  ```

---

### Task 2: Event list chip rendering and delete button

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add CSS for chips, delete button, and editing row state**

  In the `<style>` block, after `.event-time`, add:

  ```css
  .player-chip {
      display: inline-flex; align-items: center; gap: 3px;
      background: #0f172a; border: 1px solid #475569;
      border-radius: 4px; padding: 2px 7px;
      font-size: 0.78rem; font-weight: 600; cursor: pointer;
      color: #f8fafc; white-space: nowrap; vertical-align: middle;
      line-height: 1.4;
  }
  .player-chip.active { border-color: #60a5fa; background: #1e3a8a; }
  .player-chip .chevron { font-size: 0.6rem; color: #94a3b8; }

  .delete-btn {
      background: transparent; border: none; color: #ef4444;
      font-size: 0.9rem; cursor: pointer; padding: 2px 4px; flex-shrink: 0;
  }

  .event-log.editing { flex-wrap: wrap; align-items: flex-start; }
  ```

- [ ] **Step 2: Add `deleteEvent(i)` function**

  In the `// ── GOAL REGISTRATION` section, after `cancelGoal()`, add:

  ```js
  function deleteEvent(i) {
      appState.events.splice(i, 1);
      appState.goalsA = appState.events.filter(function(e) { return e.team === 'A'; }).length;
      appState.goalsB = appState.events.filter(function(e) { return e.team === 'B'; }).length;
      appState.editingEvent = null;
      localStorage.setItem('pyball_current_match', JSON.stringify(appState));
      renderApp();
  }
  ```

- [ ] **Step 3: Add `renderEventRow(e, i)` helper function**

  Before `renderApp()`, add:

  ```js
  function renderEventRow(e, i) {
      var scorerOpen = appState.editingEvent !== null &&
                       appState.editingEvent.eventIndex === i &&
                       appState.editingEvent.field === 'scorer';
      var assistOpen = appState.editingEvent !== null &&
                       appState.editingEvent.eventIndex === i &&
                       appState.editingEvent.field === 'assistant';

      var scorerChip =
          '<button class="player-chip' + (scorerOpen ? ' active' : '') +
          '" onclick="event.stopPropagation();togglePicker(' + i + ',\'scorer\')">' +
          e.scorer + ' <span class="chevron">' + (scorerOpen ? '▲' : '▼') + '</span></button>';

      var assistLabel = e.assistant ? e.assistant : 'Sin asist.';
      var assistChip =
          '<button class="player-chip' + (assistOpen ? ' active' : '') +
          '" onclick="event.stopPropagation();togglePicker(' + i + ',\'assistant\')">' +
          assistLabel + ' <span class="chevron">' + (assistOpen ? '▲' : '▼') + '</span></button>';

      var isEditing = scorerOpen || assistOpen;
      var html =
          '<div class="event-log' + (isEditing ? ' editing' : '') +
          '" onclick="event.stopPropagation()">' +
          '<span style="display:flex;align-items:center;gap:4px;flex:1;flex-wrap:wrap">' +
          '⚽ ' + scorerChip +
          '<span style="color:#64748b;font-size:0.75rem"> (Asist: </span>' +
          assistChip +
          '<span style="color:#64748b;font-size:0.75rem">)</span>' +
          '</span>' +
          '<span class="event-time">' + e.timestamp + '</span>' +
          '<button class="delete-btn" onclick="event.stopPropagation();deleteEvent(' + i + ')">🗑</button>';

      html += '</div>';
      return html;
  }
  ```

  Note: `togglePicker` and `clearAssist` are added in Task 3. The chips render correctly here but clicking them won't work until Task 3.

- [ ] **Step 4: Replace the event list rendering in `renderApp()` to use `renderEventRow`**

  Find the `eventsHtml` assignment:

  ```js
  const eventsHtml = appState.events.length > 0
      ? appState.events.map(e =>
          '<div class="event-log"><span>⚽ <strong>' + e.scorer + '</strong> ' +
          (e.assistant ? '(Asist: ' + e.assistant + ')' : '(Sin asist.)') +
          '</span><span class="event-time">' + e.timestamp + '</span></div>'
        ).join('')
      : '<div class="event-log" style="color:#64748b;justify-content:center;"><em>No hay eventos aún...</em></div>';
  ```

  Replace it with:

  ```js
  const eventsHtml = appState.events.length > 0
      ? appState.events.map(function(e, i) { return renderEventRow(e, i); }).join('')
      : '<div class="event-log" style="color:#64748b;justify-content:center;"><em>No hay eventos aún...</em></div>';
  ```

- [ ] **Step 5: Manual test**

  - Register 2 goals → scroll down to the event list.
  - Each row shows scorer and assistant as small button chips with `▼`, and a 🗑 button.
  - Tap 🗑 on a goal → row disappears, scoreboard decrements by 1.
  - Delete both goals → event list shows "No hay eventos aún…".
  - Tap a chip → nothing visible yet (picker implemented in Task 3).

- [ ] **Step 6: Commit**

  ```bash
  git add static/index.html
  git commit -m "feat: render event list as editable chips with delete button"
  ```

---

### Task 3: Player picker for inline editing

**Files:**
- Modify: `static/index.html`

- [ ] **Step 1: Add CSS for the picker dropdown**

  In the `<style>` block, after `.event-log.editing`, add:

  ```css
  .picker-dropdown {
      background: #1e293b; border: 1px solid #475569; border-radius: 8px;
      padding: 4px; margin-top: 4px;
      max-height: 180px; overflow-y: auto;
      width: 100%;
      box-shadow: 0 4px 16px rgba(0,0,0,0.5);
  }
  .picker-item {
      padding: 6px 10px; border-radius: 5px; font-size: 0.8rem;
      cursor: pointer; color: #f8fafc;
  }
  .picker-item:active { background: #334155; }
  .picker-item.selected { background: #1d4ed8; }
  .picker-item.no-assist { color: #fbbf24; }
  ```

- [ ] **Step 2: Add `renderPickerDropdown(eventIndex, field)` function**

  After `renderEventRow`, add:

  ```js
  function renderPickerDropdown(eventIndex, field) {
      var e = appState.events[eventIndex];
      var players = e.team === 'A' ? teamA : teamB;
      var opts = field === 'scorer' ? players : players.filter(function(p) { return p !== e.scorer; });
      var html = '<div class="picker-dropdown" onclick="event.stopPropagation()">';
      opts.forEach(function(p) {
          var sel = field === 'scorer' ? p === e.scorer : p === e.assistant;
          html += '<div class="picker-item' + (sel ? ' selected' : '') +
                  '" onclick="event.stopPropagation();updateEventPlayer(' + eventIndex + ',\'' +
                  field + '\',\'' + p + '\')">' + p + '</div>';
      });
      if (field === 'assistant') {
          html += '<div class="picker-item no-assist' + (e.assistant === null ? ' selected' : '') +
                  '" onclick="event.stopPropagation();clearAssist(' + eventIndex + ')">Sin asistente</div>';
      }
      html += '</div>';
      return html;
  }
  ```

- [ ] **Step 3: Add `togglePicker`, `updateEventPlayer`, and `clearAssist` functions**

  After `renderPickerDropdown`, add:

  ```js
  function togglePicker(eventIndex, field) {
      var already = appState.editingEvent !== null &&
                    appState.editingEvent.eventIndex === eventIndex &&
                    appState.editingEvent.field === field;
      appState.editingEvent = already ? null : { eventIndex: eventIndex, field: field };
      renderApp();
  }

  function updateEventPlayer(eventIndex, field, playerName) {
      appState.events[eventIndex][field] = playerName;
      appState.editingEvent = null;
      localStorage.setItem('pyball_current_match', JSON.stringify(appState));
      renderApp();
  }

  function clearAssist(eventIndex) {
      appState.events[eventIndex].assistant = null;
      appState.editingEvent = null;
      localStorage.setItem('pyball_current_match', JSON.stringify(appState));
      renderApp();
  }
  ```

- [ ] **Step 4: Update `renderEventRow` to include the picker when open**

  Find the `renderEventRow` function added in Task 2. Replace the two lines:

  ```js
      html += '</div>';
      return html;
  ```

  With:

  ```js
      if (scorerOpen) { html += renderPickerDropdown(i, 'scorer'); }
      if (assistOpen) { html += renderPickerDropdown(i, 'assistant'); }
      html += '</div>';
      return html;
  ```

- [ ] **Step 5: Add document-level click listener to close any open picker**

  In the `// ── SERVICE WORKER` section (just before `initializeApp()`), add:

  ```js
  document.addEventListener('click', function() {
      if (appState.editingEvent !== null) {
          appState.editingEvent = null;
          renderApp();
      }
  });
  ```

- [ ] **Step 6: Manual test — scorer editing**

  - Register a goal with scorer "Manu" and assistant "Suso".
  - Scroll to the event list.
  - Tap the "Manu ▼" chip → a picker dropdown appears listing only team A players; "Manu" is highlighted in blue.
  - Select a different player, e.g. "Caste" → chip now shows "Caste ▼", picker closes.
  - Tap outside the picker → picker closes without change.

- [ ] **Step 7: Manual test — assistant editing**

  - Tap the "Suso ▼" chip → picker shows team A players (excluding scorer) + "Sin asistente" in yellow.
  - Select "Sin asistente" → chip now shows "Sin asist. ▼".
  - Tap the "Sin asist. ▼" chip → picker opens again; "Sin asistente" is highlighted.
  - Select a player → chip shows that player's name.

- [ ] **Step 8: Manual test — only one picker open at a time**

  - Open the scorer picker on event 0 → it opens.
  - Without closing it, tap the assistant chip on the same event → scorer picker closes, assistant picker opens.
  - Tap the scorer chip on event 1 → assistant picker on event 0 closes, scorer picker on event 1 opens.

- [ ] **Step 9: Manual test — state persists across reload**

  - Register 2 goals.
  - Edit scorer of goal 1 to a different player.
  - Reload the page (without closing and reopening the app link).
  - Verify the edited scorer is preserved, no picker is open.

- [ ] **Step 10: Commit**

  ```bash
  git add static/index.html
  git commit -m "feat: add inline player picker for editing goal events"
  ```
