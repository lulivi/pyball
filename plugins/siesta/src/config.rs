//! Settings, read straight from PyBall's own config.toml.
//!
//! Uses `[pyball.core]` (manage_token, base_url, data_dir) and
//! `[pyball.telegram]` (bot_token, regulars.meetups.chat_id), honouring the
//! same `PYBALL_*` environment overrides PyBall does. Siesta-specific options
//! go in an optional `[pyball.siesta]` section, which PyBall ignores.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use toml::Value;

#[derive(Debug)]
pub struct Config {
    /// Where the PyBall API is reachable from this machine.
    pub api_url: String,
    /// How `api_url` was chosen, for log lines.
    pub api_url_source: &'static str,
    pub manage_token: String,
    pub max_players: usize,
    pub team_algorithm: String,
    pub state_file: PathBuf,
    pub telegram: Option<TelegramTarget>,
}

#[derive(Debug)]
pub struct TelegramTarget {
    pub bot_token: String,
    pub chat_id: String,
    /// `None` = the group's main ("General") chat.
    pub thread_id: Option<i64>,
}

impl Config {
    pub fn load(config_path: &Path) -> Result<Self> {
        let raw = std::fs::read_to_string(config_path)
            .with_context(|| format!("reading PyBall config {}", config_path.display()))?;
        let doc: Value =
            toml::from_str(&raw).with_context(|| format!("parsing {}", config_path.display()))?;
        let workspace = config_path
            .parent()
            .filter(|p| !p.as_os_str().is_empty())
            .unwrap_or(Path::new("."));

        let core = table(&doc, &["pyball", "core"]);
        let tg = table(&doc, &["pyball", "telegram"]);
        let meetups = table(&doc, &["pyball", "telegram", "regulars", "meetups"]);
        let siesta = table(&doc, &["pyball", "siesta"]);

        let manage_token = env_or("PYBALL_CORE_MANAGE_TOKEN", string(core, "manage_token"));
        // Relative to the current directory, exactly like PyBall resolves it.
        let data_dir = PathBuf::from(
            env_or("PYBALL_CORE_DATA_DIR", string(core, "data_dir"))
                .unwrap_or_else(|| "data".into()),
        );

        let (api_url, api_url_source) = resolve_api_url(siesta, core, workspace)?;

        let state_file = string(siesta, "state_file")
            .map_or_else(|| data_dir.join("siesta.json"), PathBuf::from);
        if let Some(dir) = state_file.parent().filter(|d| !d.as_os_str().is_empty())
            && !dir.is_dir()
        {
            bail!(
                "data folder {} not found (relative paths start from the current directory, \
                 like PyBall); run from the folder PyBall runs in",
                dir.display()
            );
        }

        let max_players = match siesta.and_then(|t| t.get("max_players")) {
            Some(v) => v
                .as_integer()
                .filter(|n| *n > 0)
                .context("pyball.siesta.max_players must be a positive number")?
                as usize,
            None => 10,
        };
        let team_algorithm =
            string(siesta, "team_algorithm").unwrap_or_else(|| "balanceado".into());
        if !matches!(team_algorithm.as_str(), "balanceado" | "aleatorio") {
            bail!("pyball.siesta.team_algorithm must be \"balanceado\" or \"aleatorio\"");
        }

        let bot_token =
            env_or("PYBALL_TELEGRAM_BOT_TOKEN", string(tg, "bot_token")).unwrap_or_default();
        let chat_id = env_or(
            "PYBALL_TELEGRAM_REGULARS_MEETUPS_CHAT_ID",
            string(meetups, "chat_id"),
        )
        .filter(|c| !c.is_empty() && c != "0");
        let thread_id = match siesta.and_then(|t| t.get("message_thread_id")) {
            Some(v) => parse_thread(v)?,
            None => None,
        };
        let telegram = match (bot_token.is_empty(), chat_id) {
            (false, Some(chat_id)) => Some(TelegramTarget {
                bot_token,
                chat_id,
                thread_id,
            }),
            _ => None,
        };

        Ok(Self {
            api_url,
            api_url_source,
            manage_token: manage_token.unwrap_or_default(),
            max_players,
            team_algorithm,
            state_file,
            telegram,
        })
    }
}

