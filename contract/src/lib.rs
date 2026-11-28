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

//! Harness of the contract suite: starts the core under test on a temporary workspace and
//! talks to it only over HTTP and through its `data/` files.
//!
//! `PYBALL_CORE_CMD` is the shell command that starts the core, run with the workspace as
//! its working directory; it must read `./config.toml` and serve on its `api_port`.

use std::fs::{self, File};
use std::io::{BufRead, BufReader};
use std::net::TcpListener;
use std::os::unix::process::CommandExt;
use std::path::{Path, PathBuf};
use std::process::{Child, Command, Stdio};
use std::sync::LazyLock;
use std::thread::sleep;
use std::time::{Duration, Instant};

use reqwest::Method;
use reqwest::blocking::{Client, Response};
use serde_json::{Value, json};
use tempfile::TempDir;

/// The closed meetup in the fixture, with its classic match already played.
pub const CLOSED_MEETUP: &str = "10000000-0000-4000-8000-000000000001";

/// The id of fixture player `n`: 1 to 12 are regulars, 13 and 14 substitutes.
pub fn player(n: u32) -> String {
    format!("00000000-0000-4000-8000-{n:012}")
}

/// A core running on its own workspace, stopped when dropped.
pub struct Core {
    child: Child,
    base: String,
    token: String,
    client: Client,
    workspace: TempDir,
}

/// The status and JSON body of a response; the body is `Null` when it is not JSON.
#[derive(Debug)]
pub struct Reply {
    pub status: u16,
    pub json: Value,
}

impl Core {
    /// Start a core on a fresh copy of `fixtures/club`, retrying when its port was taken.
    pub fn start() -> Self {
        let mut last = String::new();
        for _ in 0..3 {
            match Self::try_start() {
                Ok(core) => return core,
                Err(log) => last = log,
            }
        }
        panic!("the core did not start:\n{last}");
    }

    /// Call `template` (an `openapi.json` path, with `{...}` filled from `params` in
    /// order, and an optional `?query`) and check a JSON reply against its schema.
    pub fn call(
        &self,
        method: &str,
        template: &str,
        params: &[&str],
        body: Option<Value>,
    ) -> Reply {
        let mut path = template.to_owned();
        for param in params {
            let start = path.find('{').expect("more params than placeholders");
            let end = start + path[start..].find('}').unwrap();
            path.replace_range(start..=end, param);
        }
        let mut request = self.request(method, &path, Some(&self.token));
        if let Some(body) = body {
            request = request.json(&body);
        }
        let response = request.send().expect("request failed");
        let status = response.status().as_u16();
        let json = response.json().unwrap_or(Value::Null);
        check_schema(method, template.split('?').next().unwrap(), status, &json);
        Reply { status, json }
    }

    /// A raw request to `path` under `/api/v1`, with `token` as bearer if any.
    pub fn request(
        &self,
        method: &str,
        path: &str,
        token: Option<&str>,
    ) -> reqwest::blocking::RequestBuilder {
        let method = Method::from_bytes(method.as_bytes()).unwrap();
        let request = self.client.request(method, format!("{}{path}", self.base));
        match token {
            Some(token) => request.bearer_auth(token),
            None => request,
        }
    }

    /// Create a meetup at `date` with the club's defaults and return it.
    pub fn create_meetup(&self, date: &str) -> Value {
        let reply = self.call("POST", "/meetups", &[], Some(json!({ "date": date })));
        assert_eq!(reply.status, 201, "{reply:?}");
        reply.json
    }

    /// Open the event stream at `path` (`/events` with an optional query).
    pub fn events(&self, path: &str, last_event_id: Option<u64>) -> Events {
        let mut request = self
            .request("GET", path, Some(&self.token))
            .timeout(Duration::from_secs(10));
        if let Some(id) = last_event_id {
            request = request.header("Last-Event-ID", id.to_string());
        }
        let response = request.send().expect("request failed");
        assert_eq!(response.status(), 200);
        Events {
            reader: BufReader::new(response),
        }
    }

    /// Parse `data/<relative>` as JSON.
    pub fn data(&self, relative: &str) -> Value {
        let text = fs::read_to_string(self.data_dir().join(relative)).expect("missing data file");
        serde_json::from_str(&text).expect("data file is not JSON")
    }

    /// Every event in `data/events.jsonl`, in order.
    pub fn event_log(&self) -> Vec<Value> {
        let text = fs::read_to_string(self.data_dir().join("events.jsonl")).unwrap_or_default();
        text.lines()
            .map(|line| serde_json::from_str(line).unwrap())
            .collect()
    }

    fn data_dir(&self) -> PathBuf {
        self.workspace.path().join("data")
    }

    fn try_start() -> Result<Self, String> {
        let workspace = TempDir::new().unwrap();
        copy_dir(
            &Path::new(env!("CARGO_MANIFEST_DIR")).join("fixtures/club"),
            &workspace.path().join("data"),
        );
        // A token per core, so a core that lost the race for its port never answers as ours.
        let token = workspace
            .path()
            .file_name()
            .unwrap()
            .to_string_lossy()
            .into_owned();
        let port = TcpListener::bind("127.0.0.1:0")
            .unwrap()
            .local_addr()
            .unwrap()
            .port();
        fs::write(workspace.path().join("config.toml"), config(port, &token)).unwrap();
        let log_path = workspace.path().join("core.log");
        let log = File::create(&log_path).unwrap();
        let child = Command::new("sh")
            .arg("-c")
            .arg(format!("exec {}", core_cmd()))
            .current_dir(workspace.path())
            .stdout(log.try_clone().unwrap())
            .stderr(log)
            .process_group(0)
            .spawn()
            .expect("cannot run PYBALL_CORE_CMD");
        let mut core = Core {
            child,
            base: format!("http://127.0.0.1:{port}/api/v1"),
            token,
            client: Client::builder()
                .timeout(Duration::from_secs(30))
                .build()
                .unwrap(),
            workspace,
        };
        let log = || fs::read_to_string(&log_path).unwrap_or_default();
        let deadline = Instant::now() + Duration::from_secs(120);
        loop {
            if let Ok(Some(status)) = core.child.try_wait() {
                return Err(format!("the core exited with {status}:\n{}", log()));
            }
            let ready = core.request("GET", "/settings", Some(&core.token)).send();
            if ready.is_ok_and(|r| r.status().is_success()) {
                return Ok(core);
            }
            if Instant::now() > deadline {
                return Err(format!("the core did not answer in time:\n{}", log()));
            }
            sleep(Duration::from_millis(100));
        }
    }
}

