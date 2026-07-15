import { get, post, del, ApiError } from '../api.js';
import {
    chipClass, chipLabel, buildChip, buildPanel, buildCandidateList, buildSearch,
    buildRosterList, buildAddPlayerPanel, buildAddResults,
    buildRepasteTrigger, buildCancelTrigger, buildDateLocationEditor, buildManualCreatePanel,
    buildConvocatoriaRow, buildConvocatoriaDetail,
    escHtml, escAttr, _formatDate, _buildFreshFlowHTML,
} from './views.js';

// ── STATE ────────────────────────────────────────────────────────────────────
let allPlayers = [];        // [{id, name}, ...] from /api/players
let parsedPlayers = [];     // [{raw, player_id, name, confidence, candidates, excluded}, ...]
let expandedIdx = null;     // which chip is expanded
let lastParsedDate = null;  // ISO date from callup header, e.g. "2026-05-25T20:00"
// state-driven page state (null = state 0; populated = state 1 or 2)
let activeMatchData = null;
let editTeams = { A: [], B: [], C: [] };  // {id, name}[] per team letter — working copies
let editTeamLetters = ['A', 'B'];          // ['A','B'] or ['A','B','C'] — set when panel opens
let editGoalkeepers = { A: null, B: null, C: null }; // playerId | null per team letter
let editReplacingPlayer = null; // {id, name, team: 'A'|'B'|'C'} | null
let rosterAddVisible = false;   // State 1: add-player search panel open?
let rosterSearchQuery = '';     // State 1: current add-player search text
let editAddOpenTeam = null;     // State 2 edit panel: 'A' | 'B' | 'C' | null — which column's add widget is open
let editAddQuery = '';          // State 2 edit panel: current add search text
let repastePanelOpen = false;   // collapsed re-paste section open?
let manualCreateOpen = false;   // manual create-date/location form open?
let pasteFlowOpen = false;      // paste-a-callup textarea revealed?
let dateLocationEditOpen = false; // date/location edit panel open?
let expandedConvocatoriaDate = null; // which Convocatorias row is expanded, if any

// ── TAB SWITCHING ────────────────────────────────────────────────────────────
function switchTab(name, btn) {
    document.querySelectorAll('.tab-view').forEach(v => v.classList.remove('active'));
    document.querySelectorAll('.tab-btn').forEach(b => b.classList.remove('active'));
    document.getElementById('tab-' + name).classList.add('active');
    btn.classList.add('active');
    if (name === 'convocatorias') loadConvocatorias();
    if (name === 'jugadores') window.loadJugadores();
}

