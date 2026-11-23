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

//! How PyBall runs a plugin: the environment it sets, the plugin's own table in
//! `config.toml` and the `data/plugins/<name>/` folder where the plugin keeps its state.

use std::fs;
use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use toml::Value;

/// Where the plugin API is when `PYBALL_API_URL` is not set, e.g. a command run by hand.
pub const DEFAULT_API_URL: &str = "http://127.0.0.1:8000/api/v1";

/// `PYBALL_API_URL` without its trailing `/`, or [`DEFAULT_API_URL`].
pub fn api_url(given: Option<String>) -> String {
    given
        .unwrap_or_else(|| DEFAULT_API_URL.into())
        .trim_end_matches('/')
        .to_string()
}

/// `PYBALL_API_TOKEN`, which PyBall sets; by hand, the manage token.
pub fn api_token(given: Option<String>) -> Result<String> {
    given.context(
        "PYBALL_API_TOKEN is not set: PyBall sets it for the plugin; \
         by hand, pass the manage token",
    )
}

/// An environment variable, `None` when unset or empty.
pub fn env(var: &str) -> Option<String> {
    std::env::var(var).ok().filter(|v| !v.is_empty())
}

/// The plugin's `[pyball.plugins.<name>]` table in PyBall's `config.toml`, if any.
pub fn table(config_path: &Path, name: &str) -> Result<Option<toml::Table>> {
    let raw = fs::read_to_string(config_path)
        .with_context(|| format!("reading PyBall config {}", config_path.display()))?;
    let doc: Value =
        toml::from_str(&raw).with_context(|| format!("parsing {}", config_path.display()))?;
    Ok(doc
        .get("pyball")
        .and_then(|p| p.get("plugins"))
        .and_then(|p| p.get(name))
        .and_then(Value::as_table)
        .cloned())
}

/// A value of the plugin's table as a string; numbers are accepted too (chat IDs).
pub fn string(t: Option<&toml::Table>, name: &str, key: &str) -> Result<Option<String>> {
    Ok(match t.and_then(|t| t.get(key)) {
        None => None,
        Some(Value::String(s)) if s.trim().is_empty() => None,
        Some(Value::String(s)) => Some(s.trim().to_string()),
        Some(Value::Integer(n)) => Some(n.to_string()),
        Some(_) => bail!("plugins.{name}.{key} must be a text or a number"),
    })
}

/// The plugin's own folder, `data/plugins/<name>/`, relative to the workspace.
pub fn data_dir(name: &str) -> PathBuf {
    Path::new("data/plugins").join(name)
}

/// The id of the last event the plugin handled, or `None` before the first one.
pub fn load_event_id(path: &Path) -> Result<Option<u64>> {
    if !path.exists() {
        return Ok(None);
    }
    let raw = fs::read_to_string(path).with_context(|| format!("reading {}", path.display()))?;
    let id = raw
        .trim()
        .parse()
        .with_context(|| format!("parsing {}", path.display()))?;
    Ok(Some(id))
}

pub fn save_event_id(path: &Path, id: u64) -> Result<()> {
    write_atomic(path, &format!("{id}\n"))
}

/// Write through a temp file + rename, so a crash never leaves half a file. The temp
/// name carries the process id: the plugin and a command run by hand may write at once.
pub fn write_atomic(path: &Path, contents: &str) -> Result<()> {
    if let Some(dir) = path.parent().filter(|d| !d.as_os_str().is_empty()) {
        fs::create_dir_all(dir)?;
    }
    let mut tmp = path.as_os_str().to_owned();
    tmp.push(format!(".tmp.{}", std::process::id()));
    fs::write(&tmp, contents)?;
    fs::rename(&tmp, path).with_context(|| format!("writing {}", path.display()))
}

#[cfg(test)]
mod tests {
    use super::*;

    #[test]
    fn event_id_round_trips_and_starts_unset() {
        let dir = std::env::temp_dir().join(format!("pyball-client-{}", std::process::id()));
        let path = dir.join("nested/last_event_id");
        assert_eq!(load_event_id(&path).unwrap(), None);
        save_event_id(&path, 42).unwrap();
        assert_eq!(load_event_id(&path).unwrap(), Some(42));
        fs::remove_dir_all(dir).unwrap();
    }

    #[test]
    fn reads_text_or_numbers_from_the_table() {
        let t: toml::Table = toml::from_str("a = \" x \"\nb = -100\nc = \"\"\nd = true").unwrap();
        assert_eq!(string(Some(&t), "p", "a").unwrap().as_deref(), Some("x"));
        assert_eq!(string(Some(&t), "p", "b").unwrap().as_deref(), Some("-100"));
        assert_eq!(string(Some(&t), "p", "c").unwrap(), None);
        assert!(string(Some(&t), "p", "d").is_err());
        assert_eq!(api_url(Some("http://x/api/v1/".into())), "http://x/api/v1");
        assert!(api_token(None).is_err());
    }
}
