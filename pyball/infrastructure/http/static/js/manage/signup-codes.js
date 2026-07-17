import { post } from '../api.js';
import { escHtml } from './views.js';
import { copyToClipboard } from './main.js';

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
    const backdrop = document.createElement('div');
    backdrop.className = 'signup-code-backdrop';
    backdrop.innerHTML = `
    <div class="signup-code-box">
      <div class="signup-code-title">Código de ${escHtml(playerName)}</div>
      <div class="signup-code-value">${escHtml(code)}</div>
      <div class="signup-code-warning">Apúntalo — no se volverá a mostrar.</div>
      <button class="btn btn-teal signup-code-copy-btn">📋 Copiar código</button>
      <button class="btn btn-gray signup-code-close-btn">Cerrar</button>
    </div>
  `;
    document.body.appendChild(backdrop);

    const close = () => backdrop.remove();
    const copyBtn = backdrop.querySelector('.signup-code-copy-btn');
    const closeBtn = backdrop.querySelector('.signup-code-close-btn');

    backdrop.addEventListener('click', (ev) => {
        if (ev.target === backdrop) close();
    });
    closeBtn.addEventListener('click', close);
    copyBtn.addEventListener('click', () => {
        copyToClipboard(code, () => {
            copyBtn.textContent = '✅ Copiado';
            setTimeout(close, 1000);
        });
    });
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
