import { ctx, store, getGoals, clearSaved, applyTeamColors, saveTeamsSnapshot } from './state.js';
import { post } from '../api.js';

export function setTab(tabName) {
    store.set({ activeTab: tabName });
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

export async function finishMatch() {
    if (!confirm('¿Seguro que quieres guardar el partido y enviarlo al Bot?')) return;
    const saveBtn = document.getElementById('save-btn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Enviando datos...';
    try {
        const data = await post('/api/match/finish', {
            meetup_date: ctx.meetupDate,
            events: [...store.get().events].reverse(),
            finalScore: { A: getGoals('A'), B: getGoals('B') },
        });
        if (data.next_round) {
            _continueToNextRound(data.next_round);
            return;
        }
        clearSaved();
        document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="success-banner">✅ Partido guardado y enviado a Telegram</div>
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">Abre el enlace desde<br>Telegram para el próximo partido.</div>
            </div>`;
    } catch (err) {
        if (err.status === 0) {
            alert('❌ Error de red. Revisa la conexión e inténtalo de nuevo.');
        } else {
            alert(`❌ Error del servidor: ${err.detail || err.message}`);
        }
        saveBtn.disabled = false;
        saveBtn.textContent = '💾 CONFIRMAR Y GUARDAR PARTIDO';
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
    store.set({ events: [], currentStep: 1, tempScorer: null, tempScorerTeam: null, editingEvent: null });
}

export async function editMatch() {
    if (!confirm('¿Guardar la corrección y reenviar el resumen a Telegram?')) return;
    await _submit('/api/match/' + encodeURIComponent(ctx.meetupDate) + '/edit', {
        success: '✅ Corrección guardada y reenviada a Telegram',
        message: 'Resultado corregido correctamente.',
        idleLabel: '💾 GUARDAR CORRECCIÓN',
        clear: false,
    });
}

async function _submit(url, { success, message, idleLabel, clear }) {
    const saveBtn = document.getElementById('save-btn');
    saveBtn.disabled = true;
    saveBtn.textContent = 'Enviando datos...';
    try {
        await post(url, {
            meetup_date: ctx.meetupDate,
            events: [...store.get().events].reverse(),
            finalScore: { A: getGoals('A'), B: getGoals('B') },
        });
        if (clear) clearSaved();
        document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="success-banner">${success}</div>
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">${message}</div>
            </div>`;
    } catch (err) {
        if (err.status === 0) {
            alert('❌ Error de red. Revisa la conexión e inténtalo de nuevo.');
        } else {
            alert(`❌ Error del servidor: ${err.detail || err.message}`);
        }
        saveBtn.disabled = false;
        saveBtn.textContent = idleLabel;
    }
}

function _now() {
    return new Date().toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
}
