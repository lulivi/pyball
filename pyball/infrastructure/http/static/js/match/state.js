import { createStore, persistTo } from '../store.js';

export const STATE_KEY = 'pyball_current_match';
export const TEAMS_KEY = 'pyball_teams';

// Mutable match context: teams, display names, date, and mode. Views read it;
// only main.js writes it.
export const ctx = {
    teamA: [], teamB: [],
    nameA: 'A', nameB: 'B',
    meetupDate: '',
    isEditMode: false,
};

export const store = createStore({
    events: [],
    currentStep: 1,
    tempScorer: null,
    tempScorerTeam: null,
    editingEvent: null,
    activeTab: 'players',
    saveArmed: false,
    saving: false,
    saveError: null,
    timerRunning: false,
    timerMinutes: 6,
    timerStartedAt: null,
    lastCycleFired: 0,
    // Whether the browser's audio has been unlocked by a user gesture this
    // page load. Reset to false on every load (a reload re-locks audio), so
    // a resumed timer knows to prompt for a tap before it can beep.
    audioArmed: false,
});

// Persistence mirrors the old persistState(): skipped entirely in edit mode.
export function enablePersistence() {
    persistTo(store, STATE_KEY, { when: () => !ctx.isEditMode });
}

// One-shot persist of the current store, for the initial write that a
// change-triggered subscription (see enablePersistence) would otherwise miss:
// without a first goal, only the teams snapshot exists and an offline reopen
// cannot restore the match. Skipped in edit mode, same as enablePersistence.
export function persistStateNow() {
    if (ctx.isEditMode) return;
    try {
        localStorage.setItem(STATE_KEY, JSON.stringify(store.get()));
    } catch { /* ignore */ }
}

export function getGoals(teamId) {
    return store.get().events.filter(e => e.team === teamId).length;
}

export function saveTeamsSnapshot(colors = {}) {
    try {
        localStorage.setItem(TEAMS_KEY, JSON.stringify({
            teamA: ctx.teamA, teamB: ctx.teamB,
            nameA: ctx.nameA, nameB: ctx.nameB,
            meetupDate: ctx.meetupDate,
            colorA: colors.colorA ?? null, colorB: colors.colorB ?? null,
            colorTextA: colors.colorTextA ?? null, colorTextB: colors.colorTextB ?? null,
        }));
    } catch { /* ignore */ }
}

export function clearSaved() {
    localStorage.removeItem(STATE_KEY);
    localStorage.removeItem(TEAMS_KEY);
}

export function applyTeamColors(colorA, colorTextA, colorB, colorTextB) {
    if (!colorA) return;
    document.documentElement.style.setProperty('--color-light', colorA);
    document.documentElement.style.setProperty('--color-light-text', colorTextA);
    document.documentElement.style.setProperty('--color-dark', colorB);
    document.documentElement.style.setProperty('--color-dark-text', colorTextB);
}
