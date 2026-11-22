//! Minimal client for the PyBall REST API (the same endpoints /manage uses).

use anyhow::{Context, Result, bail};
use serde::Deserialize;
use serde::de::DeserializeOwned;
use serde_json::{Value, json};
use ureq::http::{Response, StatusCode};
use ureq::{Agent, Body};

pub struct PyBall {
    base: String,
    manage_token: String,
    http: Agent,
}

#[derive(Debug, Clone, Deserialize)]
pub struct ActiveMeetup {
    pub date: String,
    #[serde(default)]
    pub location: Option<String>,
    pub players: Vec<PlayerRef>,
    #[serde(default)]
    pub teams: Option<Teams>,
}

#[derive(Debug, Clone, Deserialize)]
pub struct PlayerRef {
    pub id: String,
    pub name: String,
}

#[derive(Debug, Clone, Deserialize)]
pub struct Player {
    pub id: String,
    pub name: String,
    /// PyBall group; only "regular" players (club members) are on the siesta list.
    pub group: String,
}

impl Player {
    pub fn is_regular(&self) -> bool {
        self.group == "regular"
    }
}

#[derive(Debug, Clone, Deserialize)]
#[serde(rename_all = "camelCase")]
pub struct Teams {
    pub team_a: Vec<String>,
    pub team_b: Vec<String>,
    #[serde(default)]
    pub name_a: Option<String>,
    #[serde(default)]
    pub name_b: Option<String>,
    #[serde(default)]
    pub emoji_a: Option<String>,
    #[serde(default)]
    pub emoji_b: Option<String>,
    #[serde(default)]
    pub has_recorded_results: bool,
}

impl PyBall {
    pub fn new(base_url: &str, manage_token: &str) -> Result<Self> {
        let http = Agent::config_builder()
            .timeout_global(Some(std::time::Duration::from_secs(60))) // team generation can be slowish
            .max_redirects(0)
            .max_redirects_will_error(false) // hand the 3xx back so check() reports it
            .http_status_as_error(false) // check() turns 4xx/5xx into errors itself
            .build()
            .into();
        Ok(Self {
            base: base_url.trim_end_matches('/').to_string(),
            manage_token: manage_token.to_string(),
            http,
        })
    }

    /// The meetup currently open in PyBall, or `None` if there isn't one.
    pub fn active_meetup(&self) -> Result<Option<ActiveMeetup>> {
        let resp = self.reach(self.get("/api/meetup/active").call())?;
        if resp.status() == StatusCode::NOT_FOUND {
            return Ok(None);
        }
        let resp = check(resp, "GET /api/meetup/active")?;
        Ok(Some(json_body(resp).context("decoding active meetup")?))
    }

    /// Every player in PyBall (players.json), with their group.
    pub fn players(&self) -> Result<Vec<Player>> {
        let resp = check(
            self.reach(self.get("/api/players").call())?,
            "GET /api/players",
        )?;
        json_body(resp).context("decoding players")
    }

    /// Replace the meetup's roster with exactly `player_ids` (also clears teams).
    pub fn set_roster(&self, date: &str, player_ids: &[String]) -> Result<()> {
        let body = json!({ "date": date, "player_ids": player_ids });
        let resp = self.reach(self.post("/api/meetup/create").send_json(&body))?;
        check(resp, "POST /api/meetup/create")?;
        Ok(())
    }

    /// Build two teams with the given PyBall algorithm ("balanceado" or "aleatorio").
    pub fn generate_teams(&self, date: &str, algorithm: &str) -> Result<()> {
        let body = json!({ "date": date, "algorithm": algorithm, "team_count": 2 });
        let resp = self.reach(self.post("/api/meetup/generate-teams").send_json(&body))?;
        check(resp, "POST /api/meetup/generate-teams")?;
        Ok(())
    }

    fn get(&self, path: &str) -> ureq::RequestBuilder<ureq::typestate::WithoutBody> {
        self.auth(self.http.get(format!("{}{}", self.base, path)))
    }

    fn post(&self, path: &str) -> ureq::RequestBuilder<ureq::typestate::WithBody> {
        self.auth(self.http.post(format!("{}{}", self.base, path)))
    }

    fn auth<B>(&self, req: ureq::RequestBuilder<B>) -> ureq::RequestBuilder<B> {
        if self.manage_token.is_empty() {
            req
        } else {
            req.header(
                "Cookie",
                format!("pyball_manage_token={}", self.manage_token),
            )
        }
    }

    fn reach(&self, sent: Result<Response<Body>, ureq::Error>) -> Result<Response<Body>> {
        sent.with_context(|| format!("cannot reach PyBall at {}", self.base))
    }
}

fn json_body<T: DeserializeOwned>(mut resp: Response<Body>) -> Result<T> {
    Ok(resp.body_mut().read_json()?)
}

fn check(mut resp: Response<Body>, what: &str) -> Result<Response<Body>> {
    let status = resp.status();
    if status.is_success() {
        return Ok(resp);
    }
    let detail = resp
        .body_mut()
        .read_json::<Value>()
        .ok()
        .and_then(|v| v.get("detail").map(|d| d.to_string()))
        .unwrap_or_default();
    match status {
        StatusCode::UNAUTHORIZED | StatusCode::FORBIDDEN => {
            bail!("{what}: {status} — check manage_token")
        }
        _ => bail!("{what}: {status} {detail}"),
    }
}
