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

//! Meetups: creating, finding, cancelling them and changing their roster, capacity and
//! substitute search. Every write is checked in `data/meetups/` too.

use pyball_contract::{CLOSED_MEETUP, Core, player};
use serde_json::{Value, json};

const DATE: &str = "2026-12-02T20:00:00";
const UNKNOWN: &str = "20000000-0000-4000-8000-000000000099";

#[test]
fn a_new_meetup_takes_the_club_defaults_and_is_saved() {
    let core = Core::start();
    let meetup = core.create_meetup(DATE);
    let expected = json!({
        "id": meetup["id"], "date": DATE, "location": "Campo", "capacity": 10,
        "substitute_search": false, "players": [], "teams": null, "matches": [],
        "closed": false,
    });
    assert_eq!(meetup, expected);
    assert_eq!(core.meetup_file(&meetup), meetup);
}

#[test]
fn a_new_meetup_takes_the_given_location_and_capacity() {
    let core = Core::start();
    let body = json!({ "date": DATE, "location": "Otro campo", "capacity": 14 });
    let reply = core.call("POST", "/meetups", &[], Some(body));
    assert_eq!(reply.status, 201);
    assert_eq!(
        (&reply.json["location"], &reply.json["capacity"]),
        (&json!("Otro campo"), &json!(14))
    );
    assert_eq!(core.meetup_file(&reply.json), reply.json);
}

#[test]
fn a_second_meetup_at_the_same_date_is_a_conflict() {
    let core = Core::start();
    let first = core.create_meetup(DATE);
    let reply = core.call(
        "POST",
        "/meetups",
        &[],
        Some(json!({ "date": DATE, "capacity": 12 })),
    );
    assert_eq!(reply.status, 409);
    assert_eq!(core.meetup_file(&first), first);
}

#[test]
fn an_invalid_meetup_body_is_rejected() {
    let core = Core::start();
    for body in [
        json!({}),
        json!({ "date": "mañana" }),
        json!({ "date": DATE, "capacity": 1 }),
    ] {
        assert_eq!(
            core.call("POST", "/meetups", &[], Some(body.clone()))
                .status,
            422,
            "{body}"
        );
    }
}

#[test]
fn a_meetup_is_found_by_its_date() {
    let core = Core::start();
    let meetup = core.create_meetup(DATE);
    let found = core.call("GET", &format!("/meetups?date={DATE}"), &[], None);
    assert_eq!((found.status, found.json), (200, json!([meetup])));
    let none = core.call("GET", "/meetups?date=2026-12-09T20:00:00", &[], None);
    assert_eq!((none.status, none.json), (200, json!([])));
    assert_eq!(core.call("GET", "/meetups", &[], None).status, 422);
}

#[test]
fn the_active_meetup_is_the_latest_one_not_closed() {
    let core = Core::start();
    assert_eq!(core.call("GET", "/meetups/active", &[], None).status, 404);
    core.create_meetup(DATE);
    let latest = core.create_meetup("2026-12-09T20:00:00");
    let reply = core.call("GET", "/meetups/active", &[], None);
    assert_eq!((reply.status, reply.json), (200, latest));
}

#[test]
fn cancelling_the_active_meetup_deletes_it() {
    let core = Core::start();
    let meetup = core.create_meetup(DATE);
    let id = meetup["id"].as_str().unwrap();
    let reply = core.call("DELETE", "/meetups/{meetup_id}", &[id], None);
    assert_eq!((reply.status, reply.json), (200, meetup));
    assert!(
        core.data_path("meetups/2026-12-02T20:00.json")
            .metadata()
            .is_err()
    );
    assert_eq!(core.call("GET", "/meetups/active", &[], None).status, 404);
}

#[test]
fn only_the_active_meetup_can_be_cancelled() {
    let core = Core::start();
    let older = core.create_meetup(DATE);
    core.create_meetup("2026-12-09T20:00:00");
    let older_id = older["id"].as_str().unwrap();
    assert_eq!(
        core.call("DELETE", "/meetups/{meetup_id}", &[older_id], None)
            .status,
        409
    );
    assert_eq!(
        core.call("DELETE", "/meetups/{meetup_id}", &[CLOSED_MEETUP], None)
            .status,
        409
    );
    assert_eq!(core.meetup_file(&older), older);
}

#[test]
fn an_unknown_or_malformed_meetup_id_is_not_found() {
    let core = Core::start();
    core.create_meetup(DATE);
    let p1 = player(1);
    for id in [UNKNOWN, "not-an-id"] {
        let calls = [
            ("DELETE", "/meetups/{meetup_id}", vec![id]),
            (
                "PUT",
                "/meetups/{meetup_id}/players/{player_id}",
                vec![id, &p1],
            ),
            (
                "DELETE",
                "/meetups/{meetup_id}/players/{player_id}",
                vec![id, &p1],
            ),
            ("POST", "/meetups/{meetup_id}/substitute-search", vec![id]),
            ("DELETE", "/meetups/{meetup_id}/substitute-search", vec![id]),
        ];
        for (method, template, params) in calls {
            assert_eq!(
                core.call(method, template, &params, None).status,
                404,
                "{method} {template} {id}"
            );
        }
        let reply = core.call(
            "PUT",
            "/meetups/{meetup_id}/capacity",
            &[id],
            Some(json!({ "capacity": 12 })),
        );
        assert_eq!(reply.status, 404, "capacity {id}");
    }
}

