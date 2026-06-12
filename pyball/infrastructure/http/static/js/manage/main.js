import { get, post, ApiError } from '../api.js';
import {
    chipClass, chipLabel, buildChip, buildPanel, buildCandidateList, buildSearch,
    escHtml, escAttr, _formatDate, _buildFreshFlowHTML,
} from './views.js';

// ── STATE ────────────────────────────────────────────────────────────────────
let allPlayers = [];        // [{id, name}, ...] from /api/players
let parsedPlayers = [];     // [{raw, player_id, name, confidence, candidates, excluded}, ...]
let expandedIdx = null;     // which chip is expanded
let lastParsedDate = null;  // ISO date from callup header, e.g. "2026-05-25T20:00"
// state-driven page state (null = state 0; populated = state 1 or 2)
let activeMatchData = null;
let editTeamA = [];          // {id, name}[] — working copy of team A
let editTeamB = [];          // {id, name}[] — working copy of team B
let editReplacingPlayer = null; // {id, name, team: 'A'|'B'} | null

// ── TAB SWITCHING ────────────────────────────────────────────────────────────
function switchTab(name, btn) {
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
    if (name === 'resumen') loadResumen();
}

// ── STEP 1 → 2: PARSE CALLUP ─────────────────────────────────────────────────
async function parseCallup() {
    const text = document.getElementById('callup-input').value.trim();
    if (!text) { alert('Pega la convocatoria primero.'); return; }
    try {
        const [playersRes, parseRes] = await Promise.all([
            get('/api/players'),
            post('/api/meetup/parse-callup', { text }),
        ]);
        allPlayers = playersRes;
        lastParsedDate = parseRes.date || null;
        const dateDisplay = document.getElementById('parsed-date-display');
        if (lastParsedDate) {
            document.getElementById('parsed-date-text').textContent = _formatDate(lastParsedDate);
            dateDisplay.style.display = 'flex';
        } else {
            dateDisplay.style.display = 'none';
        }
        parsedPlayers = [
            ...parseRes.titulars.map(p => ({ ...p, excluded: false })),
            ...parseRes.reserves.map(p => ({ ...p, excluded: true })),
        ];
        expandedIdx = null;
        showStep('review');
        renderChips();
    } catch (e) { alert('Error al reconocer jugadores: ' + e.message); }
}

// ── CHIP RENDERING ────────────────────────────────────────────────────────────
function renderChips() {
    const container = document.getElementById('chip-container');
    container.innerHTML = '';
    parsedPlayers.forEach((p, i) => {
        if (expandedIdx === i) {
            container.appendChild(buildPanel(i, parsedPlayers[i]));
        } else {
            container.appendChild(buildChip(i, parsedPlayers[i], expandedIdx === i));
        }
    });
}

function toggleChipPanel(i) {
    expandedIdx = (expandedIdx === i ? null : i);
    renderChips();
}

function includeChip(i) {
    parsedPlayers[i].excluded = false;
    renderChips();
}

function renderSearchResults(i) {
    const query = document.getElementById('search-' + i).value.toLowerCase();
    const resultsEl = document.getElementById('search-results-' + i);
    if (!query) { resultsEl.innerHTML = ''; return; }
    const matches = allPlayers.filter(p => p.name.toLowerCase().includes(query)).slice(0, 6);
    resultsEl.innerHTML = matches.map(p =>
        `<div class="cand-item" onclick="pickCandidate(${i},'${p.id}')">${escHtml(p.name)}</div>`
    ).join('');
}

function pickCandidate(i, player_id) {
    const fromCandidates = parsedPlayers[i].candidates.find(c => c.player_id === player_id);
    const fromAllPlayers = allPlayers.find(p => p.id === player_id);
    const name = (fromCandidates && fromCandidates.name) || (fromAllPlayers && fromAllPlayers.name) || player_id;
    parsedPlayers[i].player_id = player_id;
    parsedPlayers[i].name = name;
    parsedPlayers[i].candidates = [];
    parsedPlayers[i].confidence = 1.0;
    closePanel();
}

