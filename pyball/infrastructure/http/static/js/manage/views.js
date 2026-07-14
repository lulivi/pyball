// Pure HTML-builder and formatter functions for the manage page.
// No imports from main.js — receives any needed state as parameters.

function chipClass(p) {
    if (p.excluded) return 'excl';
    if (p.player_id) return 'ok';
    if (p.candidates && p.candidates.length > 0) return 'warn';
    return 'err';
}

function chipLabel(p) {
    if (p.excluded) return p.name || p.raw;
    if (p.player_id) return '✓ ' + p.name;
    if (p.candidates && p.candidates.length > 0) return '⚠ ' + p.raw;
    return '✗ ' + p.raw;
}

function buildChip(i, p, isExpanded) {
    const el = document.createElement('div');
    el.className = 'chip ' + chipClass(p);
    el.innerHTML = `<span class="chip-num">${i + 1}.</span><span class="chip-label">${escHtml(chipLabel(p))}</span>${p.excluded ? '' : '<span class="chev">▼</span>'}`;
    if (!p.excluded) {
        el.onclick = () => { window.toggleChipPanel(i); };
    } else {
        el.onclick = () => { window.includeChip(i); };
        el.title = 'Clic para incluir';
    }
    return el;
}

function buildPanel(i, p) {
    const isWarn = p.candidates && p.candidates.length > 0;
    const div = document.createElement('div');
    div.className = 'chip-panel ' + (isWarn ? 'warn-panel' : 'err-panel');

    div.innerHTML = `
    <div class="panel-header">
      <div class="panel-raw">Texto original: <span>${escHtml(p.raw)}</span></div>
      <button class="close-x" onclick="closePanel()">✕</button>
    </div>
    ${isWarn ? buildCandidateList(i, p) : buildSearch(i)}
    <button class="skip-link" onclick="excludePlayer(${i})">⊘ No incluir este jugador</button>
  `;
    return div;
}

function buildCandidateList(i, p) {
    let html = '<div class="step-label" style="font-size:0.68rem;margin-bottom:4px;">Candidatos por similitud</div><div class="cand-list">';
    p.candidates.forEach(c => {
        const pct = Math.round(c.confidence * 100);
        html += `<div class="cand-item" onclick="pickCandidate(${i},'${c.player_id}')">
      ${escHtml(c.name)} <span class="cand-score">${pct}%</span>
    </div>`;
    });
    html += '</div>';
    return html;
}

function buildSearch(i) {
    return `
    <div class="step-label" style="font-size:0.68rem;margin-bottom:4px;">Buscar en la base de datos</div>
    <input class="search-box" id="search-${i}" type="text" placeholder="Escribe para buscar..."
      oninput="renderSearchResults(${i})">
    <div id="search-results-${i}" class="cand-list"></div>
  `;
}

function escHtml(s) {
    return String(s).replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;').replace(/"/g, '&quot;');
}