#[test]
fn a_player_joins_once_and_leaves() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let p1 = player(1);
    let joined = join(&core, &id, &p1);
    assert_eq!(joined["players"], json!([p1]));
    assert_eq!(core.meetup_file(&joined), joined);
    assert_eq!(join(&core, &id, &p1), joined);
    let left = core.call(
        "DELETE",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, &p1],
        None,
    );
    assert_eq!((left.status, &left.json["players"]), (200, &json!([])));
    assert_eq!(core.meetup_file(&left.json), left.json);
}

#[test]
fn players_may_join_past_the_capacity() {
    let core = Core::start();
    let body = json!({ "date": DATE, "capacity": 2 });
    let id = core.call("POST", "/meetups", &[], Some(body)).json["id"]
        .as_str()
        .unwrap()
        .to_owned();
    for n in 1..=3 {
        join(&core, &id, &player(n));
    }
    let active = core.call("GET", "/meetups/active", &[], None).json;
    assert_eq!(active["players"], json!([player(1), player(2), player(3)]));
}

#[test]
fn roster_changes_are_refused_when_they_cannot_apply() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let unknown = core.call(
        "PUT",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, UNKNOWN],
        None,
    );
    assert_eq!(unknown.status, 422);
    let absent = core.call(
        "DELETE",
        "/meetups/{meetup_id}/players/{player_id}",
        &[&id, &player(1)],
        None,
    );
    assert_eq!(absent.status, 409);
    let p11 = player(11);
    let closed = core.call(
        "PUT",
        "/meetups/{meetup_id}/players/{player_id}",
        &[CLOSED_MEETUP, &p11],
        None,
    );
    assert_eq!(closed.status, 409);
}

#[test]
fn the_capacity_changes_and_is_saved() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let reply = core.call(
        "PUT",
        "/meetups/{meetup_id}/capacity",
        &[&id],
        Some(json!({ "capacity": 12 })),
    );
    assert_eq!((reply.status, &reply.json["capacity"]), (200, &json!(12)));
    assert_eq!(core.meetup_file(&reply.json), reply.json);
    let low = core.call(
        "PUT",
        "/meetups/{meetup_id}/capacity",
        &[&id],
        Some(json!({ "capacity": 1 })),
    );
    assert_eq!(low.status, 422);
    let body = json!({ "capacity": 12 });
    assert_eq!(
        core.call(
            "PUT",
            "/meetups/{meetup_id}/capacity",
            &[CLOSED_MEETUP],
            Some(body)
        )
        .status,
        409
    );
}

#[test]
fn the_substitute_search_opens_once_and_closes() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let opened = core.call(
        "POST",
        "/meetups/{meetup_id}/substitute-search",
        &[&id],
        None,
    );
    assert_eq!(
        (opened.status, &opened.json["substitute_search"]),
        (200, &json!(true))
    );
    assert_eq!(core.meetup_file(&opened.json), opened.json);
    let again = core.call(
        "POST",
        "/meetups/{meetup_id}/substitute-search",
        &[&id],
        None,
    );
    assert_eq!((again.status, again.json), (200, opened.json));
    let closed = core.call(
        "DELETE",
        "/meetups/{meetup_id}/substitute-search",
        &[&id],
        None,
    );
    assert_eq!(
        (closed.status, &closed.json["substitute_search"]),
        (200, &json!(false))
    );
    assert_eq!(core.meetup_file(&closed.json), closed.json);
}

#[test]
fn reaching_the_capacity_closes_the_substitute_search() {
    let core = Core::start();
    let body = json!({ "date": DATE, "capacity": 2 });
    let id = core.call("POST", "/meetups", &[], Some(body)).json["id"]
        .as_str()
        .unwrap()
        .to_owned();
    join(&core, &id, &player(1));
    core.call(
        "POST",
        "/meetups/{meetup_id}/substitute-search",
        &[&id],
        None,
    );
    let full = join(&core, &id, &player(13));
    assert_eq!(full["substitute_search"], json!(false));
    let reopen = core.call(
        "POST",
        "/meetups/{meetup_id}/substitute-search",
        &[&id],
        None,
    );
    assert_eq!(reopen.status, 409);
    let search = "/meetups/{meetup_id}/substitute-search";
    assert_eq!(
        core.call("POST", search, &[CLOSED_MEETUP], None).status,
        409
    );
}

#[test]
fn meetup_operations_need_a_token() {
    let core = Core::start();
    let id = core.create_meetup(DATE)["id"].as_str().unwrap().to_owned();
    let roster = format!("/meetups/{id}/players/{}", player(1));
    let calls = [
        ("GET", format!("/meetups?date={DATE}")),
        ("POST", "/meetups".to_owned()),
        ("GET", "/meetups/active".to_owned()),
        ("DELETE", format!("/meetups/{id}")),
        ("PUT", roster.clone()),
        ("DELETE", roster),
        ("PUT", format!("/meetups/{id}/capacity")),
        ("POST", format!("/meetups/{id}/substitute-search")),
        ("DELETE", format!("/meetups/{id}/substitute-search")),
    ];
    for (method, path) in calls {
        let status = core.request(method, &path, None).send().unwrap().status();
        assert_eq!(status, 401, "{method} {path}");
    }
}

fn join(core: &Core, meetup_id: &str, player_id: &str) -> Value {
    let reply = core.call(
        "PUT",
        "/meetups/{meetup_id}/players/{player_id}",
        &[meetup_id, player_id],
        None,
    );
    assert_eq!(reply.status, 200, "{reply:?}");
    reply.json
}
