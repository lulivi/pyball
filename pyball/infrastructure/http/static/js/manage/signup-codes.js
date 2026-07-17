import { post } from '../api.js';

export function initSignupCodes() {
    window.regenerateSignupCode = regenerateSignupCode;
    window.__signupCodeCell = signupCodeCell;
    window.__showSignupCode = showSignupCodeModal;
}

export function signupCodeCell(player) {
    const label = player.has_signup_code ? 'Regenerar código' : 'Generar código';
    return `<button class="btn-sm gray" onclick="regenerateSignupCode('${player.id}', '${escAttrLocal(player.name)}')">${label}</button>`;
}

export function showSignupCodeModal(playerName, code) {
    alert(`Código de ${playerName}: ${code}\n\nApúntalo — no se volverá a mostrar.`);
}

// ── Private helpers ───────────────────────────────────────────────────────────

async function regenerateSignupCode(playerId, playerName) {
    let data;
    try {
        data = await post(`/api/players/${playerId}/signup-code/regenerate`, {});
    } catch (err) {
        alert('Error: ' + (err.detail || err.message));
        return;
    }
    showSignupCodeModal(playerName, data.code);
    if (window.loadJugadores) window.loadJugadores();
}

function escAttrLocal(s) {
    return String(s).replace(/'/g, "\\'");
}
