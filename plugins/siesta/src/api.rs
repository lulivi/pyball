//! Client for PyBall's plugin API (`/api/v1`) and its event stream.

use std::io::{BufRead, BufReader, Read};
use std::time::Duration;

use anyhow::{Context, Result, bail};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use ureq::http::{Response, StatusCode};
use ureq::{Agent, Body};

pub struct Api {
    base: String,
    token: String,
    http: Agent,
    /// Without a global timeout: the event stream stays open for as long as PyBall runs.
    stream: Agent,
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
pub struct LineupBody<'a> {
    pub players: &'a [String],
    pub team_algorithm: &'a str,
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

impl Api {
    pub fn new(base_url: &str, token: &str) -> Self {
        let config = || {
            Agent::config_builder()
                .max_redirects(0)
                .max_redirects_will_error(false) // hand the 3xx back so check() reports it
                .http_status_as_error(false) // check() turns 4xx/5xx into errors itself
                .timeout_connect(Some(Duration::from_secs(10)))
        };
        Self {
            base: base_url.trim_end_matches('/').to_string(),
            token: token.to_string(),
            // team generation can be slowish
            http: config()
                .timeout_global(Some(Duration::from_secs(60)))
                .build()
                .into(),
            stream: config().build().into(),
        }
    }

    pub fn players(&self) -> Result<Vec<Player>> {
        let resp = self.call(self.get(&self.http, "/players").call(), "GET /players")?;
        json_body(resp).context("decoding players")
    }

    /// The meetup not closed yet, or `None` if there isn't one.
    pub fn active_meetup(&self) -> Result<Option<Meetup>> {
        let sent = self.get(&self.http, "/meetups/active").call();
        let resp = sent.with_context(|| format!("cannot reach PyBall at {}", self.base))?;
        if resp.status() == StatusCode::NOT_FOUND {
            return Ok(None);
        }
        let resp = check(resp, "GET /meetups/active")?;
        Ok(Some(json_body(resp).context("decoding the active meetup")?))
    }

    /// Replace the roster with exactly `players` and build teams with `algorithm`.
    pub fn set_lineup(
        &self,
        meetup_id: &str,
        players: &[String],
        algorithm: &str,
    ) -> Result<Meetup> {
        let path = format!("/meetups/{meetup_id}/lineup");
        let body = LineupBody {
            players,
            team_algorithm: algorithm,
        };
        let sent = self
            .auth(self.http.put(format!("{}{path}", self.base)))
            .send_json(&body);
        json_body(self.call(sent, &format!("PUT {path}"))?).context("decoding the meetup")
    }

    pub fn open_substitute_search(&self, meetup_id: &str) -> Result<Meetup> {
        let path = format!("/meetups/{meetup_id}/substitute-search");
        let sent = self
            .auth(self.http.post(format!("{}{path}", self.base)))
            .send_empty();
        json_body(self.call(sent, &format!("POST {path}"))?).context("decoding the meetup")
    }

    /// Open the event stream after `last_event_id` (only new events if `None`).
    pub fn events(&self, last_event_id: Option<u64>) -> Result<EventStream> {
        let mut req = self
            .get(&self.stream, "/events")
            .header("Accept", "text/event-stream");
        if let Some(id) = last_event_id {
            req = req.header("Last-Event-ID", id.to_string());
        }
        let resp = self.call(req.call(), "GET /events")?;
        Ok(EventStream::new(resp.into_body().into_reader()))
    }

    fn get(&self, agent: &Agent, path: &str) -> ureq::RequestBuilder<ureq::typestate::WithoutBody> {
        self.auth(agent.get(format!("{}{}", self.base, path)))
    }

    fn auth<B>(&self, req: ureq::RequestBuilder<B>) -> ureq::RequestBuilder<B> {
        req.header("Authorization", format!("Bearer {}", self.token))
    }

    fn call(
        &self,
        sent: Result<Response<Body>, ureq::Error>,
        what: &str,
    ) -> Result<Response<Body>> {
        let resp = sent.with_context(|| format!("cannot reach PyBall at {}", self.base))?;
        check(resp, what)
    }
}

/// Reads server-sent events one at a time.
pub struct EventStream {
    lines: std::io::Lines<BufReader<Box<dyn Read + Send + Sync + 'static>>>,
}

/// What the stream gave: an event, or a keepalive comment (sent every 15 s when idle).
pub enum Frame {
    Event(Box<Event>),
    Keepalive,
}

impl EventStream {
    fn new(reader: impl Read + Send + Sync + 'static) -> Self {
        let boxed: Box<dyn Read + Send + Sync> = Box::new(reader);
        Self {
            lines: BufReader::new(boxed).lines(),
        }
    }

    /// The next frame, or `None` when PyBall closes the stream.
    pub fn next_frame(&mut self) -> Result<Option<Frame>> {
        let mut data = String::new();
        for line in self.lines.by_ref() {
            let line = line.context("reading the event stream")?;
            if line.is_empty() {
                if data.is_empty() {
                    continue;
                }
                let event: Event = serde_json::from_str(&data).context("decoding an event")?;
                return Ok(Some(Frame::Event(Box::new(event))));
            }
            if line.starts_with(':') {
                return Ok(Some(Frame::Keepalive));
            }
            if let Some(chunk) = line.strip_prefix("data:") {
                data.push_str(chunk.strip_prefix(' ').unwrap_or(chunk));
            }
        }
        Ok(None)
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
            bail!("{what}: {status} {detail} — check PYBALL_API_TOKEN and the plugin's scopes")
        }
        _ => bail!("{what}: {status} {detail}"),
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    const MEETUP: &str = r#"{"id":"m1","date":"2026-11-18T20:00:00","location":"","capacity":10,"substitute_search":false,"players":["p1"],"teams":null,"matches":[],"closed":false}"#;

    #[test]
    fn reads_events_and_keepalives() {
        let raw = format!(
            "id: 7\nevent: substitute_search.closed\ndata: {{\"id\":7,\"type\":\"substitute_search.closed\",\"occurred_at\":\"x\",\"meetup\":{MEETUP}}}\n\n: ping\n\n"
        );
        let mut stream = EventStream::new(std::io::Cursor::new(raw.into_bytes()));
        let Some(Frame::Event(event)) = stream.next_frame().unwrap() else {
            panic!("expected an event");
        };
        assert_eq!(event.id, 7);
        assert_eq!(event.kind, "substitute_search.closed");
        assert_eq!(event.meetup.capacity, 10);
        assert!(matches!(
            stream.next_frame().unwrap(),
            Some(Frame::Keepalive)
        ));
        assert!(stream.next_frame().unwrap().is_none());
    }
}
