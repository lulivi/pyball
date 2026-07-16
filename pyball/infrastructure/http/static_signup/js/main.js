import { get, post } from '/js/api.js';
import { buildCodeScreen, buildMainScreen, buildChangeCodeScreen } from './views.js';

const app = document.getElementById('app');

async function bootstrap() {
    let me;
    try {
        me = await _fetchMeOrNull();
    } catch (err) {
        app.innerHTML = '<div class="card">Error al conectar con el servidor.</div>';
        return;
    }
    if (me === null) {
        showCodeScreen();
        return;
    }
    await showMainScreen(me.name);
}

function showCodeScreen(errorMsg) {
    app.innerHTML = buildCodeScreen(errorMsg);
    document.getElementById('verify-btn').addEventListener('click', verifyCode);
    document.getElementById('code-input').focus();
}

async function verifyCode() {
    const code = document.getElementById('code-input').value.trim().toUpperCase();
    if (!code) return;
    try {
        const player = await post('/api/signup/verify', { code });
        await showMainScreen(player.name);
    } catch (err) {
        showCodeScreen('Código incorrecto.');
    }
}

async function showMainScreen(playerName) {
    let meetup;
    try {
        meetup = await get('/api/signup/meetup');
    } catch (err) {
        app.innerHTML = '<div class="card">No hay convocatoria activa por ahora.</div>';
        return;
    }
    app.innerHTML = buildMainScreen(playerName, meetup);
    const joinBtn = document.getElementById('join-btn');
    if (joinBtn) joinBtn.addEventListener('click', () => joinOrLeave('/api/signup/join', playerName));
    const leaveBtn = document.getElementById('leave-btn');
    if (leaveBtn) leaveBtn.addEventListener('click', () => joinOrLeave('/api/signup/leave', playerName));
    document.getElementById('change-code-btn').addEventListener('click', showChangeCodeScreen);
    document.getElementById('logout-btn').addEventListener('click', logout);
}

async function joinOrLeave(path, playerName) {
    try {
        await post(path, {});
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    await showMainScreen(playerName);
}

function showChangeCodeScreen(errorMsg) {
    app.innerHTML = buildChangeCodeScreen(errorMsg);
    document.getElementById('save-code-btn').addEventListener('click', saveNewCode);
    document.getElementById('cancel-code-btn').addEventListener('click', bootstrap);
}

async function saveNewCode() {
    const currentCode = document.getElementById('current-code-input').value.trim().toUpperCase();
    const newCode = document.getElementById('new-code-input').value.trim().toUpperCase();
    if (!currentCode || !newCode) return;
    try {
        await post('/api/signup/change-code', { current_code: currentCode, new_code: newCode });
    } catch (err) {
        showChangeCodeScreen('Código actual incorrecto.');
        return;
    }
    alert('Código actualizado.');
    bootstrap();
}

async function logout() {
    await post('/api/signup/logout', {});
    showCodeScreen();
}

// ── Private helpers ───────────────────────────────────────────────────────────

// A dedicated fetch for the initial identity check: a 401 here just means "no
// player identified yet", the expected state for a first-time visitor — unlike
// every other call in this file, it must bypass the shared client's global 401
// handler (renderUnauthorized in /js/api.js), which assumes 401 always means a
// revoked site-level token and wipes the whole page before this screen can render.
async function _fetchMeOrNull() {
    const res = await fetch('/api/signup/me');
    if (res.status === 401) return null;
    if (!res.ok) throw new Error(`HTTP ${res.status}`);
    return res.json();
}

bootstrap();