impl Drop for Core {
    /// Stop the whole process group: `sh`, a wrapper such as `uv run`, and the core.
    fn drop(&mut self) {
        let group = format!("-{}", self.child.id());
        let _ = Command::new("kill").args(["-TERM", "--", &group]).status();
        let deadline = Instant::now() + Duration::from_secs(10);
        while self.child.try_wait().ok().flatten().is_none() && Instant::now() < deadline {
            sleep(Duration::from_millis(50));
        }
        // Usually the group is gone by now; this reaps whatever ignored SIGTERM.
        let _ = Command::new("kill")
            .args(["-KILL", "--", &group])
            .stderr(Stdio::null())
            .status();
        let _ = self.child.wait();
    }
}

/// An open server-sent event stream.
pub struct Events {
    reader: BufReader<Response>,
}

impl Events {
    /// The next event's JSON data, checked against its `id:` and `event:` fields.
    pub fn next_event(&mut self) -> Value {
        let (mut id, mut kind, mut data): (_, Option<String>, Option<String>) = (None, None, None);
        loop {
            let mut line = String::new();
            assert!(
                self.reader
                    .read_line(&mut line)
                    .expect("stream read failed")
                    > 0,
                "stream ended"
            );
            let line = line.trim_end_matches(['\r', '\n']);
            if line.is_empty() {
                if let Some(data) = data.take() {
                    let event: Value = serde_json::from_str(&data).unwrap();
                    check_schema_ref("EventOut", &event);
                    assert_eq!(id, Some(event["id"].to_string()), "SSE id of {event}");
                    assert_eq!(
                        kind.as_deref(),
                        event["type"].as_str(),
                        "SSE event of {event}"
                    );
                    return event;
                }
            } else if let Some(value) = line.strip_prefix("id: ") {
                id = Some(value.to_owned());
            } else if let Some(value) = line.strip_prefix("event: ") {
                kind = Some(value.to_owned());
            } else if let Some(value) = line.strip_prefix("data: ") {
                data = Some(value.to_owned());
            }
        }
    }
}

static OPENAPI: LazyLock<Value> =
    LazyLock::new(|| serde_json::from_str(include_str!("../../plugins/openapi.json")).unwrap());

/// Check `body` against the schema `openapi.json` documents for this response, if any.
fn check_schema(method: &str, path: &str, status: u16, body: &Value) {
    let operation = &OPENAPI["paths"][path][method.to_lowercase()];
    assert!(
        !operation.is_null(),
        "{method} {path} is not in openapi.json"
    );
    let schema =
        &operation["responses"][status.to_string()]["content"]["application/json"]["schema"];
    if !schema.is_null() {
        validate(schema, body, &format!("{method} {path} {status}"));
    }
}

fn check_schema_ref(name: &str, body: &Value) {
    validate(
        &json!({ "$ref": format!("#/components/schemas/{name}") }),
        body,
        name,
    );
}

fn validate(schema: &Value, body: &Value, what: &str) {
    // The schema's $refs point into #/components, so it is validated with them beside it.
    let mut root = schema.clone();
    root["components"] = OPENAPI["components"].clone();
    let validator = jsonschema::draft202012::new(&root).expect("invalid schema");
    if let Err(error) = validator.validate(body) {
        panic!("{what} does not match openapi.json: {error}\n{body:#}");
    }
}

fn core_cmd() -> String {
    std::env::var("PYBALL_CORE_CMD").unwrap_or_else(|_| {
        let repo = Path::new(env!("CARGO_MANIFEST_DIR")).parent().unwrap();
        format!("uv run --project '{}' pyball", repo.display())
    })
}

fn config(port: u16, token: &str) -> String {
    format!(
        r#"[pyball.core]
location = "Campo"
name = "Contrato"
default_week_day = "wednesday"
default_hour = "20:00"
base_url = "http://localhost"
team_colors = ["blanco", "negro"]
locale = "en_US.UTF-8"
display_date_format = "%Y-%m-%d %H:%M"
data_dir = "data"
api_port = {port}
manage_token = "{token}"
meetup_capacity = 10
"#
    )
}

fn copy_dir(from: &Path, to: &Path) {
    fs::create_dir_all(to).unwrap();
    for entry in fs::read_dir(from).unwrap() {
        let entry = entry.unwrap();
        if entry.file_type().unwrap().is_dir() {
            copy_dir(&entry.path(), &to.join(entry.file_name()));
        } else {
            fs::copy(entry.path(), to.join(entry.file_name())).unwrap();
        }
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    #[should_panic(expected = "does not match openapi.json")]
    fn a_body_off_the_schema_fails() {
        check_schema("GET", "/players", 200, &json!([{ "id": 1, "name": "Ana" }]));
    }

    #[test]
    fn a_body_on_the_schema_passes() {
        let body =
            json!([{ "id": player(1), "name": "Ana", "group": "regular", "position": null }]);
        check_schema("GET", "/players", 200, &body);
    }
}
