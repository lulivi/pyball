import { get, ApiError } from '../api.js';
import { loadPersisted } from '../store.js';
import {
    ctx, store, enablePersistence, persistStateNow, saveTeamsSnapshot, clearSaved,
    applyTeamColors, STATE_KEY, TEAMS_KEY,
} from './state.js';
import * as actions from './actions.js';
import {
    completedCycles, clampMinutes, playCue, requestWakeLock, startAudio,
    remainingMs, formatCountdown, hourWarnFireAt, playHourCue,
} from './timer.js';
import {
    renderApp, renderNoMatch, renderOffline, renderStaleMatchChoice, formatMatchDate,
} from './views.js';

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
            if (navigator.onLine) loadActiveMatch(true);
            return;
        }
        renderStaleMatchChoice(
            formatMatchDate(savedTeams.meetupDate),
            () => adoptSaved(savedState, savedTeams),
            () => { clearSaved(); startFreshFlow(); },
        );
        return;
    }

    startFreshFlow();
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
    store.set({
        ...savedState,
        ...normalizeTimer(savedState),
        audioArmed: false,
        editingEvent: null, saveArmed: false, saving: false, saveError: null,
    });
    if (store.get().timerRunning || store.get().hourWarnEnabled) {
        requestWakeLock();
        // A reload re-locks audio; the next real tap anywhere unlocks it.
        // Use 'click' (not 'pointerdown') — Chromium/Brave on Android only
        // grants the audio unlock from click/pointerup, not pointerdown.
        document.addEventListener('click', () => actions.armAudio(), { once: true });
    }
}

function startFreshFlow() {
    const params = new URLSearchParams(window.location.search);
    const teamAParam = params.get('teamA');
    const teamBParam = params.get('teamB');
    if (!teamAParam || !teamBParam) {
        waitForMatch();
        return;
    }

    ctx.meetupDate = params.get('date') || '';
    ctx.nameA = params.get('nameA') || 'A';
    ctx.nameB = params.get('nameB') || 'B';
    ctx.teamA = teamAParam.split(',');
    ctx.teamB = teamBParam.split(',');
    saveTeamsSnapshot({
        colorA: params.get('colorA'), colorB: params.get('colorB'),
        colorTextA: params.get('colorTextA'), colorTextB: params.get('colorTextB'),
    });
    persistStateNow();
    renderApp();
}

async function waitForMatch() {
    if (!navigator.onLine) {
        renderOffline();
        window.addEventListener('online', () => waitForMatch(), { once: true });
        return;
    }

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
        if (!navigator.onLine) {
            renderOffline();
            window.addEventListener('online', () => waitForMatch(), { once: true });
            return;
        }
        try {
            applyMatchData(await get('/api/match/active'));
            return;
        } catch (err) {
            if (err instanceof ApiError && err.status === 404) {
                renderNoMatch();
                return;
            }
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
            actions.resetTimer();
            if (store.get().hourWarnEnabled) actions.toggleHourWarn();
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
    persistStateNow();
    renderApp();
}

function normalizeTimer(savedState) {
    return {
        timerRunning: savedState.timerRunning ?? false,
        timerMinutes: clampMinutes(savedState.timerMinutes ?? 6),
        timerStartedAt: savedState.timerStartedAt ?? null,
        lastCycleFired: savedState.lastCycleFired ?? 0,
        hourWarnEnabled: savedState.hourWarnEnabled ?? false,
        hourWarnMinutes: clampMinutes(savedState.hourWarnMinutes ?? 5),
        hourWarnLastFired: savedState.hourWarnLastFired ?? null,
    };
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
    requestSave: actions.requestSave,
    startTimer: actions.startTimer,
    resetTimer: actions.resetTimer,
    setTimerMinutes: actions.setTimerMinutes,
    toggleHourWarn: actions.toggleHourWarn,
    setHourWarnMinutes: actions.setHourWarnMinutes,
    armAudio: actions.armAudio,
    playCue,
    playHourCue,
    waitForMatch,
});

store.subscribe(() => renderApp());
enablePersistence();

document.addEventListener('click', () => {
    if (store.get().editingEvent !== null) store.set({ editingEvent: null });
});

document.addEventListener('visibilitychange', () => {
    if (document.visibilityState === 'visible' && (store.get().timerRunning || store.get().hourWarnEnabled)) {
        requestWakeLock();
        if (store.get().audioArmed) startAudio();
        renderApp();
    }
});

if ('serviceWorker' in navigator) {
    navigator.serviceWorker.register('/sw.js', { scope: '/match' })
        .catch(err => console.warn('SW registration failed:', err));
}

function timerTick() {
    const s = store.get();
    const now = Date.now();

    if (s.hourWarnEnabled) {
        const fireAt = hourWarnFireAt(now, s.hourWarnMinutes);
        if (fireAt && fireAt !== s.hourWarnLastFired) {
            store.set({ hourWarnLastFired: fireAt });
            playHourCue();
            flashApp();
        }
    }

    if (!s.timerRunning) return;
    const done = completedCycles(s.timerStartedAt, s.timerMinutes, now);
    if (done > s.lastCycleFired) {
        store.set({ lastCycleFired: done });
        playCue();
        flashApp();
        return;
    }
    // Surgically refresh just the countdown text nodes — a full renderApp()
    // every second would rebuild the scoring grid and swallow taps.
    const label = formatCountdown(remainingMs(s.timerStartedAt, s.timerMinutes, now));
    const pill = document.getElementById('timer-pill-time');
    if (pill) pill.textContent = label;
    const big = document.getElementById('timer-countdown-value');
    if (big) big.textContent = label;
}

let _flashing = false;

function flashApp() {
    if (_flashing) return;
    _flashing = true;
    const overlay = document.createElement('div');
    overlay.id = 'timer-flash-overlay';
    document.body.appendChild(overlay);
    setTimeout(() => {
        overlay.remove();
        _flashing = false;
    }, 1200);
}

setInterval(timerTick, 1000);

initializeApp();
