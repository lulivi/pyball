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
});

// Persistence mirrors the old persistState(): skipped entirely in edit mode.
export function enablePersistence() {
    persistTo(store, STATE_KEY, { when: () => !ctx.isEditMode });
}

export function getGoals(teamId) {
    return store.get().events.filter(e => e.team === teamId).length;
}

export function saveTeamsSnapshot(colors = {}) {
    localStorage.setItem(TEAMS_KEY, JSON.stringify({
        teamA: ctx.teamA, teamB: ctx.teamB,
        nameA: ctx.nameA, nameB: ctx.nameB,
        meetupDate: ctx.meetupDate,
        colorA: colors.colorA ?? null, colorB: colors.colorB ?? null,
        colorTextA: colors.colorTextA ?? null, colorTextB: colors.colorTextB ?? null,
    }));
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
