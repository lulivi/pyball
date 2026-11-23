//! siesta against PyBall's committed plugin contract, `plugins/openapi.json`.
//!
//! For each call siesta makes, the response schema becomes sample JSON that siesta's own
//! types must decode, and every field they read must be in it. A renamed field, a changed
//! type or a field that became nullable fails here once the schema is regenerated.

use pyball_client::contract::{Sample, operation};
use serde_json::Value;

use crate::api::{ACTIVE_MEETUP, EVENTS, LineupBody, check_endpoints};

const SCHEMA: &str = include_str!("../../openapi.json");

#[test]
fn every_call_siesta_makes_matches_the_schema() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    check_endpoints(&schema);
}

#[test]
fn the_client_calls_pyball_only_through_its_endpoints() {
    // A path written anywhere but the endpoints! table would go unchecked.
    let source = include_str!("api.rs");
    let table = source.find("endpoints! {").unwrap();
    let rest = &source[source[table..].find("\n}\n").unwrap() + table..];
    assert!(
        !rest.contains("\"/"),
        "api.rs builds a PyBall path outside endpoints!: declare the call there"
    );
}

#[test]
fn siesta_can_resume_the_event_stream() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let params = operation(&schema, &EVENTS)["parameters"]
        .as_array()
        .unwrap();
    assert!(
        params
            .iter()
            .any(|p| p["in"] == "header" && p["name"] == "last-event-id"),
        "GET /events no longer reads the Last-Event-ID header"
    );
}

#[test]
fn no_active_meetup_is_a_404() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    let responses = &operation(&schema, &ACTIVE_MEETUP)["responses"];
    assert!(
        responses.get("404").is_some(),
        "GET /meetups/active no longer answers 404 when there is no active meetup"
    );
}

impl Sample for LineupBody {
    fn sample() -> Option<Self> {
        Some(LineupBody {
            players: vec!["p1".to_string()],
            team_algorithm: "balanceado".to_string(),
        })
    }
}
