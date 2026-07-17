export function escHtml(s) {
    return String(s).replace(/[&<>"']/g, (c) => ({
        '&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;',
    }[c]));
}

export function buildCodeScreen(errorMsg) {
    return `
    <div class="card">
      <div class="field-label">Tu código personal</div>
      <input id="code-input" class="code-input" type="text" maxlength="8" autocomplete="off" placeholder="XXXXXXXX">
      ${errorMsg ? `<div class="error-msg">${escHtml(errorMsg)}</div>` : ''}
      <button class="btn btn-blue" id="verify-btn">Entrar</button>
    </div>
  `;
}

export function buildMainScreen(playerName, meetup) {
    const rosterSection = meetup.signupOpen
        ? buildOpenRoster(meetup)
        : buildClosedTeam(meetup);
    return `
    <div class="card">
      <div class="player-name">${escHtml(playerName)}</div>
      <div class="meetup-info">${escHtml(meetup.location)} · ${escHtml(_formatDate(meetup.date))}</div>
      ${rosterSection}
    </div>
    <button class="link-btn" id="logout-btn">No soy yo</button>
  `;
}

// ── Private helpers ───────────────────────────────────────────────────────────

function buildOpenRoster(meetup) {
    const rosterItems = meetup.roster.map((name) => `<li>${escHtml(name)}</li>`).join('');
    const joinBtn = meetup.isJoined
        ? '<button class="btn btn-red" id="leave-btn">Salir</button>'
        : '<button class="btn btn-green" id="join-btn">Apuntarme</button>';
    return `
    <div class="field-label">Apuntados (${meetup.roster.length})</div>
    <ul class="roster-list">${rosterItems}</ul>
    ${joinBtn}
  `;
}

function buildClosedTeam(meetup) {
    const note = '<div class="closed-note">El fichaje ya está cerrado — los equipos están hechos.</div>';
    if (!meetup.team) {
        return `${note}<div class="meetup-info">No estabas apuntado a esta convocatoria.</div>`;
    }
    const teammates = meetup.team.teammates.map((name) => `<li>${escHtml(name)}</li>`).join('');
    return `
    ${note}
    <div class="field-label">Tu equipo: ${escHtml(meetup.team.name)}</div>
    <ul class="teammate-list">${teammates}</ul>
  `;
}

function _formatDate(iso) {
    const [datePart, timePart] = iso.split('T');
    const [year, month, day] = datePart.split('-');
    return `${day}/${month}/${year} ${timePart}`;
}