function excludePlayer(i) {
    parsedPlayers[i].excluded = true;
    parsedPlayers[i].player_id = null;
    closePanel();
}

function closePanel() { expandedIdx = null; renderChips(); }

// ── STEP 2 → 3: GENERATE TEAMS ───────────────────────────────────────────────
async function generateTeams() {
    const confirmed = parsedPlayers.filter(p => !p.excluded && p.player_id);
    if (confirmed.length < 2) {
        alert('Necesitas al menos 2 jugadores reconocidos para generar equipos.');
        return;
    }
    const unresolved = parsedPlayers.filter(p => !p.excluded && !p.player_id);
    if (unresolved.length > 0) {
        const names = unresolved.map(p => p.raw).join(', ');
        if (!confirm(`Hay ${unresolved.length} jugador(es) sin resolver: ${names}.\n¿Continuar igualmente?`)) return;
    }

    const today = new Date();
    const pad = n => String(n).padStart(2, '0');
    const date = lastParsedDate ||
        `${today.getFullYear()}-${pad(today.getMonth() + 1)}-${pad(today.getDate())}T20:00`;

    let data;
    try {
        data = await post('/api/meetup/create', { date, player_ids: confirmed.map(p => p.player_id) });
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    activeMatchData = data;
    renderState1(activeMatchData);
}

// ── STATE 1: match without teams ──────────────────────────────────────────
function renderState1(data) {
    const chips = data.players
        .map(p => `<div class="chip ok"><span class="chip-num">✓</span><span class="chip-label">${escHtml(p.name)}</span></div>`)
        .join('');
    document.getElementById('tab-equipos').innerHTML = `
    <div class="date-badge">📅 <span>${_formatDate(data.date)}</span></div>
    <div class="step-label">Jugadores convocados (${data.players.length})</div>
    <div id="chip-container">${chips}</div>
    <button class="btn btn-green" onclick="generateFromActive()">⚽ Generar equipos</button>
  `;
}

async function generateFromActive() {
    const btn = document.querySelector('#tab-equipos .btn-green');
    if (btn) { btn.disabled = true; btn.textContent = 'Generando...'; }
    try {
        activeMatchData = await _callGenerateTeams();
        if (!activeMatchData.teams) {
            alert('Error: el servidor no devolvió equipos.');
            if (btn) { btn.disabled = false; btn.textContent = '⚽ Generar equipos'; }
            return;
        }
        renderState2(activeMatchData);
    } catch (e) {
        alert('Error: ' + e.message);
        if (btn) { btn.disabled = false; btn.textContent = '⚽ Generar equipos'; }
    }
}

// ── STATE 2: match with teams ─────────────────────────────────────────────
function renderState2(data) {
    const t = data.teams;
    const teamsText = `${t.emojiA} *${t.nameA}*\n${t.teamA.join('\n')}\n\n${t.emojiB} *${t.nameB}*\n${t.teamB.join('\n')}`;
    document.getElementById('tab-equipos').innerHTML = `
    <div class="date-badge">📅 <span>${_formatDate(data.date)}</span></div>
    <div id="teams-text" class="teams-box">${escHtml(teamsText)}</div>
    <button class="btn btn-teal" onclick="copyTeams()">📋 Copiar para WhatsApp</button>
    <div class="regen-row">
      <button class="btn-sm gray" onclick="toggleTeamsEditPanel()">✏️ Editar equipos</button>
      <button class="btn-sm green" onclick="regenerateCurrentTeams()">↺ Regenerar</button>
    </div>
    <div id="edit-panel-container"></div>
    <hr class="divider">
    <div class="step-label">Abre el marcador en otro móvil</div>
    <div class="qr-box">
      <canvas id="qr-canvas"></canvas>
      <a class="qr-hint" id="qr-hint" href="${escHtml(t.matchUrl)}" target="_blank" rel="noopener">Link del partido</a>
    </div>
  `;
    _renderQR(t.matchUrl, document.getElementById('qr-canvas'));
}

function copyTeams() {
    _copyToClipboard(document.getElementById('teams-text').textContent);
}

async function regenerateCurrentTeams() {
    const btn = document.querySelector('.regen-row .btn-sm.green');
    if (btn) { btn.textContent = 'Regenerando...'; btn.disabled = true; }
    try {
        activeMatchData = await _callGenerateTeams();
        if (!activeMatchData.teams) {
            alert('Error: el servidor no devolvió equipos.');
            if (btn) { btn.disabled = false; btn.textContent = '↺ Regenerar'; }
            return;
        }
        renderState2(activeMatchData);
    } catch (e) {
        alert('Error: ' + e.message);
        if (btn) { btn.textContent = '↺ Regenerar'; btn.disabled = false; }
    }
}

// ── TEAMS EDIT PANEL ─────────────────────────────────────────────────────
async function toggleTeamsEditPanel() {
    const container = document.getElementById('edit-panel-container');
    if (container.innerHTML) {
        editTeamA = [];
        editTeamB = [];
        editReplacingPlayer = null;
        container.innerHTML = '';
        return;
    }
    const open = () => {
        const t = activeMatchData.teams;
        const byName = {};
        activeMatchData.players.forEach(p => { byName[p.name] = p; });
        editTeamA = t.teamA.map(name => byName[name] || { id: null, name });
        editTeamB = t.teamB.map(name => byName[name] || { id: null, name });
        const missing = [...editTeamA, ...editTeamB].filter(p => !p.id).map(p => p.name);
        if (missing.length) {
            editTeamA = [];
            editTeamB = [];
            alert('No se encontró ID para: ' + missing.join(', ') + '. Recarga la página e inténtalo de nuevo.');
            return;
        }
        editReplacingPlayer = null;
        _renderTeamsEditPanel();
    };
    if (!allPlayers.length) {
        try {
            allPlayers = await get('/api/players');
            open();
        } catch (e) { alert('Error al cargar jugadores: ' + e.message); }
        return;
    }
    open();
}

function moveToOtherTeam(id, fromTeam) {
    const fromArr = fromTeam === 'A' ? editTeamA : editTeamB;
    const toArr = fromTeam === 'A' ? editTeamB : editTeamA;
    const idx = fromArr.findIndex(p => p.id === id);
    if (idx === -1) return;
    const [player] = fromArr.splice(idx, 1);
    toArr.push(player);
    _renderTeamsEditPanel();
}

function startReplacePlayer(id, team) {
    const arr = team === 'A' ? editTeamA : editTeamB;
    const player = arr.find(p => p.id === id);
    if (!player) return;
    editReplacingPlayer = { ...player, team };
    _renderTeamsEditPanel();
}

function pickReplacement(id, name) {
    if (!editReplacingPlayer) return;
    const arr = editReplacingPlayer.team === 'A' ? editTeamA : editTeamB;
    const idx = arr.findIndex(p => p.id === editReplacingPlayer.id);
    if (idx !== -1) arr[idx] = { id, name };
    editReplacingPlayer = null;
    _renderTeamsEditPanel();
}

function cancelReplace() {
    editReplacingPlayer = null;
    _renderTeamsEditPanel();
}

function renderReplaceSearchResults() {
    const query = document.getElementById('replace-search').value.toLowerCase();
    const resultsEl = document.getElementById('replace-results');
    if (!query) { resultsEl.innerHTML = ''; return; }
    const editIds = new Set([...editTeamA, ...editTeamB].map(p => p.id));
    const matches = allPlayers
        .filter(p => p.name.toLowerCase().includes(query) && !editIds.has(p.id))
        .slice(0, 6);
    resultsEl.innerHTML = matches
        .map(p => `<div class="cand-item" data-pid="${escHtml(p.id)}" data-pname="${escHtml(p.name)}" onclick="pickReplacement(this.dataset.pid, this.dataset.pname)">${escHtml(p.name)}</div>`)
        .join('');
}

async function saveTeams() {
    const saveBtn = document.querySelector('#teams-edit-panel .btn-green');
    if (saveBtn) { saveBtn.disabled = true; saveBtn.textContent = 'Guardando...'; }
    let data;
    try {
        data = await post('/api/meetup/assign-teams', {
            date: activeMatchData.date,
            team_a_ids: editTeamA.map(p => p.id),
            team_b_ids: editTeamB.map(p => p.id),
        });
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '💾 Guardar equipos'; }
        return;
    }
    activeMatchData = data;
    editTeamA = [];
    editTeamB = [];
    editReplacingPlayer = null;
    renderState2(activeMatchData);
}

