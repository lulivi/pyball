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

//! `/settings` and `/players`, and the bearer token every operation needs.

use pyball_contract::{Core, player};
use serde_json::json;

#[test]
fn settings_are_the_club_display_settings() {
    let core = Core::start();
    let reply = core.call("GET", "/settings", &[], None);
    assert_eq!(reply.status, 200);
    assert_eq!(
        reply.json,
        json!({ "display_date_format": "%Y-%m-%d %H:%M", "locale": "C.UTF-8" })
    );
}

#[test]
fn players_lists_every_player_in_the_data() {
    let core = Core::start();
    let reply = core.call("GET", "/players", &[], None);
    assert_eq!(reply.status, 200);
    assert_eq!(reply.json, core.data("players.json")["players"]);
    assert_eq!(reply.json[12]["id"], player(13));
}

#[test]
fn a_missing_or_wrong_token_is_unauthorized() {
    let core = Core::start();
    for path in ["/settings", "/players"] {
        for token in [None, Some("wrong")] {
            let status = core.request("GET", path, token).send().unwrap().status();
            assert_eq!(status, 401, "GET {path} with {token:?}");
        }
    }
}
