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

//! The event stream and `data/events.jsonl`: what each write records, and replaying,
//! resuming and following the stream.

use std::thread::sleep;
use std::time::Duration;

use pyball_contract::{Core, player};
use serde_json::{Value, json};

const DATE: &str = "2026-12-02T20:00:00";

#[test]
fn each_write_records_its_event_with_the_meetup_after_it() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let (p1, p13) = (player(1), player(13));
    let roster = "/meetups/{meetup_id}/players/{player_id}";
    let search = "/meetups/{meetup_id}/substitute-search";
    let writes: [(&str, &str, Vec<&str>, Option<Value>); 9] = [
        ("PUT", roster, vec![&id, &p1], None),
        ("PUT", roster, vec![&id, &p1], None),
        ("POST", search, vec![&id], None),
        ("POST", search, vec![&id], None),
        ("PUT", roster, vec![&id, &p13], None),
        ("DELETE", search, vec![&id], None),
        ("DELETE", roster, vec![&id, &p13], None),
        (
            "PUT",
            "/meetups/{meetup_id}/capacity",
            vec![&id],
            Some(json!({ "capacity": 12 })),
        ),
        ("DELETE", "/meetups/{meetup_id}", vec![&id], None),
    ];
    let mut meetups = vec![core.call("GET", "/meetups/active", &[], None).json];
    for (method, template, params, body) in writes {
        let reply = core.call(method, template, &params, body);
        assert_eq!(reply.status, 200, "{method} {template}: {reply:?}");
        meetups.push(reply.json);
    }
    let log = core.event_log();
    let types: Vec<&str> = log
        .iter()
        .map(|event| event["type"].as_str().unwrap())
        .collect();
    assert_eq!(
        types,
        [
            "meetup.created",
            "player.joined",
            "substitute_search.opened",
            "player.joined",
            "meetup.updated",
            "substitute_search.closed",
            "player.left",
            "meetup.updated",
            "meetup.cancelled",
        ]
    );
    let ids: Vec<u64> = log
        .iter()
        .map(|event| event["id"].as_u64().unwrap())
        .collect();
    assert_eq!(ids, (1..=9).collect::<Vec<_>>());
    // The meetup of each event is the one the write that recorded it answered with.
    let after = [0, 1, 3, 5, 6, 6, 7, 8, 9];
    for (event, write) in log.iter().zip(after) {
        assert_eq!(event["meetup"], meetups[write], "{event}");
    }
    assert_eq!(
        (&log[1]["player"]["id"], &log[1]["is_substitute"]),
        (&json!(p1), &json!(false))
    );
    assert_eq!(
        (&log[3]["player"]["id"], &log[3]["is_substitute"]),
        (&json!(p13), &json!(true))
    );
    assert_eq!(log[3]["player"], core.data("players.json")["players"][12]);
}

#[test]
fn a_lineup_records_one_meetup_update() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let players: Vec<String> = (1..=10).map(player).collect();
    let body = json!({ "players": players, "team_algorithm": "random" });
    let reply = core.call("PUT", "/meetups/{meetup_id}/lineup", &[&id], Some(body));
    let log = core.event_log();
    assert_eq!(log.len(), 2);
    assert_eq!(log[1]["type"], "meetup.updated");
    assert_eq!(log[1]["meetup"], reply.json);
}

#[test]
fn the_stream_replays_the_whole_log_after_zero() {
    let core = Core::start();
    two_events(&core);
    let mut stream = core.events("/events?after=0", None);
    assert_eq!(
        [stream.next_event(), stream.next_event()],
        core.event_log()[..]
    );
}

#[test]
fn the_stream_resumes_after_the_last_event_seen() {
    let core = Core::start();
    two_events(&core);
    let second = core.event_log()[1].clone();
    assert_eq!(core.events("/events?after=1", None).next_event(), second);
    assert_eq!(core.events("/events", Some(1)).next_event(), second);
}

#[test]
fn the_stream_follows_live_events_after_the_backlog() {
    let core = Core::start();
    let id = two_events(&core);
    let mut stream = core.events("/events?after=1", None);
    assert_eq!(stream.next_event()["id"], 2);
    core.call(
        "DELETE",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, &player(1)],
        None,
    );
    let live = stream.next_event();
    assert_eq!(
        (&live["id"], &live["type"]),
        (&json!(3), &json!("player.left"))
    );
}

#[test]
fn the_stream_without_a_position_sends_only_new_events() {
    let core = Core::start();
    let id = two_events(&core);
    let mut stream = core.events("/events", None);
    // ponytail: a fixed wait for the core to subscribe the stream; a write sent before it
    // would be missed. Raise it if this test flakes on a slow machine.
    sleep(Duration::from_millis(500));
    core.call(
        "DELETE",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, &player(1)],
        None,
    );
    assert_eq!(stream.next_event()["id"], 3);
}

#[test]
fn the_stream_rejects_a_negative_position_and_needs_a_token() {
    let core = Core::start();
    assert_eq!(core.call("GET", "/events?after=-1", &[], None).status, 422);
    assert_eq!(
        core.request("GET", "/events", None)
            .send()
            .unwrap()
            .status(),
        401
    );
}

/// Create a meetup and have player 1 join it: events 1 and 2. Returns the meetup id.
fn two_events(core: &Core) -> String {
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    core.call(
        "PUT",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, &player(1)],
        None,
    );
    id
}
