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

//! The stats image, of the season or of all time.

use pyball_contract::Core;

const PNG_SIGNATURE: &[u8] = b"\x89PNG\r\n\x1a\n";

#[test]
fn the_stats_image_is_a_png_for_each_scope() {
    let core = Core::start();
    for query in ["", "?scope=season", "?scope=alltime"] {
        let response = core
            .request("GET", &format!("/stats.png{query}"), Some(core.token()))
            .send()
            .unwrap();
        assert_eq!(response.status(), 200, "{query}");
        assert_eq!(response.headers()["content-type"], "image/png", "{query}");
        assert!(
            response.bytes().unwrap().starts_with(PNG_SIGNATURE),
            "{query}"
        );
    }
}

#[test]
fn an_unknown_scope_is_rejected() {
    let core = Core::start();
    assert_eq!(
        core.call("GET", "/stats.png?scope=forever", &[], None)
            .status,
        422
    );
}

#[test]
fn the_stats_image_needs_a_token() {
    let core = Core::start();
    assert_eq!(
        core.request("GET", "/stats.png", None)
            .send()
            .unwrap()
            .status(),
        401
    );
}