// ── TAB: RESUMEN ──────────────────────────────────────────────────────────────
async function loadResumen() {
    const el = document.getElementById('resumen-content');
    el.innerHTML = '<div class="empty-state">Cargando...</div>';
    try {
        let latestData;
        try {
            latestData = await get('/api/match/latest');
        } catch (err) {
            if (err instanceof ApiError && err.status === 404) {
                el.innerHTML = '<div class="empty-state">Aún no hay partidos terminados.</div>';
                return;
            }
            throw err;
        }
        const { date } = latestData;
        let summaryData;
        try {
            summaryData = await get(`/api/match/${encodeURIComponent(date)}/summary`);
        } catch {
            el.innerHTML = '<div class="empty-state">Error al cargar el resumen.</div>';
            return;
        }
        const { date_label, message } = summaryData;

        el.innerHTML = `
      <div class="step-label">${escHtml(date_label)}</div>
      <div class="summary-box" id="summary-msg">${escHtml(message)}</div>
      <button class="btn btn-teal" onclick="copySummary()">📋 Copiar texto</button>
      <button class="btn btn-purple" data-share-date="${escHtml(date)}" onclick="shareStats(this, this.dataset.shareDate, document.getElementById('summary-msg').textContent)">📤 Compartir imagen con texto</button>
      <button class="btn btn-purple" data-date="${escHtml(date)}" onclick="downloadStats(this.dataset.date)">📥 Descargar imagen</button>
      <hr class="divider">
      <button class="btn-sm green" data-date="${escHtml(date)}"
        onclick="openEditMode(this.dataset.date)">✏️ Corregir resultado</button>
    `;
    } catch (e) { el.innerHTML = '<div class="empty-state">Error de red.</div>'; }
}

