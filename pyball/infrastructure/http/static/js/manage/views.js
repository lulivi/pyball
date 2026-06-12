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

export {
    chipClass, chipLabel, buildChip, buildPanel, buildCandidateList, buildSearch,
    escHtml, escAttr, _formatDate, _buildFreshFlowHTML,
};
