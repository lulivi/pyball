# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.
"""Round-robin ruleset for triangular tournaments: who plays the next match."""

from __future__ import annotations

import random as random_module

from pyball.domain.meetup.models import Match, Meetup, Team

_MAX_CONSECUTIVE = 3


def ensure_first_match(meetup: Meetup) -> bool:
    """Create meetup's first pending match in place, if none exists yet.

    No-op (returns False) if teams aren't assigned yet, a match is already
    pending, or any match has already been played.
    """
    if meetup.teams is None or meetup.current_match() is not None or meetup.matches:
        return False
    teams = meetup.teams
    if len(teams) == 2:
        pairing = (teams[0], teams[1])
    else:
        pairing = pick_first_pairing((teams[0], teams[1], teams[2]))
    meetup.add_match(Match(teams_playing=pairing))
    return True


def pick_first_pairing(
    teams: tuple[Team, Team, Team],
    rng: random_module.Random | None = None,
) -> tuple[Team, Team]:
    """Randomly choose which 2 of the 3 teams play the opening match."""
    source = rng or random_module
    resting = source.choice(teams)
    playing = tuple(t for t in teams if t != resting)
    return playing  # type: ignore[return-value]


def calculate_next_round(
    teams: tuple[Team, Team, Team],
    matches: list[Match],
    rng: random_module.Random | None = None,
) -> tuple[Team, Team]:
    """Return the 2 teams that should play the next match, per the triangular ruleset.

    The second element of the returned tuple is always the team that was
    NOT part of the just-finished match — i.e. the team now entering the
    pitch — regardless of which branch (simple win, forced-out win, or draw)
    decided who from the just-finished match stays on. That team is never
    the one just sent to the bench by this same decision: re-entering
    immediately would defeat whichever rule just benched it.

    Args:
        teams: The 3 teams in this triangular.
        matches: Match history so far, oldest first. Empty for the opening match.
        rng: Optional random source, for deterministic tests.

    Raises:
        ValueError: If matches is non-empty but the last match has no result yet.
    """
    if not matches:
        return pick_first_pairing(teams, rng)

    last = matches[-1]
    if last.result is None:
        raise ValueError("Cannot compute the next round: last match has no result yet")

    team_x, team_y = last.teams_playing
    entering = _resting_team(teams, last)
    streaks = {t: _consecutive_streak(t, matches) for t in (team_x, team_y)}

    if last.result.score_a == last.result.score_b:
        if streaks[team_x] == streaks[team_y]:
            stays = (rng or random_module).choice([team_x, team_y])
        else:
            stays = team_x if streaks[team_x] < streaks[team_y] else team_y
    else:
        winner = team_x if last.result.score_a > last.result.score_b else team_y
        loser = team_y if winner is team_x else team_x
        stays = loser if streaks[winner] >= _MAX_CONSECUTIVE else winner

    return (stays, entering)


def _resting_team(teams: tuple[Team, Team, Team], match: Match) -> Team:
    """Return the team not present in the given match."""
    resting = set(teams) - set(match.teams_playing)
    return next(iter(resting))


def _consecutive_streak(team: Team, matches: list[Match]) -> int:
    """Return how many trailing matches (from the most recent) this team played in a row."""
    streak = 0
    for match in reversed(matches):
        if team in match.teams_playing:
            streak += 1
        else:
            break
    return streak
