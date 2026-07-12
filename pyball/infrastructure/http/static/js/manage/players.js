import { get, post, del } from '../api.js';
import { escHtml, escAttr } from './views.js';

// ── STATE ────────────────────────────────────────────────────────────────
let players = [];          // [{id, name, group, position}, ...]
let createOpen = false;
let editingId = null;      // id of the row currently in edit mode, or null

const POSITION_LABELS = {
    portero: 'Portero',
    defensa: 'Defensa',
    centrocampista: 'Centrocampista',
    delantero: 'Delantero',
};

// ── TAB: JUGADORES ──────────────────────────────────────────────────────
async function loadJugadores() {
    const el = document.getElementById('tab-jugadores');
    el.innerHTML = '<div class="empty-state">Cargando...</div>';
    try {
        players = await get('/api/players');
    } catch (e) {
        el.innerHTML = '<div class="empty-state">Error al cargar jugadores.</div>';
        return;
    }
    render();
}

function render() {
    const sorted = [...players].sort((a, b) => a.name.localeCompare(b.name, 'es'));
    const rows = sorted.map(p => editingId === p.id ? buildEditRow(p) : buildRow(p)).join('');
    const createPanel = createOpen ? buildCreatePanel() : '';
    document.getElementById('tab-jugadores').innerHTML = `
    <div class="step-label">Jugadores (${players.length})</div>
    <input class="search-box" id="player-search" type="text" placeholder="Buscar jugador..."
      oninput="filterPlayers()">
    <div id="player-list">${rows}</div>
    <button class="btn-sm gray" style="margin-top:6px;" onclick="togglePlayerCreate()">
      ${createOpen ? '✕ Cerrar' : '+ Nuevo jugador'}</button>
    ${createPanel}
  `;
}

function filterPlayers() {
    const q = document.getElementById('player-search').value.trim().toLowerCase();
    const rowsEl = document.getElementById('player-list');
    const sorted = [...players].sort((a, b) => a.name.localeCompare(b.name, 'es'));
    const visible = q ? sorted.filter(p => p.name.toLowerCase().includes(q)) : sorted;
    rowsEl.innerHTML = visible.map(p => editingId === p.id ? buildEditRow(p) : buildRow(p)).join('');
}

function buildRow(p) {
    const posLabel = p.position ? POSITION_LABELS[p.position] : '—';
    const groupLabel = p.group === 'regular' ? 'Regular' : 'Suplente';
    return `
    <div class="edit-chip">
      <span style="flex:1;">${escHtml(p.name)}</span>
      <span class="cand-score">${groupLabel} · ${posLabel}</span>
      <button class="btn-sm gray" style="padding:3px 8px;" data-pid="${escHtml(p.id)}"
        onclick="togglePlayerEdit(this.dataset.pid)">✏️</button>
      <button class="remove-btn" data-pid="${escHtml(p.id)}"
        onclick="deletePlayerRow(this.dataset.pid)">✕</button>
    </div>`;
}

function buildFieldsForm(idPrefix, values) {
    const groupPill = (value, label) => `
      <div class="pill${values.group === value ? ' sel' : ''}" data-value="${value}"
        onclick="selectField('${idPrefix}-group', this)">${label}</div>`;
    const posPill = (value, label) => `
      <div class="pill${values.position === value ? ' sel-pos' : ''}" data-value="${value || ''}"
        onclick="selectField('${idPrefix}-position', this)">${label}</div>`;
    return `
    <input class="search-box" id="${idPrefix}-name" type="text" placeholder="Nombre"
      value="${escHtml(values.name || '')}">
    <div class="field-label">Grupo</div>
    <div class="pill-row" id="${idPrefix}-group" data-selected="${values.group}">
      ${groupPill('regular', 'Regular')}${groupPill('substitute', 'Suplente')}
    </div>
    <div class="field-label">Posición</div>
    <div class="pill-row" id="${idPrefix}-position" data-selected="${values.position || ''}">
      ${posPill('', 'Ninguna')}${posPill('portero', 'Portero')}${posPill('defensa', 'Defensa')}
      ${posPill('centrocampista', 'Centro')}${posPill('delantero', 'Delantero')}
    </div>`;
}

function buildCreatePanel() {
    return `
    <div class="edit-panel">
      ${buildFieldsForm('create', { group: 'substitute', position: '' })}
      <button class="btn btn-green" style="margin-top:8px;" onclick="createPlayer()">Crear</button>
    </div>`;
}

function buildEditRow(p) {
    return `
    <div class="edit-panel">
      ${buildFieldsForm('edit', p)}
      <div class="edit-actions" style="margin-top:8px;">
        <button class="btn-sm green" data-pid="${escHtml(p.id)}"
          onclick="savePlayerEdit(this.dataset.pid)">Guardar</button>
        <button class="btn-sm gray" onclick="togglePlayerEdit(null)">Cancelar</button>
      </div>
    </div>`;
}

function selectField(containerId, el) {
    const container = document.getElementById(containerId);
    container.dataset.selected = el.dataset.value;
    Array.from(container.children).forEach(child => child.classList.remove('sel', 'sel-pos'));
    el.classList.add(containerId.endsWith('-position') ? 'sel-pos' : 'sel');
}

async function togglePlayerCreate() {
    createOpen = !createOpen;
    render();
}

function togglePlayerEdit(id) {
    editingId = id;
    render();
}

async function createPlayer() {
    const name = document.getElementById('create-name').value.trim();
    if (!name) { alert('El nombre no puede estar vacío.'); return; }
    const group = document.getElementById('create-group').dataset.selected;
    const position = document.getElementById('create-position').dataset.selected || null;
    try {
        const created = await post('/api/players', { name, group, position });
        players.push(created);
    } catch (err) {
        alert('Error al crear jugador: ' + (err.detail || err.message));
        return;
    }
    createOpen = false;
    render();
}

async function savePlayerEdit(id) {
    const name = document.getElementById('edit-name').value.trim();
    if (!name) { alert('El nombre no puede estar vacío.'); return; }
    const group = document.getElementById('edit-group').dataset.selected;
    const position = document.getElementById('edit-position').dataset.selected || null;
    let updated;
    try {
        updated = await post(`/api/players/${id}/edit`, { name, group, position });
    } catch (err) {
        alert('Error al guardar: ' + (err.detail || err.message));
        return;
    }
    players = players.map(p => p.id === id ? updated : p);
    editingId = null;
    render();
}

async function deletePlayerRow(id) {
    const player = players.find(p => p.id === id);
    if (!player) return;
    if (!confirm(`¿Borrar a ${player.name}? Esta acción no se puede deshacer.`)) return;
    try {
        await del(`/api/players/${id}`);
    } catch (err) {
        alert('Error al borrar: ' + (err.detail || err.message));
        return;
    }
    players = players.filter(p => p.id !== id);
    render();
}

Object.assign(window, {
    loadJugadores,
    togglePlayerCreate,
    createPlayer,
    togglePlayerEdit,
    savePlayerEdit,
    deletePlayerRow,
    filterPlayers,
    selectField,
});