function escAttr(s) {
    return String(s).replace(/'/g, "\\'");
}

function _formatDate(iso) {
    if (!iso) return '';
    const d = new Date(iso);
    if (isNaN(d.getTime())) return '';
    const day = d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
    const time = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    return `${day.charAt(0).toUpperCase()}${day.slice(1)} · ${time}`;
}

function _buildFreshFlowHTML() {
    document.getElementById('tab-equipos').innerHTML = `
    <div id="step-paste">
      <div class="step-label">1. Pega la convocatoria</div>
      <textarea id="callup-input" class="paste-area" placeholder="Lunes 18 Mayo&#10;1. Juande&#10;2. David Quesada&#10;...&#10;&#10;Reservas&#10;- Manu&#10;..."></textarea>
      <button class="btn btn-blue" onclick="parseCallup()">🔍 Reconocer jugadores</button>
    </div>
    <div id="step-review" style="display:none">
      <div class="step-label">2. Revisa los jugadores</div>
      <div id="parsed-date-display" class="date-badge" style="display:none">📅 <span id="parsed-date-text"></span></div>
      <div id="review-legend" style="font-size:0.72rem;color:#64748b;margin-bottom:8px;">
        ✓ Reconocido &nbsp; ⚠ Dudoso (toca para elegir) &nbsp; ✗ No encontrado (toca para buscar) &nbsp; Tachado = Reserva excluida
      </div>
      <div id="chip-container"></div>
      <button class="btn btn-green" onclick="generateTeams()">⚽ Generar equipos equilibrados</button>
    </div>
  `;
}

function buildRosterRow(p) {
    return `<div class="edit-chip">
      <span style="flex:1;">${escHtml(p.name)}</span>
      <button class="remove-btn" data-pid="${escHtml(p.id)}"
        onclick="removeFromRoster(this.dataset.pid)">✕</button>
    </div>`;
}

function buildRosterList(players) {
    return players.map(buildRosterRow).join('');
}

// One collapsed row in the Convocatorias list. `open` = detail panel expanded.
function buildConvocatoriaRow(item, open) {
    return `
    <button class="collapsible-trigger" data-date="${escHtml(item.date)}"
      onclick="toggleConvocatoriaRow(this.dataset.date)">
      <span>📅 ${escHtml(_formatDate(item.date))} · ${escHtml(item.location)}</span>
      <span>${open ? '▾' : '▸'}</span>
    </button>
    <div id="convocatoria-detail-${escHtml(item.date)}"></div>`;
}

// Detail panel for one expanded row — identical content to the old Resumen tab,
// parameterised by date instead of always "the latest match".
function buildConvocatoriaDetail(date, message) {
    return `
    <div class="summary-box" id="summary-msg-${escHtml(date)}">${escHtml(message)}</div>
    <button class="btn btn-teal" data-date="${escHtml(date)}" onclick="copySummary(this.dataset.date)">📋 Copiar texto</button>
    <button class="btn btn-purple" data-date="${escHtml(date)}" onclick="shareStats(this, this.dataset.date, document.getElementById('summary-msg-' + this.dataset.date).textContent)">📤 Compartir imagen con texto</button>
    <button class="btn btn-purple" data-date="${escHtml(date)}" onclick="downloadStats(this.dataset.date)">📥 Descargar imagen</button>
    <hr class="divider">
    <button class="btn-sm green" data-date="${escHtml(date)}"
      onclick="openEditMode(this.dataset.date)">✏️ Corregir resultado</button>`;
}

// Date/location editor shown next to the date badge in "Convocatoria actual".
// `data` is activeMatchData ({date, location, ...}); `open` toggles edit mode.
function buildDateLocationEditor(data, open) {
    if (!open) {
        return `<button class="btn-sm gray" onclick="toggleDateLocationEdit()">✏️ ${escHtml(data.location || '')}</button>`;
    }
    const [datePart, timePart] = (data.date || '').split('T');
    return `
    <div class="edit-panel">
      <div class="field-label">Fecha</div>
      <input class="search-box" id="edit-date-input" type="date" value="${escHtml(datePart || '')}">
      <div class="field-label">Hora</div>
      <input class="search-box" id="edit-time-input" type="time" value="${escHtml(timePart || '')}">
      <div class="field-label">Ubicación</div>
      <input class="search-box" id="edit-location-input" type="text" value="${escHtml(data.location || '')}">
      <div class="edit-actions">
        <button class="btn-sm green" onclick="saveDateLocationEdit()">Guardar</button>
        <button class="btn-sm gray" onclick="toggleDateLocationEdit()">Cancelar</button>
      </div>
    </div>`;
}

// Search input + results container for the add-player widget.
// idPrefix yields #<idPrefix>-search and #<idPrefix>-results; searchFn is the
// oninput handler call as a string, e.g. 'searchRosterAdd()'.
function buildAddPlayerPanel(idPrefix, searchFn) {
    return `
    <div style="margin-top:6px;">
      <input class="search-box" id="${idPrefix}-search" type="text" autocomplete="off"
        placeholder="Buscar jugador..." oninput="${searchFn}">
      <div id="${idPrefix}-results" class="cand-list"></div>
    </div>`;
}

// Result rows for the add-player widget. opts: { pickFn, team? }.
// pickFn is called as pickFn(id, name[, team]).
function buildAddResults(results, opts) {
    const teamArg = opts.team ? `, '${opts.team}'` : '';
    return results.map(p =>
        `<div class="cand-item" data-pid="${escHtml(p.id)}" data-pname="${escHtml(p.name)}"
       onclick="${opts.pickFn}(this.dataset.pid, this.dataset.pname${teamArg})">${escHtml(p.name)}</div>`
    ).join('');
}

function buildRepasteTrigger(open) {
    const body = open ? `
      <textarea id="repaste-input" class="paste-area"
        placeholder="Pega aquí la nueva convocatoria..."></textarea>
      <button class="btn btn-blue" onclick="parseRepaste()">🔍 Reconocer jugadores</button>
      <div id="repaste-review"></div>` : '';
    return `
    <button class="collapsible-trigger" onclick="toggleRepaste()">
      <span>📋 Re-pegar convocatoria</span><span>${open ? '▾' : '▸'}</span>
    </button>
    <div id="repaste-container">${body}</div>`;
}

function buildCancelTrigger() {
    return `<button class="cancel-match-btn" onclick="cancelMeetup()">🗑 Cancelar partido</button>`;
}

export {
    chipClass, chipLabel, buildChip, buildPanel, buildCandidateList, buildSearch,
    buildRosterRow, buildRosterList, buildAddPlayerPanel, buildAddResults,
    buildRepasteTrigger, buildCancelTrigger, buildDateLocationEditor,
    buildConvocatoriaRow, buildConvocatoriaDetail,
    escHtml, escAttr, _formatDate, _buildFreshFlowHTML,
};