function copySummary() {
    _copyToClipboard(document.getElementById('summary-msg').textContent);
}

async function downloadStats(date) {
    const url = `/api/match/${encodeURIComponent(date)}/stats.png`;
    const a = document.createElement('a');
    a.href = url;
    a.download = `stats-${date}.png`;
    a.click();
}

async function shareStats(btn, date, summaryText) {
    if (btn) { btn.disabled = true; btn.textContent = 'Preparando…'; }
    try {
        const url = `/api/match/${encodeURIComponent(date)}/stats.png`;
        // binary response: raw fetch
        const res = await fetch(url);
        if (!res.ok) throw new Error('Error al descargar la imagen');
        const blob = await res.blob();
        const file = new File([blob], `stats-${date}.png`, { type: 'image/png' });
        if (navigator.canShare && navigator.canShare({ files: [file] })) {
            await navigator.share({ files: [file], text: summaryText || document.getElementById('summary-msg')?.textContent || '' });
        } else {
            alert('Compartir archivos no está disponible en este navegador.');
        }
    } catch (e) {
        if (e.name !== 'AbortError') alert('Error al compartir: ' + e.message);
    } finally {
        if (btn) { btn.disabled = false; btn.textContent = '📤 Compartir imagen con texto'; }
    }
}

// ── HELPERS ───────────────────────────────────────────────────────────────────
function showStep(name) {
    ['paste', 'review'].forEach(s =>
        document.getElementById('step-' + s).style.display = s === name ? 'block' : 'none'
    );
}

