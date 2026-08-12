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

export function showSignupCodeModal(playerName, code, signupUrl) {
    const message = `Acceso a la web de la peña: ${signupUrl}\nTu código: ${code}`;
    const shareBtn = typeof navigator.share === 'function'
        ? '<button class="btn btn-teal signup-code-share-btn">📤 Compartir</button>'
        : '';
    const backdrop = document.createElement('div');
    backdrop.className = 'signup-code-backdrop';
    backdrop.innerHTML = `
    <div class="signup-code-box">
      <div class="signup-code-title">Código de ${escHtml(playerName)}</div>
      <div class="signup-code-value">${escHtml(code)}</div>
      <div class="signup-code-warning">Apúntalo — no se volverá a mostrar.</div>
      <div class="signup-code-url">${escHtml(signupUrl)}</div>
      ${shareBtn}
      <button class="btn btn-teal signup-code-copy-btn">📋 Copiar mensaje</button>
      <button class="btn btn-gray signup-code-close-btn">Cerrar</button>
    </div>
  `;
    document.body.appendChild(backdrop);

    const close = () => backdrop.remove();
    const shareBtnEl = backdrop.querySelector('.signup-code-share-btn');
    const copyBtn = backdrop.querySelector('.signup-code-copy-btn');
    const closeBtn = backdrop.querySelector('.signup-code-close-btn');

    backdrop.addEventListener('click', (ev) => {
        if (ev.target === backdrop) close();
    });
    closeBtn.addEventListener('click', close);
    if (shareBtnEl) {
        shareBtnEl.addEventListener('click', () => {
            navigator.share({ text: message }).catch(() => {});
        });
    }
    copyBtn.addEventListener('click', () => {
        copyToClipboard(message, () => {
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
    showSignupCodeModal(playerName, data.code, data.signup_url);
    if (window.loadJugadores) window.loadJugadores();
}

function escAttrLocal(s) {
    return String(s).replace(/'/g, "\\'");
}
