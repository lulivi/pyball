//! Settings: the plugin API from the environment, the rest from siesta's own
//! `[pyball.plugins.siesta]` table in PyBall's config.toml.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use chrono::{NaiveTime, Weekday};
use chrono_tz::Tz;
use toml::Value;

/// Where the state lives, relative to the workspace the core runs plugins from.
const STATE_FILE: &str = "data/plugins/siesta/state.json";
const EVENT_ID_FILE: &str = "data/plugins/siesta/last_event_id";
const DEFAULT_API_URL: &str = "http://127.0.0.1:8000/api/v1";

#[derive(Debug)]
pub struct Config {
    /// `PYBALL_API_URL`, ending in `/api/v1`.
    pub api_url: String,
    /// `PYBALL_API_TOKEN`: the plugin's own token, or the manage token by hand.
    pub api_token: String,
    pub team_algorithm: String,
    pub schedule: Schedule,
    pub state_file: PathBuf,
    pub event_id_file: PathBuf,
    pub telegram: Option<TelegramTarget>,
}

/// When the weekly draw runs.
#[derive(Debug, Clone, Copy)]
pub struct Schedule {
    pub weekday: Weekday,
    pub time: NaiveTime,
    pub timezone: Tz,
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
        let table = doc
            .get("pyball")
            .and_then(|p| p.get("plugins"))
            .and_then(|p| p.get("siesta"))
            .and_then(Value::as_table);
        Self::from_table(table, env("PYBALL_API_URL"), env("PYBALL_API_TOKEN"))
    }

    fn from_table(
        t: Option<&toml::Table>,
        api_url: Option<String>,
        api_token: Option<String>,
    ) -> Result<Self> {
        let api_token = api_token.context(
            "PYBALL_API_TOKEN is not set: PyBall sets it for the plugin; \
             by hand, pass the manage token",
        )?;

        let team_algorithm = string(t, "team_algorithm")?.unwrap_or_else(|| "balanceado".into());
        if !matches!(team_algorithm.as_str(), "balanceado" | "random") {
            bail!("plugins.siesta.team_algorithm must be \"balanceado\" or \"random\"");
        }

        let weekday = match string(t, "weekday")? {
            Some(day) => day
                .parse::<Weekday>()
                .ok()
                .context("plugins.siesta.weekday must be a day in English, e.g. \"monday\"")?,
            None => Weekday::Mon,
        };
        let time = match string(t, "time")? {
            Some(hm) => NaiveTime::parse_from_str(&hm, "%H:%M")
                .context("plugins.siesta.time must be HH:MM, e.g. \"10:00\"")?,
            None => NaiveTime::from_hms_opt(10, 0, 0).expect("valid time"),
        };
        let timezone = match string(t, "timezone")? {
            Some(tz) => tz
                .parse::<Tz>()
                .ok()
                .context("plugins.siesta.timezone must be an IANA name, e.g. \"Europe/Madrid\"")?,
            None => chrono_tz::Europe::Madrid,
        };

        let bot_token = string(t, "telegram_bot_token")?;
        let chat_id = string(t, "telegram_chat_id")?.filter(|c| c != "0");
        let thread_id = match string(t, "telegram_message_thread_id")? {
            Some(n) => Some(
                n.parse::<i64>()
                    .context("plugins.siesta.telegram_message_thread_id must be a number")?,
            )
            .filter(|n| *n != 0),
            None => None,
        };
        let telegram = match (bot_token, chat_id) {
            (Some(bot_token), Some(chat_id)) => Some(TelegramTarget {
                bot_token,
                chat_id,
                thread_id,
            }),
            _ => None,
        };

        Ok(Self {
            api_url: api_url
                .unwrap_or_else(|| DEFAULT_API_URL.into())
                .trim_end_matches('/')
                .to_string(),
            api_token,
            team_algorithm,
            schedule: Schedule {
                weekday,
                time,
                timezone,
            },
            state_file: PathBuf::from(STATE_FILE),
            event_id_file: PathBuf::from(EVENT_ID_FILE),
            telegram,
        })
    }
}

/// A config value as a string; numbers are accepted too (chat IDs).
fn string(t: Option<&toml::Table>, key: &str) -> Result<Option<String>> {
    Ok(match t.and_then(|t| t.get(key)) {
        None => None,
        Some(Value::String(s)) if s.trim().is_empty() => None,
        Some(Value::String(s)) => Some(s.trim().to_string()),
        Some(Value::Integer(n)) => Some(n.to_string()),
        Some(_) => bail!("plugins.siesta.{key} must be a text or a number"),
    })
}

fn env(var: &str) -> Option<String> {
    std::env::var(var).ok().filter(|v| !v.is_empty())
}

#[cfg(test)]
mod tests {
    use super::*;

    fn load(toml: &str) -> Result<Config> {
        let doc: toml::Table = toml::from_str(toml).unwrap();
        Config::from_table(Some(&doc), None, Some("t".into()))
    }

    #[test]
    fn defaults_to_monday_ten_in_madrid_without_telegram() {
        let cfg = load("").unwrap();
        assert_eq!(cfg.api_url, DEFAULT_API_URL);
        assert_eq!(cfg.schedule.weekday, Weekday::Mon);
        assert_eq!(cfg.schedule.time.to_string(), "10:00:00");
        assert_eq!(cfg.schedule.timezone, chrono_tz::Europe::Madrid);
        assert_eq!(cfg.team_algorithm, "balanceado");
        assert!(cfg.telegram.is_none());
    }

    #[test]
    fn reads_its_own_table() {
        let cfg = load(
            r#"
weekday = "tuesday"
time = "09:30"
timezone = "America/Lima"
team_algorithm = "random"
telegram_bot_token = "123:abc"
telegram_chat_id = -1001234
telegram_message_thread_id = 0
"#,
        )
        .unwrap();
        assert_eq!(cfg.schedule.weekday, Weekday::Tue);
        assert_eq!(cfg.schedule.time.to_string(), "09:30:00");
        assert_eq!(cfg.schedule.timezone, chrono_tz::America::Lima);
        let tg = cfg.telegram.unwrap();
        assert_eq!(tg.chat_id, "-1001234");
        assert_eq!(tg.thread_id, None, "0 is the group's main chat");
    }

    #[test]
    fn rejects_bad_values_and_a_missing_token() {
        assert!(load("weekday = \"lunes\"").is_err());
        assert!(load("time = \"10h\"").is_err());
        assert!(load("timezone = \"Madrid\"").is_err());
        assert!(load("team_algorithm = \"aleatorio\"").is_err());
        assert!(Config::from_table(None, None, None).is_err());
    }
}
