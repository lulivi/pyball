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

//! Matches: setting a meetup's lineup and teams, and the summary of a closed meetup.

use pyball_contract::{CLOSED_MEETUP, Core, player};
use serde_json::{Value, json};

const DATE: &str = "2026-12-02T20:00:00";
const LINEUP: &str = "/meetups/{meetup_id}/lineup";

#[test]
fn a_lineup_alone_replaces_the_roster() {
    let core = Core::start();
    let id = new_meetup(&core);
    let players = json!([player(3), player(1), player(13)]);
    let reply = core.call("PUT", LINEUP, &[&id], Some(json!({ "players": players })));
    assert_eq!(reply.status, 200);
    assert_eq!(
        (&reply.json["players"], &reply.json["teams"]),
        (&players, &Value::Null)
    );
    assert_eq!(core.meetup_file(&reply.json), reply.json);
}

#[test]
fn a_lineup_with_an_algorithm_makes_the_teams() {
    for (count, names) in [(2, json!(["A", "B"])), (3, json!(["A", "B", "C"]))] {
        let core = Core::start();
        let id = new_meetup(&core);
        let players: Vec<String> = (1..=12).map(player).collect();
        let body = json!({ "players": players, "team_algorithm": "random", "team_count": count });
        let reply = core.call("PUT", LINEUP, &[&id], Some(body));
        assert_eq!(reply.status, 200, "{reply:?}");
        let teams = reply.json["teams"].as_array().unwrap();
        let team_names: Vec<_> = teams.iter().map(|team| team["name"].clone()).collect();
        assert_eq!(json!(team_names), names);
        let mut assigned: Vec<String> = teams
            .iter()
            .flat_map(|team| team["players"].as_array().unwrap().iter())
            .map(|id| id.as_str().unwrap().to_owned())
            .collect();
        assigned.sort();
        assert_eq!(assigned, players);
        // The file keeps the teams without their display color and emoji.
        let mut file_teams = reply.json["teams"].clone();
        for team in file_teams.as_array_mut().unwrap() {
            let team = team.as_object_mut().unwrap();
            team.remove("color");
            team.remove("emoji");
        }
        let mut expected = reply.json.clone();
        expected["teams"] = file_teams;
        let first = &reply.json["matches"][0]["teams"];
        expected["matches"] = json!([{ "teams_playing": first, "result": null }]);
        assert_eq!(core.meetup_file(&reply.json), expected);
    }
}

#[test]
fn an_invalid_lineup_is_rejected() {
    let core = Core::start();
    let id = new_meetup(&core);
    let players: Vec<String> = (1..=10).map(player).collect();
    let bodies = [
        json!({}),
        json!({ "players": [players[0], "20000000-0000-4000-8000-000000000099"] }),
        json!({ "players": players, "team_algorithm": "a dedo" }),
        json!({ "players": players, "team_algorithm": "random", "team_count": 4 }),
    ];
    for body in bodies {
        let reply = core.call("PUT", LINEUP, &[&id], Some(body.clone()));
        assert_eq!(reply.status, 422, "{body}");
    }
    let unchanged = core.call("GET", "/meetups/active", &[], None).json;
    assert_eq!(core.meetup_file(&unchanged), unchanged);
    assert_eq!(unchanged["players"], json!([]));
}

#[test]
fn a_lineup_is_refused_once_the_meetup_has_teams() {
    let core = Core::start();
    let body = json!({ "players": [player(1), player(2)] });
    assert_eq!(
        core.call("PUT", LINEUP, &[CLOSED_MEETUP], Some(body.clone()))
            .status,
        409
    );
    let unknown = "20000000-0000-4000-8000-000000000099";
    assert_eq!(core.call("PUT", LINEUP, &[unknown], Some(body)).status, 404);
}

#[test]
fn a_closed_meetup_has_a_summary_naming_its_scorers() {
    let core = Core::start();
    let reply = core.call(
        "GET",
        "/meetups/{meetup_id}/summary",
        &[CLOSED_MEETUP],
        None,
    );
    assert_eq!(reply.status, 200);
    let text = reply.json["text"].as_str().unwrap();
    for scorer in ["Dani", "Edu", "Hugo"] {
        assert!(text.contains(scorer), "{scorer} missing from:\n{text}");
    }
}

#[test]
fn only_a_closed_meetup_has_a_summary() {
    let core = Core::start();
    let id = new_meetup(&core);
    assert_eq!(
        core.call("GET", "/meetups/{meetup_id}/summary", &[&id], None)
            .status,
        409
    );
    let unknown = "20000000-0000-4000-8000-000000000099";
    assert_eq!(
        core.call("GET", "/meetups/{meetup_id}/summary", &[unknown], None)
            .status,
        404
    );
}

#[test]
fn match_operations_need_a_token() {
    let core = Core::start();
    for (method, path) in [
        ("PUT", format!("/meetups/{CLOSED_MEETUP}/lineup")),
        ("GET", format!("/meetups/{CLOSED_MEETUP}/summary")),
    ] {
        core.assert_unauthorized(method, &path, None);
    }
}

fn new_meetup(core: &Core) -> String {
    core.create_meetup(DATE)["id"].as_str().unwrap().to_owned()
}
