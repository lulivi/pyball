import {
    ctx, store, getGoals, clearSaved, applyTeamColors, saveTeamsSnapshot, persistStateNow,
} from './state.js';
import { post } from '../api.js';
import { startAudio, requestWakeLock, releaseWakeLock, clampMinutes } from './timer.js';

let _saveArmTimer = null;

export function setTab(tabName) {
    clearTimeout(_saveArmTimer);
    store.set({ activeTab: tabName, saveArmed: false, saveError: null });
}

export function startTimer() {
    if (store.get().timerRunning) return;
    startAudio();
    store.set({
        timerRunning: true, timerStartedAt: Date.now(), lastCycleFired: 0, audioArmed: true,
    });
    requestWakeLock();
}

// Unlock audio from a user gesture after a reload re-locked it — wired to the
// muted pill, the "Activar sonido" button, and a one-shot page-wide tap.
export function armAudio() {
    if (store.get().audioArmed) return;
    startAudio();
    store.set({ audioArmed: true });
}

export function resetTimer() {
    if (!store.get().timerRunning) return;
    store.set({ timerRunning: false, timerStartedAt: null, lastCycleFired: 0 });
    if (!store.get().hourWarnEnabled) releaseWakeLock();
}

export function setTimerMinutes(delta) {
    if (store.get().timerRunning) return;
    store.set({ timerMinutes: clampMinutes(store.get().timerMinutes + delta) });
}

export function toggleHourWarn() {
    const enabling = !store.get().hourWarnEnabled;
    if (enabling) {
        startAudio();
        requestWakeLock();
        store.set({ hourWarnEnabled: true, hourWarnLastFired: null, audioArmed: true });
        return;
    }
    store.set({ hourWarnEnabled: false });
    if (!store.get().timerRunning) releaseWakeLock();
}

export function setHourWarnMinutes(delta) {
    if (store.get().hourWarnEnabled) return;
    store.set({ hourWarnMinutes: clampMinutes(store.get().hourWarnMinutes + delta) });
}

export function selectPlayer(playerName, teamId) {
    const s = store.get();
    if (s.currentStep === 1) {
        store.set({ tempScorer: playerName, tempScorerTeam: teamId, currentStep: 2 });
    } else {
        registerGoal(playerName);
    }
}

export function registerGoal(assistantName) {
    const s = store.get();
    store.set({
        events: [{
            type: 'gol',
            scorer: s.tempScorer,
            assistant: assistantName || null,
            team: s.tempScorerTeam,
            timestamp: _now(),
        }, ...s.events],
        currentStep: 1, tempScorer: null, tempScorerTeam: null,
    });
}

export function registerOwnGoal() {
    const s = store.get();
    store.set({
        events: [{
            scorer: s.tempScorer,
            assistant: null,
            team: s.tempScorerTeam === 'A' ? 'B' : 'A',
            timestamp: _now(),
            is_own_goal: true,
        }, ...s.events],
        currentStep: 1, tempScorer: null, tempScorerTeam: null,
    });
}

export function cancelGoal() {
    store.set({ currentStep: 1, tempScorer: null, tempScorerTeam: null });
}

export function deleteEvent(i) {
    const events = [...store.get().events];
    events.splice(i, 1);
    store.set({ events, editingEvent: null });
}

export function togglePicker(eventIndex, field) {
    const cur = store.get().editingEvent;
    const already = cur !== null && cur.eventIndex === eventIndex && cur.field === field;
    store.set({ editingEvent: already ? null : { eventIndex, field } });
}

export function updateEventPlayer(eventIndex, field, playerName) {
    const events = store.get().events.map((e, i) => {
        if (i !== eventIndex) return e;
        const updated = { ...e, [field]: playerName };
        if (field === 'scorer' && e.assistant === playerName) updated.assistant = null;
        return updated;
    });
    store.set({ events, editingEvent: null });
}

export function clearAssist(eventIndex) {
    const events = store.get().events.map(
        (e, i) => (i === eventIndex ? { ...e, assistant: null } : e)
    );
    store.set({ events, editingEvent: null });
}

export function requestSave() {
    const s = store.get();
    if (s.saving) return;
    if (!s.saveArmed) {
        store.set({ saveArmed: true, saveError: null });
        clearTimeout(_saveArmTimer);
        _saveArmTimer = setTimeout(() => store.set({ saveArmed: false }), 4000);
        return;
    }
    clearTimeout(_saveArmTimer);
    store.set({ saveArmed: false, saving: true, saveError: null });
    if (ctx.isEditMode) _submitEdit();
    else _submitFinish();
}

async function _submitFinish() {
    try {
        const data = await post('/api/match/finish', _payload());
        if (data.next_round) {
            _continueToNextRound(data.next_round);
            return;
        }
        resetTimer();
        if (store.get().hourWarnEnabled) toggleHourWarn();
        clearSaved();
        _renderDone('✅ Partido guardado', 'Vuelve a /manage<br>para el próximo partido.');
    } catch (err) {
        store.set({ saving: false, saveError: _errMsg(err) });
    }
}

async function _submitEdit() {
    try {
        await post('/api/match/' + encodeURIComponent(ctx.meetupDate) + '/edit', _payload());
        _renderDone('✅ Corrección guardada', 'Resultado corregido correctamente.');
    } catch (err) {
        store.set({ saving: false, saveError: _errMsg(err) });
    }
}

function _continueToNextRound(nextRound) {
    ctx.teamA = nextRound.teamA;
    ctx.teamB = nextRound.teamB;
    ctx.nameA = nextRound.nameA;
    ctx.nameB = nextRound.nameB;
    applyTeamColors(nextRound.colorA, nextRound.colorTextA, nextRound.colorB, nextRound.colorTextB);
    saveTeamsSnapshot({
        colorA: nextRound.colorA, colorB: nextRound.colorB,
        colorTextA: nextRound.colorTextA, colorTextB: nextRound.colorTextB,
    });
    store.set({
        events: [], currentStep: 1, tempScorer: null, tempScorerTeam: null,
        editingEvent: null, saveArmed: false, saving: false, saveError: null,
    });
    // Redundant with persistTo's subscriber (store.set above already wrote STATE_KEY);
    // kept as an explicit invariant that the new round is persisted before any await.
    persistStateNow();
}

function _payload() {
    return {
        meetup_date: ctx.meetupDate,
        events: [...store.get().events].reverse(),
        finalScore: { A: getGoals('A'), B: getGoals('B') },
    };
}

function _renderDone(banner, message) {
    document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="success-banner">${banner}</div>
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">${message}</div>
            </div>`;
}

function _errMsg(err) {
    return err.status === 0
        ? '❌ Error de red. Revisa la conexión e inténtalo de nuevo.'
        : `❌ Error del servidor: ${err.detail || err.message}`;
}

function _now() {
    return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}
