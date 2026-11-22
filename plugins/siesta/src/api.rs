//! Client for PyBall's plugin API (`/api/v1`) and its event stream.

use std::io::{BufRead, BufReader, Read};
use std::marker::PhantomData;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use serde::de::DeserializeOwned;
use serde::{Deserialize, Serialize};
use serde_json::Value;
use ureq::http::{Request, Response, StatusCode, request};
use ureq::{Agent, Body};

/// Every call siesta makes to PyBall: its method, its path, the JSON body it sends (if
/// any, in parentheses) and what it answers with. The client sends requests only through
/// these, and the contract test checks each one against `plugins/openapi.json`.
macro_rules! endpoints {
    ($($name:ident: $method:ident $path:literal $(($body:ty))? -> $out:ty;)*) => {
        $(
            pub const $name: Endpoint<endpoints!(@body $($body)?), $out> =
                Endpoint::new(stringify!($method), $path);
        )*

        /// Check every endpoint, with the body siesta sends and the type it decodes.
        #[cfg(test)]
        pub fn check_endpoints(schema: &Value) {
            $(crate::contract::check(schema, &$name);)*
        }
    };
    (@body) => { () };
    (@body $body:ty) => { $body };
}

endpoints! {
    PLAYERS: GET "/players" -> Vec<Player>;
    ACTIVE_MEETUP: GET "/meetups/active" -> Meetup;
    LINEUP: PUT "/meetups/{meetup_id}/lineup" (LineupBody) -> Meetup;
    SUBSTITUTE_SEARCH: POST "/meetups/{meetup_id}/substitute-search" -> Meetup;
    EVENTS: GET "/events" -> Event;
}

/// One PyBall call, sending an `In` (`()` for no body) and answering with an `Out`.
pub struct Endpoint<In, Out> {
    pub method: &'static str,
    pub path: &'static str,
    types: PhantomData<fn(In) -> Out>,
}

impl<In, Out> Endpoint<In, Out> {
    const fn new(method: &'static str, path: &'static str) -> Self {
        Self {
            method,
            path,
            types: PhantomData,
        }
    }

