// Tiny pub/sub state container with optional localStorage persistence helpers.

export function createStore(initialState) {
    let state = initialState;
    const listeners = new Set();
    return {
        get: () => state,
        set(partial) {
            state = { ...state, ...partial };
            listeners.forEach(fn => fn(state));
        },
        subscribe(fn) {
            listeners.add(fn);
            return () => listeners.delete(fn);
        },
    };
}

// Persist every store change under `key` while `when()` returns true.
export function persistTo(store, key, { when = () => true } = {}) {
    return store.subscribe(state => {
        if (when()) localStorage.setItem(key, JSON.stringify(state));
    });
}

// Load a previously persisted value, or null when absent/corrupt.
export function loadPersisted(key) {
    const raw = localStorage.getItem(key);
    if (!raw) return null;
    try { return JSON.parse(raw); } catch { return null; }
}
