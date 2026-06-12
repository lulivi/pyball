import { get, ApiError } from '../api.js';
import { loadPersisted } from '../store.js';
import {
    ctx, store, enablePersistence, saveTeamsSnapshot, clearSaved,
    applyTeamColors, STATE_KEY, TEAMS_KEY,
} from './state.js';
import * as actions from './actions.js';
import { renderApp, renderNoMatch, formatMatchDate } from './views.js';

function initializeApp() {
    const params = new URLSearchParams(window.location.search);
    applyTeamColors(
        params.get('colorA'), params.get('colorTextA'),
        params.get('colorB'), params.get('colorTextB'),
    );

    if (params.get('edit') === '1') {
        ctx.isEditMode = true;
        const editDate = params.get('date') || '';
        if (editDate) loadEditMode(editDate);
        else renderNoMatch();
        return;
    }

    const savedState = loadPersisted(STATE_KEY);
    const savedTeams = loadPersisted(TEAMS_KEY);
    const urlDate = params.get('date') || '';

    if (savedState && savedTeams) {
        if (!urlDate || savedTeams.meetupDate === urlDate) {
            adoptSaved(savedState, savedTeams);
            loadActiveMatch(true); // silent: on network error keep running offline
            return;
        }
        const oldDate = formatMatchDate(savedTeams.meetupDate);
        if (!confirm(`Hay un partido del ${oldDate} sin guardar.\n¿Empezar el de hoy y descartar el anterior?`)) {
            adoptSaved(savedState, savedTeams);
            return;
        }
        clearSaved();
    }

    const teamAParam = params.get('teamA');
    const teamBParam = params.get('teamB');
    if (!teamAParam || !teamBParam) {
        waitForMatch();
        return;
    }

    ctx.meetupDate = urlDate;
    ctx.nameA = params.get('nameA') || 'A';
    ctx.nameB = params.get('nameB') || 'B';
    ctx.teamA = teamAParam.split(',');
    ctx.teamB = teamBParam.split(',');
    saveTeamsSnapshot({
        colorA: params.get('colorA'), colorB: params.get('colorB'),
        colorTextA: params.get('colorTextA'), colorTextB: params.get('colorTextB'),
    });
    renderApp();
}

function adoptSaved(savedState, savedTeams) {
    ctx.teamA = savedTeams.teamA;
    ctx.teamB = savedTeams.teamB;
    ctx.nameA = savedTeams.nameA || 'A';
    ctx.nameB = savedTeams.nameB || 'B';
    ctx.meetupDate = savedTeams.meetupDate;
    applyTeamColors(
        savedTeams.colorA, savedTeams.colorTextA,
        savedTeams.colorB, savedTeams.colorTextB,
    );
    store.set({ ...savedState, editingEvent: null });
}

async function waitForMatch() {
    let attempts = 0;

    const showConnecting = () => {
        const msg = attempts >= 3
            ? 'Está tardando más de lo esperado...'
            : 'Conectando con el servidor...';
        document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">${msg}</div>
                <div class="spinner"></div>
            </div>`;
    };

    showConnecting();

    while (true) {
        try {
            applyMatchData(await get('/api/match/active'));
            return;
        } catch (err) {
            if (err instanceof ApiError && err.status === 404) {
                renderNoMatch();
                return;
            }
            // network error or 5xx — retry
        }
        attempts++;
        showConnecting();
        await new Promise(resolve => setTimeout(resolve, 5000));
    }
}

async function loadActiveMatch(silent = false) {
    try {
        applyMatchData(await get('/api/match/active'));
    } catch (err) {
        if (err instanceof ApiError && err.status === 404) {
            clearSaved();
            renderNoMatch();
            return;
        }
        if (!silent) renderNoMatch();
    }
}

async function loadEditMode(date) {
    try {
        const data = await get('/api/match/' + encodeURIComponent(date) + '/events');
        ctx.meetupDate = data.date;
        ctx.nameA = data.nameA;
        ctx.nameB = data.nameB;
        ctx.teamA = data.teamA;
        ctx.teamB = data.teamB;
        applyTeamColors(data.colorA, data.colorTextA, data.colorB, data.colorTextB);
        store.set({ events: data.events, editingEvent: null });
    } catch {
        renderNoMatch();
    }
}

function applyMatchData(data) {
    ctx.meetupDate = data.date;
    ctx.nameA = data.nameA;
    ctx.nameB = data.nameB;
    ctx.teamA = data.teamA;
    ctx.teamB = data.teamB;
    applyTeamColors(data.colorA, data.colorTextA, data.colorB, data.colorTextB);
    saveTeamsSnapshot({
        colorA: data.colorA, colorB: data.colorB,
        colorTextA: data.colorTextA, colorTextB: data.colorTextB,
    });
    renderApp();
}

// Inline onclick="" attributes in the rendered HTML resolve against window:
Object.assign(window, {
    setTab: actions.setTab,
    selectPlayer: actions.selectPlayer,
    registerGoal: actions.registerGoal,
    registerOwnGoal: actions.registerOwnGoal,
    cancelGoal: actions.cancelGoal,
    deleteEvent: actions.deleteEvent,
    togglePicker: actions.togglePicker,
    updateEventPlayer: actions.updateEventPlayer,
    clearAssist: actions.clearAssist,
    finishMatch: actions.finishMatch,
    editMatch: actions.editMatch,
    waitForMatch,
});

store.subscribe(() => renderApp());
enablePersistence();

document.addEventListener('click', () => {
    if (store.get().editingEvent !== null) store.set({ editingEvent: null });
});

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/match' })
        .catch(err => console.warn('SW registration failed:', err));
}

initializeApp();