    /// The path for one meetup, and how errors name the call.
    fn at(&self, meetup_id: &str) -> (String, String) {
        let path = self.path.replace("{meetup_id}", meetup_id);
        let what = format!("{} {path}", self.method);
        (path, what)
    }
}

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
        self.call(&PLAYERS, "").context("decoding players")
    }

    /// The meetup not closed yet, or `None` if there isn't one.
    pub fn active_meetup(&self) -> Result<Option<Meetup>> {
        let resp = self.request(&self.http, &ACTIVE_MEETUP, "", None)?;
        if resp.status() == StatusCode::NOT_FOUND {
            return Ok(None);
        }
        let resp = check(resp, &ACTIVE_MEETUP.at("").1)?;
        Ok(Some(
            json_body(&ACTIVE_MEETUP, resp).context("decoding the active meetup")?,
        ))
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
        self.call_with(&LINEUP, meetup_id, &body)
            .context("decoding the meetup")
    }

    pub fn open_substitute_search(&self, meetup_id: &str) -> Result<Meetup> {
        self.call(&SUBSTITUTE_SEARCH, meetup_id)
            .context("decoding the meetup")
    }

    /// Open the event stream after `last_event_id` (only new events if `None`).
    pub fn events(&self, last_event_id: Option<u64>) -> Result<EventStream<Event>> {
        let (path, what) = EVENTS.at("");
        let mut req = self
            .builder(&EVENTS, &path)
            .header("Accept", "text/event-stream");
        if let Some(id) = last_event_id {
            req = req.header("Last-Event-ID", id.to_string());
        }
        let sent = self.stream.run(req.body(())?);
        let resp = sent.with_context(|| format!("cannot reach PyBall at {}", self.base))?;
        let resp = check(resp, &what)?;
        Ok(EventStream::new(&EVENTS, resp.into_body().into_reader()))
    }

    /// Call a bodyless `endpoint` for `meetup_id` and decode its answer.
    fn call<Out: DeserializeOwned>(
        &self,
        endpoint: &Endpoint<(), Out>,
        meetup_id: &str,
    ) -> Result<Out> {
        json_body(endpoint, self.send(&self.http, endpoint, meetup_id, None)?)
    }

    /// Call `endpoint` for `meetup_id` with `body` as JSON and decode its answer.
    fn call_with<In: Serialize, Out: DeserializeOwned>(
        &self,
        endpoint: &Endpoint<In, Out>,
        meetup_id: &str,
        body: &In,
    ) -> Result<Out> {
        let json = Some(serde_json::to_vec(body)?);
        json_body(endpoint, self.send(&self.http, endpoint, meetup_id, json)?)
    }

    /// Call `endpoint` for `meetup_id` with an optional JSON body; fail on any error status.
    fn send<In, Out>(
        &self,
        agent: &Agent,
        endpoint: &Endpoint<In, Out>,
        meetup_id: &str,
        json: Option<Vec<u8>>,
    ) -> Result<Response<Body>> {
        let resp = self.request(agent, endpoint, meetup_id, json)?;
        check(resp, &endpoint.at(meetup_id).1)
    }

    /// Call `endpoint`, handing back whatever status PyBall answered with.
    fn request<In, Out>(
        &self,
        agent: &Agent,
        endpoint: &Endpoint<In, Out>,
        meetup_id: &str,
        json: Option<Vec<u8>>,
    ) -> Result<Response<Body>> {
        let (path, _) = endpoint.at(meetup_id);
        let req = self.builder(endpoint, &path);
        let sent = match (json, endpoint.method) {
            (Some(body), _) => {
                agent.run(req.header("Content-Type", "application/json").body(body)?)
            }
            (None, "GET") => agent.run(req.body(())?),
            (None, _) => agent.run(req.body(Vec::new())?), // Content-Length: 0, not chunked
        };
        sent.with_context(|| format!("cannot reach PyBall at {}", self.base))
    }

    fn builder<In, Out>(&self, endpoint: &Endpoint<In, Out>, path: &str) -> request::Builder {
        Request::builder()
            .method(endpoint.method)
            .uri(format!("{}{path}", self.base))
            .header("Authorization", format!("Bearer {}", self.token))
    }
}

/// Reads server-sent events one at a time, each decoded as its endpoint's `Out`.
pub struct EventStream<Out> {
    lines: std::io::Lines<BufReader<Box<dyn Read + Send + Sync + 'static>>>,
    out: PhantomData<fn() -> Out>,
}

/// What the stream gave: an event, or a keepalive comment (sent every 15 s when idle).
pub enum Frame<Out> {
    Event(Box<Out>),
    Keepalive,
}

impl<Out: DeserializeOwned> EventStream<Out> {
    fn new<In>(_: &Endpoint<In, Out>, reader: impl Read + Send + Sync + 'static) -> Self {
        let boxed: Box<dyn Read + Send + Sync> = Box::new(reader);
        Self {
            lines: BufReader::new(boxed).lines(),
            out: PhantomData,
        }
    }

    /// The next frame, or `None` when PyBall closes the stream.
    pub fn next_frame(&mut self) -> Result<Option<Frame<Out>>> {
        let mut data = String::new();
        for line in self.lines.by_ref() {
            let line = line.context("reading the event stream")?;
            if line.is_empty() {
                if data.is_empty() {
                    continue;
                }
                let event: Out = serde_json::from_str(&data).context("decoding an event")?;
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

/// Decode `endpoint`'s answer as the type its table entry declares.
fn json_body<In, Out: DeserializeOwned>(
    _: &Endpoint<In, Out>,
    mut resp: Response<Body>,
) -> Result<Out> {
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
        let mut stream = EventStream::new(&EVENTS, std::io::Cursor::new(raw.into_bytes()));
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
