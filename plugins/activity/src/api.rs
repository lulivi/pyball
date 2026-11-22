//! activity's one call to PyBall's plugin API, the event stream, and what it reads.

use pyball_client::endpoints;
use serde::Deserialize;

endpoints! {
    EVENTS: GET "/events" -> Event;
}

/// One server-sent event, with only the fields the activity feed shows.
#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(serde::Serialize))]
pub struct Event {
    pub id: u64,
    #[serde(rename = "type")]
    pub kind: String,
    pub meetup: Meetup,
    /// Only on `player.joined` and `player.left`.
    pub player: Option<Player>,
    /// Only on `player.joined` and `player.left`.
    pub is_substitute: Option<bool>,
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(serde::Serialize))]
pub struct Meetup {
    /// `YYYY-MM-DDTHH:MM:SS`, PyBall's local time.
    pub date: String,
}

#[derive(Debug, Clone, Deserialize)]
#[cfg_attr(test, derive(serde::Serialize))]
pub struct Player {
    pub name: String,
}
