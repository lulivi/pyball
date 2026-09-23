// Rotation-timer engine for the /match wall.
//
// Zone 1 here is the small set of side-effecting wrappers (audio + wake lock)
// the SPA calls; their real bodies land with GL-205. Zone 2 is the pure
// countdown arithmetic — no DOM, no audio, no Date.now(): `now` is always
// passed in, so the same math drives the live display and any later test.

const MIN_MINUTES = 1;
const MAX_MINUTES = 15;
const DEFAULT_MINUTES = 6;

// Goalkeeper-change alarm (rotation cronómetro): one long, flat square-wave
// tone — no trill — loud enough to carry across a noisy pitch.
const CUE_LEN = 1.0;     // seconds of sustain
const CUE_GAIN = 0.60;
const CUE_HZ = 850;

const HOUR_MS = 3600000;

// Pitch-time-ending alarm: referee whistle "pi · pi · piiiiii" — two short
// blasts and a long one, each trilled (carrier frequency wobbled by an LFO),
// so it is tellable apart from the flat goalkeeper tone by count, rhythm and
// timbre. Blasts are [start offset, sustain] in seconds.
const WHISTLE_BLASTS = [[0, 0.35], [0.5, 0.35], [1.0, 1.0]];
const WHISTLE_GAIN = 0.60;
const WHISTLE_HZ = 2500;
const WHISTLE_TRILL_HZ = 25;      // LFO rate
const WHISTLE_TRILL_DEPTH = 150;  // ± Hz swing of the carrier

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
    _playBlasts([[0, CUE_LEN]], CUE_HZ, CUE_GAIN, 0);
}

export function playHourCue() {
    _playBlasts(WHISTLE_BLASTS, WHISTLE_HZ, WHISTLE_GAIN, WHISTLE_TRILL_DEPTH);
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

// Returns the epoch ms of the next hour boundary once we're within
// `minutesBefore` minutes of it, or null otherwise. Fires exactly once per
// boundary crossing when the caller tracks the last returned value.
export function hourWarnFireAt(now, minutesBefore) {
    const nextHour = Math.ceil((now + 1) / HOUR_MS) * HOUR_MS;
    const remaining = nextHour - now;
    return remaining <= minutesBefore * 60000 ? nextHour : null;
}

// ── Zone 2 (private) — shared oscillator loop for playCue/playHourCue ──────

function _playBlasts(blasts, hz, gain, trillDepth) {
    if (!_audioCtx) return;
    try {
        if (_audioCtx.state !== 'running') _audioCtx.resume().catch(() => {});
        const start = _audioCtx.currentTime + 0.06;
        for (const [offset, len] of blasts) {
            const at = start + offset;
            const osc = _audioCtx.createOscillator();
            const gainNode = _audioCtx.createGain();
            osc.type = 'square';
            osc.frequency.value = hz;
            if (trillDepth > 0) {
                const lfo = _audioCtx.createOscillator();
                const lfoGain = _audioCtx.createGain();
                lfo.frequency.value = WHISTLE_TRILL_HZ;
                lfoGain.gain.value = trillDepth;
                lfo.connect(lfoGain).connect(osc.frequency);
                lfo.start(at);
                lfo.stop(at + len + 0.05);
            }
            gainNode.gain.setValueAtTime(0, at);
            gainNode.gain.linearRampToValueAtTime(gain, at + 0.015);
            gainNode.gain.setValueAtTime(gain, at + len);
            gainNode.gain.linearRampToValueAtTime(0, at + len + 0.03);
            osc.connect(gainNode).connect(_audioCtx.destination);
            osc.start(at);
            osc.stop(at + len + 0.05);
        }
    } catch { /* ignore — flash still fires */ }
}
