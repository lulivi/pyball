import { ctx, store, getGoals } from './state.js';
import { remainingMs, formatCountdown } from './timer.js';

function escHtml(s) {
    return s.replace(/&/g, '&amp;').replace(/</g, '&lt;').replace(/>/g, '&gt;');
}

function renderPickerDropdown(eventIndex, field) {
    const state = store.get();
    const e = state.events[eventIndex];
    const scorerTeam = e.is_own_goal ? (e.team === 'A' ? ctx.teamB : ctx.teamA) : (e.team === 'A' ? ctx.teamA : ctx.teamB);
    const opts = field === 'scorer' ? scorerTeam : (e.team === 'A' ? ctx.teamA : ctx.teamB).filter(p => p !== e.scorer);

    let html = `<div class="picker-dropdown" onclick="event.stopPropagation()">`;
    opts.forEach(p => {
        const pSafe = p.replace(/'/g, "\\'");
        const sel = field === 'scorer' ? p === e.scorer : p === e.assistant;
        html += `<div class="picker-item ${sel ? 'selected' : ''}" onclick="event.stopPropagation();updateEventPlayer(${eventIndex},'${field}','${pSafe}')">${escHtml(p)}</div>`;
    });

    if (field === 'assistant') {
        html += `<div class="picker-item no-assist ${e.assistant === null ? 'selected' : ''}" onclick="event.stopPropagation();clearAssist(${eventIndex})">Sin asistente</div>`;
    }
    html += `</div>`;
    return html;
}

function renderEventRow(e, i) {
    const state = store.get();
    const teamClass = e.team === 'A' ? 'team-a' : 'team-b';
    const scorerOpen = state.editingEvent?.eventIndex === i && state.editingEvent?.field === 'scorer';

    if (e.is_own_goal) {
        const scorerChip = `
                <button class="player-chip ${scorerOpen ? 'active' : ''}" onclick="event.stopPropagation();togglePicker(${i},'scorer')">
                    <span class="truncate-text">${escHtml(e.scorer)}</span> <span class="chevron">${scorerOpen ? '▲' : '▼'}</span>
                </button>`;
        return `
                <div class="event-log ${teamClass} ${scorerOpen ? 'editing' : ''}" onclick="event.stopPropagation()" style="display:flex;align-items:center;gap:4px;">
                    <span class="event-time" style="flex: 0 0 42px; text-align:center;">${escHtml(e.timestamp)}</span>
                    <span style="flex: 1; min-width: 0; display: flex; justify-content: center;">${scorerChip}</span>
                    <span style="flex: 1; min-width: 0; display: flex; justify-content: center;">
                        <span class="own-goal-badge">En propia 🔴</span>
                    </span>
                    <button class="delete-btn" style="flex: 0 0 35px; display: flex; justify-content: center; align-items: center;" onclick="event.stopPropagation();deleteEvent(${i})">🗑</button>
                    ${scorerOpen ? renderPickerDropdown(i, 'scorer') : ''}
                </div>`;
    }

    const assistOpen = state.editingEvent?.eventIndex === i && state.editingEvent?.field === 'assistant';

    const scorerChip = `
            <button class="player-chip ${scorerOpen ? 'active' : ''}" onclick="event.stopPropagation();togglePicker(${i},'scorer')">
                <span class="truncate-text">${escHtml(e.scorer)}</span> <span class="chevron">${scorerOpen ? '▲' : '▼'}</span>
            </button>`;

    const assistLabel = e.assistant ? e.assistant : 'Sin asistente';
    const assistChip = `
            <button class="player-chip ${assistOpen ? 'active' : ''}" onclick="event.stopPropagation();togglePicker(${i},'assistant')">
                <span class="truncate-text">${escHtml(assistLabel)}</span> <span class="chevron">${assistOpen ? '▲' : '▼'}</span>
            </button>`;

    return `
            <div class="event-log ${teamClass} ${scorerOpen || assistOpen ? 'editing' : ''}" onclick="event.stopPropagation()" style="display:flex;align-items:center;gap:4px;">
                <span class="event-time" style="flex: 0 0 42px; text-align:center;">${escHtml(e.timestamp)}</span>
                <span style="flex: 1; min-width: 0; display: flex; justify-content: center;">${scorerChip}</span>
                <span style="flex: 1; min-width: 0; display: flex; justify-content: center;">${assistChip}</span>
                <button class="delete-btn" style="flex: 0 0 35px; display: flex; justify-content: center; align-items: center;" onclick="event.stopPropagation();deleteEvent(${i})">🗑</button>

                ${scorerOpen ? renderPickerDropdown(i, 'scorer') : ''}
                ${assistOpen ? renderPickerDropdown(i, 'assistant') : ''}
            </div>
        `;
}

function renderTimerTab() {
    const state = store.get();

    if (state.timerRunning) {
        const ms = remainingMs(state.timerStartedAt, state.timerMinutes, Date.now());
        const soundBtn = state.audioArmed
            ? ''
            : `<button class="timer-btn timer-sound-btn" onclick="armAudio();playCue()">🔊 Activar sonido</button>`;
        return `
            <div class="timer-tab">
                <div class="timer-countdown" id="timer-countdown-value">${formatCountdown(ms)}</div>
                ${soundBtn}
                <button class="timer-btn timer-btn-reset" onclick="resetTimer()">⟲ Reiniciar</button>
            </div>
        `;
    }

    return `
        <div class="timer-tab">
            <div class="timer-stepper">
                <button class="timer-step" onclick="setTimerMinutes(-1)">−</button>
                <span class="timer-step-value">${state.timerMinutes}<small>min</small></span>
                <button class="timer-step" onclick="setTimerMinutes(1)">+</button>
            </div>
            <button class="timer-btn timer-btn-start" onclick="startTimer()">▶️ Iniciar cronómetro</button>
        </div>
    `;
}

// Small live countdown next to the match date, on every tab except the timer
// tab itself (where the big countdown already shows it). The tick loop in
// main.js refreshes #timer-pill-time in place each second. When audio is still
// locked (e.g. right after a reload) the pill shows a 🔇 and a tap on it — or
// anywhere on the page — unlocks the sound.
function renderTimerPill() {
    const state = store.get();
    if (!state.timerRunning) return '';
    if (state.activeTab === 'timer' && !ctx.isEditMode) return '';
    const ms = remainingMs(state.timerStartedAt, state.timerMinutes, Date.now());
    const muted = !state.audioArmed;
    const cls = muted ? 'timer-pill timer-pill-muted' : 'timer-pill';
    const icon = muted ? '🔇' : '⏱';
    const tap = muted ? "armAudio();playCue();setTab('timer')" : "setTab('timer')";
    return ` <button class="${cls}" onclick="${tap}">`
        + `${icon} <span id="timer-pill-time">${formatCountdown(ms)}</span></button>`;
}

function renderPlayersTab() {
    const state = store.get();
    const { currentStep, tempScorer, tempScorerTeam } = state;
    const instructionText = currentStep === 1 ? '¿Quién ha marcado gol?' : `⚽ ${tempScorer} marcó — ¿quién asistió?`;

    let colAHtml = '', colBHtml = '';
    let colAClass = 'team-col', colBClass = 'team-col';

    const btnHtml = (p, teamId) => `<button class="player-btn btn-${teamId.toLowerCase()}" onclick="selectPlayer('${p}', '${teamId}')">${p}</button>`;
    const noAssistBtn = (scorerTeam) => {
        const oppositeClass = scorerTeam === 'A' ? 'btn-b' : 'btn-a';
        return `<button class="player-btn ${oppositeClass}" onclick="registerGoal(null)">Sin asistente</button>`;
    };
    const cancelBtn = (scorerTeam) => {
        const btnClass = `own-goal-btn ${scorerTeam === 'A' ? 'btn-b' : 'btn-a'}`;
        return `
                <div class="cancel-split-col">
                    <button class="cancel-full-btn" style="flex:1;height:auto;" onclick="cancelGoal()">Cancelar</button>
                    <button class="${btnClass}" onclick="registerOwnGoal()">🥅 Propia puerta</button>
                </div>`;
    };

    if (currentStep === 1) {
        colAHtml = ctx.teamA.map(p => btnHtml(p, 'A')).join('');
        colBHtml = ctx.teamB.map(p => btnHtml(p, 'B')).join('');
    } else if (tempScorerTeam === 'A') {
        colAHtml = ctx.teamA.map(p => p === tempScorer ? noAssistBtn('A') : btnHtml(p, 'A')).join('');
        colBHtml = cancelBtn('A');
        colBClass += ' waiting';
    } else {
        colBHtml = ctx.teamB.map(p => p === tempScorer ? noAssistBtn('B') : btnHtml(p, 'B')).join('');
        colAHtml = cancelBtn('B');
        colAClass += ' waiting';
    }

    return `
            <div class="scoreboard">
                <div class="team-score">
                    <div class="team-name">${ctx.nameA}</div>
                    <div class="score-number score-a">${getGoals('A')}</div>
                </div>
                <div class="score-separator">–</div>
                <div class="team-score">
                    <div class="team-name">${ctx.nameB}</div>
                    <div class="score-number score-b">${getGoals('B')}</div>
                </div>
            </div>
            <p class="instruction ${currentStep === 2 ? 'assist' : ''}">${instructionText}</p>
            <div class="player-grid">
                <div class="${colAClass}">${colAHtml}</div>
                <div class="${colBClass}">${colBHtml}</div>
            </div>
        `;
}

function renderEventsTab() {
    const state = store.get();
    const eventsHtml = state.events.length > 0
        ? state.events.map((e, i) => renderEventRow(e, i)).join('')
        : `<div class="event-log" style="color:#64748b;justify-content:center;"><em>No hay eventos aún...</em></div>`;

    const idleLabel = ctx.isEditMode ? '💾 GUARDAR CORRECCIÓN' : '💾 CONFIRMAR Y GUARDAR PARTIDO';
    const armedLabel = ctx.isEditMode
        ? '⚠️ Pulsa otra vez para guardar la corrección'
        : '⚠️ Pulsa otra vez para guardar el partido';

    let btnLabel = idleLabel;
    let btnClass = 'save-btn';
    if (state.saving) {
        btnLabel = 'Enviando datos...';
    } else if (state.saveArmed) {
        btnLabel = armedLabel;
        btnClass = 'save-btn save-btn-armed';
    }
    const disabledAttr = state.saving ? ' disabled' : '';
    const errorHtml = state.saveError
        ? `<div class="save-error">${escHtml(state.saveError)}</div>`
        : '';

    return `
            <div class="events-tab">
                ${ctx.isEditMode ? '<div class="edit-mode-banner">✏️ Modo edición — corrección de resultado</div>' : ''}
                <div class="events-scroll">
                    <div id="event-list">
                        <div class="event-log" style="display:flex;align-items:center;gap:4px;padding:8px 4px;font-size:0.7rem;color:#94a3b8;text-transform:uppercase;letter-spacing:0.05em;">
                            <span style="flex: 0 0 42px;"></span>
                            <span style="flex: 1; text-align:center;">Goleador</span>
                            <span style="flex: 1; text-align:center;">Asistente</span>
                            <span style="flex: 0 0 35px;"></span>
                        </div>
                        ${eventsHtml}
                    </div>
                </div>
                <div class="events-footer">
                    ${errorHtml}
                    <button id="save-btn" class="${btnClass}" onclick="requestSave()"${disabledAttr}>${btnLabel}</button>
                </div>
            </div>
        `;
}

function renderNoMatch() {
    document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">No hay partido activo.<br>Espera a que se generen los equipos.</div>
                <button class="save-btn" style="max-width:200px;margin-top:8px;" onclick="waitForMatch()">🔄 Reintentar</button>
            </div>`;
}

function renderOffline() {
    document.getElementById('app').innerHTML = `
        <div class="no-match">
            <div class="no-match-icon">📡</div>
            <div class="no-match-title">PyBall</div>
            <div class="no-match-msg">Sin conexión.<br>Se reintentará al recuperar internet.</div>
        </div>`;
}

function renderStaleMatchChoice(oldDateLabel, onKeep, onFresh) {
    document.getElementById('app').innerHTML = `
            <div class="no-match">
                <div class="no-match-icon">⚽</div>
                <div class="no-match-title">PyBall</div>
                <div class="no-match-msg">Hay un partido del <strong>${escHtml(oldDateLabel)}</strong><br>sin guardar en este dispositivo.</div>
                <button class="save-btn" style="max-width:280px;" id="stale-keep">▶️ Seguir con ese partido</button>
                <button class="save-btn save-btn-armed" style="max-width:280px;" id="stale-fresh">🆕 Empezar el de hoy</button>
            </div>`;
    document.getElementById('stale-keep').addEventListener('click', onKeep, { once: true });
    document.getElementById('stale-fresh').addEventListener('click', onFresh, { once: true });
}

function renderApp() {
    const state = store.get();
    const prevScrollTop = document.querySelector('.events-scroll')?.scrollTop ?? 0;
    document.getElementById('app').innerHTML = `
            <div style="height:100vh;height:100svh;display:flex;flex-direction:column;padding:8px 12px 12px;">
                <div class="match-date">${formatMatchDate(ctx.meetupDate)}${renderTimerPill()}</div>
                <div class="tab-bar">
                    ${ctx.isEditMode ? '' : `<button class="tab-btn ${state.activeTab === 'timer' ? 'active' : ''}" onclick="setTab('timer')">Tiempo</button>`}
                    <button class="tab-btn ${state.activeTab === 'players' ? 'active' : ''}" onclick="setTab('players')">Jugadores</button>
                    <button class="tab-btn ${state.activeTab === 'events' ? 'active' : ''}" onclick="setTab('events')">Resultados</button>
                </div>
                ${state.activeTab === 'timer' && !ctx.isEditMode ? renderTimerTab() : ''}
                ${state.activeTab === 'players' ? renderPlayersTab() : ''}
                ${state.activeTab === 'events' ? renderEventsTab() : ''}
            </div>
        `;
    const scrollEl = document.querySelector('.events-scroll');
    if (scrollEl) scrollEl.scrollTop = prevScrollTop;
}

function formatMatchDate(dateStr) {
    if (!dateStr) return '';
    const d = new Date(dateStr);
    if (isNaN(d.getTime())) return '';
    const day = d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
    const time = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    return `${day.charAt(0).toUpperCase()}${day.slice(1)} · ${time}`;
}

export { renderApp, renderNoMatch, renderOffline, renderStaleMatchChoice, formatMatchDate };
