// Rotation-timer engine for the /match wall.
//
// Zone 1 here is the small set of side-effecting wrappers (audio + wake lock)
// the SPA calls; their real bodies land with GL-205. Zone 2 is the pure
// countdown arithmetic — no DOM, no audio, no Date.now(): `now` is always
// passed in, so the same math drives the live display and any later test.

const MIN_MINUTES = 1;
const MAX_MINUTES = 15;
const DEFAULT_MINUTES = 6;

// End-of-interval alarm: square-wave beeps, loud enough to carry across a
// noisy pitch. Tune the count / spacing / length / volume / pitch here.
const BEEP_COUNT = 3;
const BEEP_LEN = 0.30;   // seconds of sustain per beep
const BEEP_GAP = BEEP_LEN + 0.05;   // seconds, start-to-start
const BEEP_GAIN = 0.60;
const BEEP_HZ = 850;

// ── Zone 1 — side effects (implemented in GL-205) ──────────────────────────

let _audioCtx = null;
let _wakeLock = null;
let _wakeLockPending = false;

export function startAudio() {
    try {
        const Ctor = window.AudioContext || window.webkitAudioContext;
        if (!Ctor) return;
        if (!_audioCtx) _audioCtx = new Ctor();
        if (_audioCtx.state !== 'running') _audioCtx.resume().catch(() => {});
        // Play one silent sample inside the gesture — Chromium on Android
        // (Brave included) leaves a freshly-resumed context muted until it
        // has actually rendered something.
        const src = _audioCtx.createBufferSource();
        src.buffer = _audioCtx.createBuffer(1, 1, _audioCtx.sampleRate);
        src.connect(_audioCtx.destination);
        src.start(0);
    } catch { /* audio unavailable — timer still runs silently */ }
}

export function playCue() {
    if (!_audioCtx) return;
    try {
        if (_audioCtx.state !== 'running') _audioCtx.resume().catch(() => {});
        const start = _audioCtx.currentTime + 0.06;
        for (let i = 0; i < BEEP_COUNT; i += 1) {
            const at = start + i * BEEP_GAP;
            const osc = _audioCtx.createOscillator();
            const gain = _audioCtx.createGain();
            osc.type = 'square';
            osc.frequency.value = BEEP_HZ;
            gain.gain.setValueAtTime(0, at);
            gain.gain.linearRampToValueAtTime(BEEP_GAIN, at + 0.015);
            gain.gain.setValueAtTime(BEEP_GAIN, at + BEEP_LEN);
            gain.gain.linearRampToValueAtTime(0, at + BEEP_LEN + 0.03);
            osc.connect(gain).connect(_audioCtx.destination);
            osc.start(at);
            osc.stop(at + BEEP_LEN + 0.05);
        }
    } catch { /* ignore — flash still fires */ }
}

export function requestWakeLock() {
    try {
        if (!('wakeLock' in navigator) || _wakeLock || _wakeLockPending) return;
        _wakeLockPending = true;
        navigator.wakeLock.request('screen').then(lock => {
            _wakeLock = lock;
            _wakeLockPending = false;
            lock.addEventListener('release', () => { _wakeLock = null; });
        }).catch(() => { _wakeLockPending = false; });
    } catch { _wakeLockPending = false; }
}

export function releaseWakeLock() {
    try {
        if (_wakeLock) _wakeLock.release();
    } catch { /* ignore */ }
    _wakeLock = null;
}

// ── Zone 2 — pure arithmetic ──────────────────────────────────────────────

export function clampMinutes(n) {
    const i = Math.floor(Number(n));
    if (!Number.isFinite(i)) return DEFAULT_MINUTES;
    return Math.min(MAX_MINUTES, Math.max(MIN_MINUTES, i));
}

export function periodMs(minutes) {
    return minutes * 60000;
}

export function completedCycles(startedAt, minutes, now) {
    if (startedAt == null) return 0;
    const elapsed = now - startedAt;
    if (elapsed <= 0) return 0;
    return Math.floor(elapsed / periodMs(minutes));
}

export function remainingMs(startedAt, minutes, now) {
    const period = periodMs(minutes);
    if (startedAt == null) return period;
    const elapsed = now - startedAt;
    if (elapsed <= 0) return period;
    const offset = elapsed % period;
    return offset === 0 ? period : period - offset;
}

export function formatCountdown(ms) {
    const totalSeconds = Math.max(0, Math.ceil(ms / 1000));
    const minutes = Math.floor(totalSeconds / 60);
    const seconds = totalSeconds % 60;
    return `${minutes}:${String(seconds).padStart(2, '0')}`;
}