/// Pick the URL to reach PyBall's API:
/// 1. `[pyball.siesta] api_url`, if set;
/// 2. `http://127.0.0.1:<PORT>` from the workspace's `.env` (how compose publishes it);
/// 3. `[pyball.core] base_url`.
fn resolve_api_url(
    siesta: Option<&toml::Table>,
    core: Option<&toml::Table>,
    workspace: &Path,
) -> Result<(String, &'static str)> {
    if let Some(url) = env_or("PYBALL_SIESTA_API_URL", string(siesta, "api_url")) {
        return Ok((url, "pyball.siesta.api_url"));
    }
    if let Some(port) = dotenv_port(&workspace.join(".env")) {
        return Ok((format!("http://127.0.0.1:{port}"), "PORT in .env"));
    }
    if let Some(url) = env_or("PYBALL_CORE_BASE_URL", string(core, "base_url")) {
        return Ok((url, "pyball.core.base_url"));
    }
    bail!("can't tell where PyBall is: set [pyball.siesta] api_url in config.toml")
}

fn dotenv_port(path: &Path) -> Option<u16> {
    let raw = std::fs::read_to_string(path).ok()?;
    raw.lines()
        .filter_map(|l| l.trim().strip_prefix("PORT="))
        .find_map(|v| v.trim().trim_matches('"').trim_matches('\'').parse().ok())
}

fn table<'a>(doc: &'a Value, path: &[&str]) -> Option<&'a toml::Table> {
    let mut cur = doc;
    for key in path {
        cur = cur.get(key)?;
    }
    cur.as_table()
}

/// A config value as a string; numbers are accepted too (chat IDs).
fn string(t: Option<&toml::Table>, key: &str) -> Option<String> {
    match t?.get(key)? {
        Value::String(s) if !s.trim().is_empty() => Some(s.trim().to_string()),
        Value::Integer(n) => Some(n.to_string()),
        _ => None,
    }
}

fn env_or(var: &str, fallback: Option<String>) -> Option<String> {
    match std::env::var(var) {
        Ok(v) => Some(v).filter(|v| !v.is_empty()),
        Err(_) => fallback,
    }
}

fn parse_thread(v: &Value) -> Result<Option<i64>> {
    Ok(match v {
        Value::Integer(0) => None,
        Value::Integer(n) => Some(*n),
        Value::String(s) if s.trim().is_empty() => None,
        Value::String(s) => Some(
            s.trim()
                .parse()
                .context("pyball.siesta.message_thread_id must be a number")?,
        ),
        _ => bail!("pyball.siesta.message_thread_id must be a number"),
    })
}

#[cfg(test)]
mod tests {
    use super::*;

    fn write(dir: &Path, name: &str, body: &str) -> PathBuf {
        let p = dir.join(name);
        std::fs::write(&p, body).unwrap();
        p
    }

    #[test]
    fn reads_everything_from_pyball_config() {
        let dir = std::env::temp_dir().join(format!("siesta-cfg-{}", std::process::id()));
        let data = dir.join("data");
        std::fs::create_dir_all(&data).unwrap();
        let _ = std::fs::remove_file(dir.join(".env"));
        let toml = r#"
[pyball.core]
base_url = "https://futbol.example.com"
manage_token = "m"
data_dir = "DATA"

[pyball.telegram]
bot_token = "123:abc"

[pyball.telegram.regulars.meetups]
chat_id = -1001234
message_thread_id = 55
"#
        .replace("DATA", &data.display().to_string());
        let cfg_path = write(&dir, "config.toml", &toml);
        let cfg = Config::load(&cfg_path).unwrap();
        assert_eq!(cfg.api_url, "https://futbol.example.com");
        assert_eq!(cfg.manage_token, "m");
        assert_eq!(cfg.state_file, data.join("siesta.json"));
        let tg = cfg.telegram.unwrap();
        assert_eq!(tg.chat_id, "-1001234");
        assert_eq!(
            tg.thread_id, None,
            "goes to the general chat, not the callup topic"
        );

        write(&dir, ".env", "UID=1000\nPORT=8123\n");
        let cfg = Config::load(&cfg_path).unwrap();
        assert_eq!(cfg.api_url, "http://127.0.0.1:8123");
    }
}