// ── NO ACTIVE MEETUP: three creation actions ─────────────────────────────────
async function createNextMeetup() {
    let data;
    try {
        data = await post('/api/meetup/create-next', {});
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    activeMatchData = data;
    manualCreateOpen = false;
    pasteFlowOpen = false;
    renderState1(activeMatchData);
}

function toggleManualCreate() {
    manualCreateOpen = !manualCreateOpen;
    if (manualCreateOpen) { pasteFlowOpen = false; _renderPasteContainer(); }
    _renderManualCreateContainer();
}

async function confirmManualCreate() {
    const date = document.getElementById('create-date-input').value;
    const time = document.getElementById('create-time-input').value;
    const location = document.getElementById('create-location-input').value.trim();
    if (!date || !time || !location) {
        alert('Completa fecha, hora y ubicación.');
        return;
    }
    const iso = `${date}T${time}`;
    let created;
    try {
        created = await post('/api/meetup/create', { date: iso, player_ids: [] });
        await post('/api/meetup/location', { date: created.date, location });
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    activeMatchData = { ...created, location };
    manualCreateOpen = false;
    pasteFlowOpen = false;
    renderState1(activeMatchData);
}

function togglePasteFlow() {
    pasteFlowOpen = !pasteFlowOpen;
    if (pasteFlowOpen) { manualCreateOpen = false; _renderManualCreateContainer(); }
    _renderPasteContainer();
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
    const addBtnLabel = rosterAddVisible ? '✕ Cerrar búsqueda' : '+ Añadir jugador';
    const addPanel = rosterAddVisible
        ? buildAddPlayerPanel('roster-add', 'searchRosterAdd()')
        : '';
    document.getElementById('tab-equipos').innerHTML = `
    ${buildDateLocationEditor(data, dateLocationEditOpen)}
    <div class="step-label">Jugadores convocados (${data.players.length})</div>
    <div id="roster-list">${buildRosterList(data.players)}</div>
    <button class="btn-sm gray" style="margin-top:6px;" onclick="toggleRosterAdd()">${addBtnLabel}</button>
    ${addPanel}
    <div class="action-row">
      <button class="btn btn-green" onclick="generateFromActive(2, this)">⚽ Generar 2 equipos</button>
      <button class="btn btn-green" onclick="generateFromActive(3, this)">⚽ Generar 3 equipos</button>
    </div>
    ${buildRepasteTrigger(repastePanelOpen)}
    ${buildCancelTrigger()}
  `;
    if (rosterAddVisible) {
        const input = document.getElementById('roster-add-search');
        input.value = rosterSearchQuery;
        input.focus();
        searchRosterAdd();
    }
}

async function generateFromActive(teamCount, btn) {
    const buttons = document.querySelectorAll('#tab-equipos .action-row .btn');
    const originalLabels = Array.from(buttons).map(b => b.textContent);
    buttons.forEach(b => { b.disabled = true; });
    if (btn) btn.textContent = 'Generando...';
    try {
        activeMatchData = await _callGenerateTeams(teamCount);
        if (!activeMatchData.teams) {
            alert('Error: el servidor no devolvió equipos.');
            buttons.forEach((b, i) => { b.disabled = false; b.textContent = originalLabels[i]; });
            return;
        }
        renderState2(activeMatchData);
    } catch (e) {
        alert('Error: ' + e.message);
        buttons.forEach((b, i) => { b.disabled = false; b.textContent = originalLabels[i]; });
    }
}

async function removeFromRoster(id) {
    const remaining = activeMatchData.players.filter(p => p.id !== id);
    await _saveRoster(remaining.map(p => p.id));
}

async function toggleDateLocationEdit() {
    if (!dateLocationEditOpen && activeMatchData.location === undefined) {
        try {
            const active = await get('/api/meetup/active');
            activeMatchData.location = active.location;
        } catch {
            activeMatchData.location = '';
        }
    }
    dateLocationEditOpen = !dateLocationEditOpen;
    _rerenderActiveState();
}

async function saveDateLocationEdit() {
    const newDate = document.getElementById('edit-date-input').value;
    const newTime = document.getElementById('edit-time-input').value;
    const newLocation = document.getElementById('edit-location-input').value.trim();
    if (!newDate || !newTime || !newLocation) {
        alert('Completa fecha, hora y ubicación.');
        return;
    }
    const newIso = `${newDate}T${newTime}`;
    try {
        if (newIso !== activeMatchData.date) {
            await post('/api/meetup/date', { old_date: activeMatchData.date, new_date: newIso });
            activeMatchData.date = newIso;
        }
        if (newLocation !== activeMatchData.location) {
            await post('/api/meetup/location', { date: activeMatchData.date, location: newLocation });
            activeMatchData.location = newLocation;
        }
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    dateLocationEditOpen = false;
    _rerenderActiveState();
}

function toggleRosterAdd() {
    rosterAddVisible = !rosterAddVisible;
    rosterSearchQuery = '';
    renderState1(activeMatchData);
}

async function searchRosterAdd() {
    const input = document.getElementById('roster-add-search');
    rosterSearchQuery = input ? input.value.trim() : '';
    if (!allPlayers.length) {
        try { allPlayers = await get('/api/players'); }
        catch (e) { alert('Error al cargar jugadores: ' + e.message); return; }
    }
    const resultsEl = document.getElementById('roster-add-results');
    if (!resultsEl) return;
    if (!rosterSearchQuery) { resultsEl.innerHTML = ''; return; }
    const rosterIds = new Set(activeMatchData.players.map(p => p.id));
    const q = rosterSearchQuery.toLowerCase();
    const matches = allPlayers
        .filter(p => p.name.toLowerCase().includes(q) && !rosterIds.has(p.id))
        .slice(0, 6);
    resultsEl.innerHTML = buildAddResults(matches, { pickFn: 'pickRosterAdd' });
}

async function pickRosterAdd(id) {
    const ids = activeMatchData.players.map(p => p.id);
    ids.push(id);
    await _saveRoster(ids);
}

// ── STATE 2: match with teams ─────────────────────────────────────────────
function renderState2(data) {
    const t = data.teams;
    const blocks = [`${t.emojiA} *${t.nameA}*\n${t.teamA.join('\n')}`, `${t.emojiB} *${t.nameB}*\n${t.teamB.join('\n')}`];
    if (t.teamC) blocks.push(`${t.emojiC} *${t.nameC}*\n${t.teamC.join('\n')}`);
    const teamsText = blocks.join('\n\n');
    document.getElementById('tab-equipos').innerHTML = `
    ${buildDateLocationEditor(data, dateLocationEditOpen)}
    ${buildRepasteTrigger(repastePanelOpen)}
    <div id="teams-text" class="teams-box">${escHtml(teamsText)}</div>
    <div class="action-row">
      <button class="btn btn-green regen-btn" onclick="regenerateCurrentTeams(2, this)">↺ Regenerar equipos (2)</button>
      <button class="btn btn-green regen-btn" onclick="regenerateCurrentTeams(3, this)">↺ Regenerar equipos (3)</button>
    </div>
    <button class="btn btn-gray" onclick="toggleTeamsEditPanel()">✏️ Editar equipos</button>
    <button class="btn btn-teal" onclick="copyTeams()">📋 Copiar equipos</button>
    ${t.teamC ? '<button class="btn-sm amber" style="width:100%;margin-bottom:10px;" onclick="closeMeetup()">🏁 Cerrar triangular</button>' : ''}
    <div id="edit-panel-container"></div>
    ${buildCancelTrigger()}
  `;
}

function copyTeams() {
    _copyToClipboard(document.getElementById('teams-text').textContent);
}

async function regenerateCurrentTeams(teamCount, btn) {
    const buttons = document.querySelectorAll('.regen-btn');
    const originalLabels = Array.from(buttons).map(b => b.textContent);
    buttons.forEach(b => { b.disabled = true; });
    if (btn) btn.textContent = 'Regenerando...';
    try {
        activeMatchData = await _callGenerateTeams(teamCount);
        if (!activeMatchData.teams) {
            alert('Error: el servidor no devolvió equipos.');
            buttons.forEach((b, i) => { b.disabled = false; b.textContent = originalLabels[i]; });
            return;
        }
        renderState2(activeMatchData);
    } catch (e) {
        alert('Error: ' + e.message);
        buttons.forEach((b, i) => { b.disabled = false; b.textContent = originalLabels[i]; });
    }
}

// ── TEAMS EDIT PANEL ─────────────────────────────────────────────────────
async function toggleTeamsEditPanel() {
    const container = document.getElementById('edit-panel-container');
    if (container.innerHTML) {
        editTeamLetters.forEach(letter => { editTeams[letter] = []; editGoalkeepers[letter] = null; });
        editReplacingPlayer = null;
        editAddOpenTeam = null;
        editAddQuery = '';
        container.innerHTML = '';
        const teamsBox = document.getElementById('teams-text');
        if (teamsBox) teamsBox.style.display = '';
        return;
    }
    const open = () => {
        const t = activeMatchData.teams;
        const byName = {};
        activeMatchData.players.forEach(p => { byName[p.name] = p; });
        editTeamLetters = t.teamC ? ['A', 'B', 'C'] : ['A', 'B'];
        const namesByLetter = { A: t.teamA, B: t.teamB, C: t.teamC };
        const gkByLetter = { A: t.goalkeeperA, B: t.goalkeeperB, C: t.goalkeeperC };
        editTeamLetters.forEach(letter => { editGoalkeepers[letter] = gkByLetter[letter] || null; });
        editTeamLetters.forEach(letter => {
            editTeams[letter] = namesByLetter[letter].map(name => byName[name] || { id: null, name });
        });
        const missing = editTeamLetters
            .flatMap(letter => editTeams[letter])
            .filter(p => !p.id)
            .map(p => p.name);
        if (missing.length) {
            editTeamLetters.forEach(letter => { editTeams[letter] = []; });
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

function moveToOtherTeam(id, fromTeam, toTeam) {
    const fromArr = editTeams[fromTeam];
    const idx = fromArr.findIndex(p => p.id === id);
    if (idx === -1) return;
    const [player] = fromArr.splice(idx, 1);
    if (editGoalkeepers[fromTeam] === id) editGoalkeepers[fromTeam] = null;
    editTeams[toTeam].push(player);
    _renderTeamsEditPanel();
}

function setEditGoalkeeper(team, playerId) {
    editGoalkeepers[team] = playerId || null;
}

function startReplacePlayer(id, team) {
    const player = editTeams[team].find(p => p.id === id);
    if (!player) return;
    editReplacingPlayer = { ...player, team };
    _renderTeamsEditPanel();
}

function pickReplacement(id, name) {
    if (!editReplacingPlayer) return;
    const arr = editTeams[editReplacingPlayer.team];
    const idx = arr.findIndex(p => p.id === editReplacingPlayer.id);
    if (idx !== -1) arr[idx] = { id, name };
    editReplacingPlayer = null;
    _renderTeamsEditPanel();
}

function cancelReplace() {
    editReplacingPlayer = null;
    _renderTeamsEditPanel();
}

function removeFromEditTeam(id, team) {
    const arr = editTeams[team];
    const idx = arr.findIndex(p => p.id === id);
    if (idx !== -1) arr.splice(idx, 1);
    if (editGoalkeepers[team] === id) editGoalkeepers[team] = null;
    _renderTeamsEditPanel();
}

function toggleEditAdd(team) {
    editAddOpenTeam = (editAddOpenTeam === team ? null : team);
    editAddQuery = '';
    _renderTeamsEditPanel();
}

function searchEditAdd() {
    const input = document.getElementById('edit-add-search');
    editAddQuery = input ? input.value.trim() : '';
    const resultsEl = document.getElementById('edit-add-results');
    if (!resultsEl) return;
    if (!editAddQuery) { resultsEl.innerHTML = ''; return; }
    const usedIds = new Set(editTeamLetters.flatMap(letter => editTeams[letter]).map(p => p.id));
    const q = editAddQuery.toLowerCase();
    const matches = allPlayers
        .filter(p => p.name.toLowerCase().includes(q) && !usedIds.has(p.id))
        .slice(0, 6);
    resultsEl.innerHTML = buildAddResults(matches, { pickFn: 'pickEditAdd', team: editAddOpenTeam });
}

function pickEditAdd(id, name, team) {
    editTeams[team].push({ id, name });
    editAddOpenTeam = null;
    editAddQuery = '';
    _renderTeamsEditPanel();
}

function renderReplaceSearchResults() {
    const query = document.getElementById('replace-search').value.toLowerCase();
    const resultsEl = document.getElementById('replace-results');
    if (!query) { resultsEl.innerHTML = ''; return; }
    const editIds = new Set(editTeamLetters.flatMap(letter => editTeams[letter]).map(p => p.id));
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
    const body = {
        date: activeMatchData.date,
        team_a_ids: editTeams.A.map(p => p.id),
        team_b_ids: editTeams.B.map(p => p.id),
        team_a_goalkeeper_id: editGoalkeepers.A,
        team_b_goalkeeper_id: editGoalkeepers.B,
    };
    if (editTeamLetters.includes('C')) {
        body.team_c_ids = editTeams.C.map(p => p.id);
        body.team_c_goalkeeper_id = editGoalkeepers.C;
    }
    let data;
    try {
        data = await post('/api/meetup/assign-teams', body);
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        if (saveBtn) { saveBtn.disabled = false; saveBtn.textContent = '💾 Guardar equipos'; }
        return;
    }
    activeMatchData = data;
    editTeamLetters.forEach(letter => { editTeams[letter] = []; editGoalkeepers[letter] = null; });
    editReplacingPlayer = null;
    editAddOpenTeam = null;
    editAddQuery = '';
    renderState2(activeMatchData);
}

function toggleRepaste() {
    repastePanelOpen = !repastePanelOpen;
    _rerenderActiveState();
}

async function parseRepaste() {
    const text = document.getElementById('repaste-input').value.trim();
    if (!text) { alert('Pega la convocatoria primero.'); return; }
    try {
        const [playersRes, parseRes] = await Promise.all([
            get('/api/players'),
            post('/api/meetup/parse-callup', { text }),
        ]);
        allPlayers = playersRes;
        lastParsedDate = parseRes.date || null;
        parsedPlayers = [
            ...parseRes.titulars.map(p => ({ ...p, excluded: false })),
            ...parseRes.reserves.map(p => ({ ...p, excluded: true })),
        ];
        expandedIdx = null;
        const dateBadge = lastParsedDate
            ? `<div class="date-badge">📅 <span>${_formatDate(lastParsedDate)}</span></div>` : '';
        document.getElementById('repaste-review').innerHTML = `
      ${dateBadge}
      <div id="chip-container"></div>
      <button class="btn btn-green" onclick="confirmRepaste()">✔ Confirmar convocatoria</button>`;
        renderChips();
    } catch (e) { alert('Error al reconocer jugadores: ' + e.message); }
}

async function confirmRepaste() {
    const confirmed = parsedPlayers.filter(p => !p.excluded && p.player_id);
    if (confirmed.length < 2) {
        alert('Necesitas al menos 2 jugadores reconocidos.');
        return;
    }
    const unresolved = parsedPlayers.filter(p => !p.excluded && !p.player_id);
    if (unresolved.length > 0) {
        const names = unresolved.map(p => p.raw).join(', ');
        if (!confirm(`Hay ${unresolved.length} jugador(es) sin resolver: ${names}.\n¿Continuar igualmente?`)) return;
    }
    const newDate = lastParsedDate || activeMatchData.date;
    const dateChanged = newDate !== activeMatchData.date;
    let data;
    try {
        if (dateChanged) {
            await del('/api/meetup/active');
        }
        data = await post('/api/meetup/create', { date: newDate, player_ids: confirmed.map(p => p.player_id) });
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        if (dateChanged || (err instanceof ApiError && err.status === 409)) {
            activeMatchData = null;
            repastePanelOpen = false;
            rosterAddVisible = false;
            manualCreateOpen = false;
            pasteFlowOpen = false;
            _buildFreshFlowHTML();
            showStep('paste');
        }
        return;
    }
    activeMatchData = data;
    repastePanelOpen = false;
    renderState1(activeMatchData);
}

async function cancelMeetup() {
    if (!confirm('¿Seguro que quieres cancelar el partido? Esta acción no se puede deshacer.')) return;
    try {
        await del('/api/meetup/active');
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    activeMatchData = null;
    repastePanelOpen = false;
    rosterAddVisible = false;
    manualCreateOpen = false;
    pasteFlowOpen = false;
    _buildFreshFlowHTML();
    showStep('paste');
}

async function closeMeetup() {
    if (!confirm('¿Seguro que quieres cerrar el triangular? Esta acción no se puede deshacer.')) return;
    try {
        await post('/api/meetup/close');
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    activeMatchData = null;
    repastePanelOpen = false;
    rosterAddVisible = false;
    manualCreateOpen = false;
    pasteFlowOpen = false;
    _buildFreshFlowHTML();
    showStep('paste');
}

// ── TAB: CONVOCATORIAS ────────────────────────────────────────────────────────
async function loadConvocatorias() {
    const el = document.getElementById('convocatorias-content');
    el.innerHTML = '<div class="empty-state">Cargando...</div>';
    let history;
    try {
        history = await get('/api/meetup/history');
    } catch {
        el.innerHTML = '<div class="empty-state">Error al cargar el historial.</div>';
        return;
    }
    if (!history.length) {
        el.innerHTML = '<div class="empty-state">Aún no hay convocatorias cerradas.</div>';
        return;
    }
    el.innerHTML = history.map(item => buildConvocatoriaRow(item, item.date === expandedConvocatoriaDate)).join('');
    if (expandedConvocatoriaDate) await _loadConvocatoriaDetail(expandedConvocatoriaDate);
}

// Toggles one row's expand state in place (arrow + detail panel only) — never
// rebuilds the whole list, so the page never collapses to a "Cargando..."
// placeholder and the browser has no reason to reset scroll position.
async function toggleConvocatoriaRow(date) {
    const previous = expandedConvocatoriaDate;
    if (previous && previous !== date) {
        _setConvocatoriaExpanded(previous, false);
    }
    const opening = previous !== date;
    expandedConvocatoriaDate = opening ? date : null;
    _setConvocatoriaExpanded(date, opening);
    if (opening) await _loadConvocatoriaDetail(date);
}

function copySummary(date) {
    _copyToClipboard(document.getElementById('summary-msg-' + date).textContent);
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
            await navigator.share({ files: [file], text: summaryText || document.getElementById('summary-msg-' + date)?.textContent || '' });
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
                    manualCreateOpen = false;
                    pasteFlowOpen = false;
                    _buildFreshFlowHTML();
                    showStep('paste');
                    return;
                }
                if (err instanceof ApiError && err.status !== 0) {
                    manualCreateOpen = false;
                    pasteFlowOpen = false;
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
async function _callGenerateTeams(teamCount) {
    try {
        return await post('/api/meetup/generate-teams', {
            date: activeMatchData.date, algorithm: 'balanceado', team_count: teamCount,
        });
    } catch (err) {
        throw new Error(err.detail || err.message);
    }
}

// Persist the full roster (SetMeetupPlayers upsert: resets players, clears teams).
async function _saveRoster(playerIds) {
    let data;
    try {
        data = await post('/api/meetup/create', { date: activeMatchData.date, player_ids: playerIds });
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        if (err instanceof ApiError && err.status === 409) bootstrap();
        return;
    }
    activeMatchData = data;
    rosterAddVisible = false;
    rosterSearchQuery = '';
    renderState1(activeMatchData);
}

// Re-render whichever state matches the current activeMatchData.
function _rerenderActiveState() {
    if (!activeMatchData) return;
    if (activeMatchData.teams) renderState2(activeMatchData);
    else renderState1(activeMatchData);
}

function _renderManualCreateContainer() {
    const el = document.getElementById('manual-create-container');
    if (el) el.innerHTML = buildManualCreatePanel(manualCreateOpen);
}

function _renderPasteContainer() {
    const el = document.getElementById('paste-flow-container');
    if (!el) return;
    el.innerHTML = pasteFlowOpen ? `
    <div class="step-label" style="margin-top:12px;">Pega la convocatoria</div>
    <textarea id="callup-input" class="paste-area" placeholder="Lunes 18 Mayo&#10;1. Juande&#10;2. David Quesada&#10;...&#10;&#10;Reservas&#10;- Manu&#10;..."></textarea>
    <button class="btn btn-blue" onclick="parseCallup()">🔍 Reconocer jugadores</button>` : '';
}

function _renderTeamsEditPanel() {
    const teamsBox = document.getElementById('teams-text');
    if (teamsBox) teamsBox.style.display = 'none';
    const sizes = editTeamLetters.map(letter => editTeams[letter].length);
    const tooUneven = Math.max(...sizes) - Math.min(...sizes) > 1;
    const t = activeMatchData.teams;
    const nameByLetter = { A: t.nameA, B: t.nameB, C: t.nameC };
    const emojiByLetter = { A: t.emojiA, B: t.emojiB, C: t.emojiC };

    const row = (p, team) => {
        const hl = editReplacingPlayer && editReplacingPlayer.id === p.id
            ? 'background:#431407;border-color:#ef4444;' : '';
        const nameBtn = `<span style="color:#38bdf8;text-decoration:underline;cursor:pointer;flex:1;"
      onclick="startReplacePlayer('${escAttr(p.id)}','${team}')">${escHtml(p.name)}</span>`;
        const moveButtons = editTeamLetters
            .filter(letter => letter !== team)
            .map(letter => `<button class="btn-sm gray" style="padding:3px 8px;font-size:0.85rem;"
           onclick="moveToOtherTeam('${escAttr(p.id)}','${team}','${letter}')">→ ${escHtml(nameByLetter[letter])}</button>`)
            .join('');
        const removeBtn = `<button class="remove-btn"
      onclick="removeFromEditTeam('${escAttr(p.id)}','${team}')">✕</button>`;
        return `<div class="edit-chip" style="${hl}">${nameBtn}${moveButtons}${removeBtn}</div>`;
    };

    const addBtn = (team) => `<button class="btn-sm gray"
    style="width:100%;margin-top:4px;padding:4px;font-size:0.78rem;"
    onclick="toggleEditAdd('${team}')">${editAddOpenTeam === team ? '✕ Cerrar' : '＋ Añadir'}</button>`;

    const gkSelector = (letter) => {
        const options = editTeams[letter].map(p =>
            `<option value="${escHtml(p.id)}" ${editGoalkeepers[letter] === p.id ? 'selected' : ''}>${escHtml(p.name)}</option>`
        ).join('');
        return `
        <div class="gk-row" style="display:flex;align-items:center;gap:8px;margin-top:6px;">
          <span style="font-size:0.78rem;color:#94a3b8;white-space:nowrap;">🧤 Portero</span>
          <select class="search-box" style="margin:0;" data-team="${letter}" onchange="setEditGoalkeeper('${letter}', this.value)">
            <option value="">Ninguno</option>
            ${options}
          </select>
        </div>`;
    };

    const addPanel = editAddOpenTeam ? `
    <div style="margin-bottom:8px;">
      <div class="step-label" style="font-size:0.65rem;">
        ＋ Añadir a ${escHtml(nameByLetter[editAddOpenTeam])}</div>
      ${buildAddPlayerPanel('edit-add', 'searchEditAdd()')}
    </div>` : '';

    const replaceSearch = editReplacingPlayer ? `
    <div style="background:#1e293b;border:1px solid #3b82f6;border-radius:6px;padding:8px;margin-bottom:8px;">
      <div style="font-size:0.72rem;color:#94a3b8;margin-bottom:5px;">
        Reemplazar a <strong style="color:#fca5a5;">${escHtml(editReplacingPlayer.name)}</strong>:</div>
      <input class="search-box" id="replace-search" type="text" placeholder="Buscar jugador..."
        oninput="renderReplaceSearchResults()">
      <div id="replace-results" class="cand-list"></div>
      <button class="skip-link" style="margin-top:4px;" onclick="cancelReplace()">✕ Cancelar</button>
    </div>` : '';

    const saveBtn = tooUneven
        ? `<button class="btn btn-green" style="margin-top:4px;opacity:0.5;cursor:not-allowed;"
         disabled>💾 Guardar equipos</button>`
        : `<button class="btn btn-green" style="margin-top:4px;"
         onclick="saveTeams()">💾 Guardar equipos</button>`;

    const teamBlock = (letter) => `
        <div style="margin-bottom:10px;">
          <div class="step-label" style="font-size:0.65rem;">${escHtml(emojiByLetter[letter])} ${escHtml(nameByLetter[letter])} (${editTeams[letter].length})</div>
          ${editTeams[letter].map(p => row(p, letter)).join('')}
          ${addBtn(letter)}
          ${gkSelector(letter)}
        </div>`;

    const teamsSection = `<div style="margin-bottom:8px;">${editTeamLetters.map(teamBlock).join('')}</div>`;

    document.getElementById('edit-panel-container').innerHTML = `
    <div class="edit-panel" id="teams-edit-panel">
      <div class="edit-panel-header">
        <div class="step-label" style="margin:0;">✏️ Editar equipos</div>
        <button class="close-x" onclick="toggleTeamsEditPanel()">✕</button>
      </div>
      ${replaceSearch}
      ${teamsSection}
      ${addPanel}
      ${tooUneven ? '<div class="load-warning">⚠ Los equipos no pueden diferir en más de 1 jugador</div>' : ''}
      ${saveBtn}
    </div>
  `;
    if (editAddOpenTeam) {
        const input = document.getElementById('edit-add-search');
        input.value = editAddQuery;
        input.focus();
        searchEditAdd();
    }
}

// Flips one row's arrow icon and clears its detail panel on collapse.
// Does nothing to the rest of the list — no full-list rebuild, no scroll reset.
function _setConvocatoriaExpanded(date, expanded) {
    const arrow = document.getElementById('convocatoria-arrow-' + date);
    if (arrow) arrow.textContent = expanded ? '▾' : '▸';
    if (!expanded) {
        const detail = document.getElementById('convocatoria-detail-' + date);
        if (detail) detail.innerHTML = '';
    }
}

async function _loadConvocatoriaDetail(date) {
    const container = document.getElementById('convocatoria-detail-' + date);
    if (!container) return;
    container.innerHTML = '<div class="empty-state">Cargando...</div>';
    try {
        const { message } = await get(`/api/match/${encodeURIComponent(date)}/summary`);
        container.innerHTML = buildConvocatoriaDetail(date, message);
    } catch {
        container.innerHTML = '<div class="empty-state">Error al cargar el resumen.</div>';
    }
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
    setEditGoalkeeper,
    startReplacePlayer,
    pickReplacement,
    cancelReplace,
    removeFromEditTeam,
    toggleEditAdd,
    searchEditAdd,
    pickEditAdd,
    saveTeams,
    toggleRepaste,
    parseRepaste,
    confirmRepaste,
    createNextMeetup,
    toggleManualCreate,
    confirmManualCreate,
    togglePasteFlow,
    cancelMeetup,
    closeMeetup,
    copySummary,
    downloadStats,
    shareStats,
    loadConvocatorias,
    toggleConvocatoriaRow,
    pickCandidate,
    excludePlayer,
    closePanel,
    openEditMode,
    showStep,
    renderReplaceSearchResults,
    renderSearchResults,
    toggleChipPanel,
    includeChip,
    removeFromRoster,
    toggleRosterAdd,
    searchRosterAdd,
    pickRosterAdd,
    toggleDateLocationEdit,
    saveDateLocationEdit,
});

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/manage' })
        .catch(err => console.warn('SW registration failed:', err));
}

bootstrap();
