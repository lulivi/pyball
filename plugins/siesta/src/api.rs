// Copyright (c) 2026 Luis Liñán
//
// Permission is hereby granted, free of charge, to any person obtaining a copy
// of this software and associated documentation files (the "Software"), to deal
// in the Software without restriction, including without limitation the rights
// to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
// copies of the Software, and to permit persons to whom the Software is
// furnished to do so, subject to the following conditions:
//
// The above copyright notice and this permission notice shall be included in all
// copies or substantial portions of the Software.
//
// THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
// IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
// FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
// AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
// LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
// OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
// SOFTWARE.

//! siesta's calls to PyBall's plugin API (`/api/v1`) and the shapes it reads back.

use anyhow::{Context, Result};
use pyball_client::{EventStream, endpoints};
use serde::{Deserialize, Serialize};

endpoints! {
    PLAYERS: GET "/players" -> Vec<Player>;
    ACTIVE_MEETUP: GET "/meetups/active" -> Meetup;
    LINEUP: PUT "/meetups/{meetup_id}/lineup" (LineupBody) -> Meetup;
    SUBSTITUTE_SEARCH: POST "/meetups/{meetup_id}/substitute-search" -> Meetup;
    EVENTS: GET "/events" -> Event;
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(Serialize))]
pub struct Meetup {
    pub id: String,
    /// `YYYY-MM-DDTHH:MM:SS`, PyBall's local time.
    pub date: String,
    #[serde(default)]
    pub location: String,
    pub capacity: usize,
    pub substitute_search: bool,
    /// Player ids.
    pub players: Vec<String>,
    pub teams: Option<Vec<Team>>,
    #[serde(default)]
    pub matches: Vec<Match>,
    pub closed: bool,
}

impl Meetup {
    pub fn has_recorded_results(&self) -> bool {
        self.matches.iter().any(|m| m.score.is_some())
    }
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(Serialize))]
pub struct Team {
    pub name: String,
    pub players: Vec<String>,
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(Serialize))]
pub struct Match {
    pub score: Option<Vec<u32>>,
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(Serialize))]
pub struct Player {
    pub id: String,
    pub name: String,
    /// Only "regular" players (club members) are on the siesta list.
    pub group: String,
}

impl Player {
    pub fn is_regular(&self) -> bool {
        self.group == "regular"
    }
}

/// Body of `PUT /meetups/{id}/lineup`.
#[derive(Serialize)]
pub struct LineupBody {
    pub players: Vec<String>,
    pub team_algorithm: String,
}

/// One server-sent event: its id, its type and the meetup as it was right after.
#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(Serialize))]
pub struct Event {
    pub id: u64,
    #[serde(rename = "type")]
    pub kind: String,
    pub meetup: Meetup,
}

/// The plugin API, through siesta's endpoints only.
pub struct Api(pyball_client::Api);

impl Api {
    pub fn new(base_url: &str, token: &str) -> Self {
        Self(pyball_client::Api::new(base_url, token))
    }

    pub fn players(&self) -> Result<Vec<Player>> {
        self.0.call(&PLAYERS, "").context("decoding players")
    }

    /// The meetup not closed yet, or `None` if there isn't one.
    pub fn active_meetup(&self) -> Result<Option<Meetup>> {
        self.0
            .call_optional(&ACTIVE_MEETUP, "")
            .context("decoding the active meetup")
    }

    /// Replace the roster with exactly `players` and build teams with `algorithm`.
    pub fn set_lineup(
        &self,
        meetup_id: &str,
        players: &[String],
        algorithm: &str,
    ) -> Result<Meetup> {
        let body = LineupBody {
            players: players.to_vec(),
            team_algorithm: algorithm.to_string(),
        };
        self.0
            .call_with(&LINEUP, meetup_id, &body)
            .context("decoding the meetup")
    }

    pub fn open_substitute_search(&self, meetup_id: &str) -> Result<Meetup> {
        self.0
            .call(&SUBSTITUTE_SEARCH, meetup_id)
            .context("decoding the meetup")
    }

    /// Open the event stream after `last_event_id` (only new events if `None`).
    pub fn events(&self, last_event_id: Option<u64>) -> Result<EventStream<Event>> {
        self.0.events(&EVENTS, last_event_id)
    }
}
