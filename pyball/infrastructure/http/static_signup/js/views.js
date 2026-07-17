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
      <div class="meetup-info">${escHtml(_formatDate(meetup.date))} · ${escHtml(meetup.location)}</div>
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
    const wasInATeam = meetup.teams.some((team) => team.players.some((p) => p.isMe));
    const notJoinedNote = wasInATeam
        ? ''
        : '<div class="meetup-info">No estabas apuntado a esta convocatoria.</div>';
    const teamsHtml = meetup.teams.map((team) => {
        const players = team.players
            .map((p) => `<li${p.isMe ? ' class="me"' : ''}>${escHtml(p.name)}</li>`)
            .join('');
        return `
      <div class="team-card">
        <div class="team-header" style="background:${team.colorBg};color:${team.colorText}">${escHtml(team.name)}</div>
        <ul class="teammate-list">${players}</ul>
      </div>
    `;
    }).join('');
    return `${note}${notJoinedNote}${teamsHtml}`;
}

function _formatDate(iso) {
    const d = new Date(iso);
    const day = d.toLocaleDateString('es-ES', { weekday: 'long', day: 'numeric', month: 'long' });
    const time = d.toLocaleTimeString('es-ES', { hour: '2-digit', minute: '2-digit' });
    return `${day.charAt(0).toUpperCase()}${day.slice(1)} · ${time}`;
}