function openEditMode(date) {
    if (!date) { alert('Selecciona una fecha.'); return; }
    window.location.href = '/match?edit=1&date=' + encodeURIComponent(date);
}

// ── BOOTSTRAP ─────────────────────────────────────────────────────────────
async function bootstrap() {
    let attempts = 0;

    const showConnecting = () => {
        const msg = attempts >= 3
            ? 'Está tardando más de lo esperado...'
            : 'Conectando con el servidor...';
        document.getElementById('tab-equipos').innerHTML = `
      <div class="no-match">
        <div class="no-match-icon">⚽</div>
        <div class="no-match-title">PyBall</div>
        <div class="no-match-msg">${msg}</div>
        <div class="spinner"></div>
      </div>
    `;
    };

    showConnecting();

    while (true) {
        try {
            let data;
            try {
                data = await get('/api/meetup/active');
            } catch (err) {
                if (err instanceof ApiError && err.status === 404) {
                    _buildFreshFlowHTML();
                    showStep('paste');
                    return;
                }
                if (err instanceof ApiError && err.status !== 0) {
                    _buildFreshFlowHTML();
                    showStep('paste');
                    document.getElementById('step-paste').insertAdjacentHTML(
                        'afterbegin',
                        '<div class="load-warning">⚠ Error al cargar el partido activo. Puedes crear uno nuevo.</div>'
                    );
                    return;
                }
                throw err;
            }
            activeMatchData = data;
            if (activeMatchData.teams) {
                renderState2(activeMatchData);
            } else {
                renderState1(activeMatchData);
            }
            return;
        } catch {
            // network error — fall through to retry
        }
        attempts++;
        showConnecting();
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

// ── PRIVATE HELPERS ───────────────────────────────────────────────────────────
function _renderQR(url, canvas) {
    try {
        const qr = qrcode(0, 'M');
        qr.addData(url);
        qr.make();
        const cells = qr.getModuleCount();
        const margin = 4;
        const scale = Math.max(4, Math.floor(220 / cells));
        const size = (cells + margin * 2) * scale;
        canvas.width = size;
        canvas.height = size;
        const ctx = canvas.getContext('2d');
        ctx.fillStyle = '#ffffff';
        ctx.fillRect(0, 0, size, size);
        for (let r = 0; r < cells; r++) {
            for (let c = 0; c < cells; c++) {
                ctx.fillStyle = qr.isDark(r, c) ? '#000000' : '#ffffff';
                ctx.fillRect((c + margin) * scale, (r + margin) * scale, scale, scale);
            }
        }
    } catch (e) {
        canvas.style.display = 'none';
    }
}

async function _callGenerateTeams() {
    try {
        return await post('/api/meetup/generate-teams', { date: activeMatchData.date, algorithm: 'balanceado' });
    } catch (err) {
        throw new Error(err.detail || err.message);
    }
}

function _renderTeamsEditPanel() {
    const unequal = editTeamA.length !== editTeamB.length;
    const t = activeMatchData.teams;

    const row = (p, team) => {
        const hl = editReplacingPlayer && editReplacingPlayer.id === p.id
            ? 'background:#431407;border-color:#ef4444;' : '';
        const nameBtn = `<span style="color:#38bdf8;text-decoration:underline;cursor:pointer;flex:1;"
      onclick="startReplacePlayer('${escAttr(p.id)}','${team}')">${escHtml(p.name)}</span>`;
        const arrow = team === 'A'
            ? `<button class="btn-sm gray" style="padding:3px 8px;font-size:0.85rem;"
           onclick="moveToOtherTeam('${escAttr(p.id)}','A')">➡️</button>`
            : `<button class="btn-sm gray" style="padding:3px 8px;font-size:0.85rem;"
           onclick="moveToOtherTeam('${escAttr(p.id)}','B')">⬅️</button>`;
        const order = team === 'A'
            ? `${nameBtn}${arrow}` : `${arrow}${nameBtn}`;
        return `<div class="edit-chip" style="${hl}">${order}</div>`;
    };

    const replaceSearch = editReplacingPlayer ? `
    <div style="background:#1e293b;border:1px solid #3b82f6;border-radius:6px;padding:8px;margin-bottom:8px;">
      <div style="font-size:0.72rem;color:#94a3b8;margin-bottom:5px;">
        Reemplazar a <strong style="color:#fca5a5;">${escHtml(editReplacingPlayer.name)}</strong>:</div>
      <input class="search-box" id="replace-search" type="text" placeholder="Buscar jugador..."
        oninput="renderReplaceSearchResults()">
      <div id="replace-results" class="cand-list"></div>
      <button class="skip-link" style="margin-top:4px;" onclick="cancelReplace()">✕ Cancelar</button>
    </div>` : '';

    const saveBtn = unequal
        ? `<button class="btn btn-green" style="margin-top:4px;opacity:0.5;cursor:not-allowed;"
         disabled>💾 Guardar equipos</button>`
        : `<button class="btn btn-green" style="margin-top:4px;"
         onclick="saveTeams()">💾 Guardar equipos</button>`;

    document.getElementById('edit-panel-container').innerHTML = `
    <div class="edit-panel" id="teams-edit-panel">
      <div class="edit-panel-header">
        <div class="step-label" style="margin:0;">✏️ Editar equipos</div>
        <button class="close-x" onclick="toggleTeamsEditPanel()">✕</button>
      </div>
      ${replaceSearch}
      <div style="display:flex;gap:8px;margin-bottom:8px;">
        <div style="flex:1;">
          <div class="step-label" style="font-size:0.65rem;">${escHtml(t.emojiA)} ${escHtml(t.nameA)} (${editTeamA.length})</div>
          ${editTeamA.map(p => row(p, 'A')).join('')}
        </div>
        <div style="flex:1;">
          <div class="step-label" style="font-size:0.65rem;">${escHtml(t.emojiB)} ${escHtml(t.nameB)} (${editTeamB.length})</div>
          ${editTeamB.map(p => row(p, 'B')).join('')}
        </div>
      </div>
      ${unequal ? '<div class="load-warning">⚠ Los equipos deben tener el mismo número de jugadores</div>' : ''}
      ${saveBtn}
    </div>
  `;
}

function _copyToClipboard(text) {
    if (navigator.clipboard) {
        navigator.clipboard.writeText(text).then(() => alert('Copiado al portapapeles ✓'));
        return;
    }
    const ta = document.createElement('textarea');
    ta.value = text;
    ta.style.cssText = 'position:fixed;opacity:0';
    document.body.appendChild(ta);
    ta.focus();
    ta.select();
    try {
        document.execCommand('copy');
        alert('Copiado al portapapeles ✓');
    } catch (e) {
        alert('No se pudo copiar. Por favor copia el texto manualmente.');
    }
    document.body.removeChild(ta);
}

// ── WINDOW BINDINGS ───────────────────────────────────────────────────────────
Object.assign(window, {
    switchTab,
    parseCallup,
    generateTeams,
    generateFromActive,
    copyTeams,
    regenerateCurrentTeams,
    toggleTeamsEditPanel,
    moveToOtherTeam,
    startReplacePlayer,
    pickReplacement,
    cancelReplace,
    saveTeams,
    copySummary,
    downloadStats,
    shareStats,
    loadResumen,
    pickCandidate,
    excludePlayer,
    closePanel,
    openEditMode,
    showStep,
    renderReplaceSearchResults,
    renderSearchResults,
    toggleChipPanel,
    includeChip,
});

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/manage' })
        .catch(err => console.warn('SW registration failed:', err));
}

bootstrap();
