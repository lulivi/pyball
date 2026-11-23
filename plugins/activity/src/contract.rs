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

//! activity against PyBall's committed plugin contract, `plugins/openapi.json`.
//!
//! The event stream's schema becomes sample JSON that activity's own types must decode,
//! and every field they read must be in it. A renamed field, a changed type or a field
//! that became nullable fails here once the schema is regenerated.

use pyball_client::contract::operation;
use serde_json::Value;

use crate::api::{EVENTS, check_endpoints};

const SCHEMA: &str = include_str!("../../openapi.json");

#[test]
fn every_call_activity_makes_matches_the_schema() {
    let schema: Value = serde_json::from_str(SCHEMA).unwrap();
    check_endpoints(&schema);
}

#[test]
fn the_client_calls_pyball_only_through_its_endpoints() {
    // A path written anywhere but the endpoints! table would go unchecked.
    for source in [include_str!("main.rs"), include_str!("target.rs")] {
        assert!(
            !source.contains("\"/"),
            "activity builds a PyBall path outside endpoints!: declare the call in api.rs"
        );
    }
}

#[test]
fn activity_can_resume_the_event_stream() {
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
