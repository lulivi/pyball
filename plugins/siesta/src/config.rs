//! Settings: the plugin API from the environment, the rest from siesta's own
//! `[pyball.plugins.siesta]` table in PyBall's config.toml.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use chrono::{NaiveTime, Weekday};
use chrono_tz::Tz;
use pyball_client::plugin;

use crate::telegram::Telegram;

/// The plugin's table and its folder under `data/plugins/`.
const NAME: &str = "siesta";

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
    pub telegram: Option<Telegram>,
}

/// When the weekly draw runs.
#[derive(Debug, Clone, Copy)]
pub struct Schedule {
    pub weekday: Weekday,
    pub time: NaiveTime,
    pub timezone: Tz,
}

impl Config {
    pub fn load(config_path: &Path) -> Result<Self> {
        let table = plugin::table(config_path, NAME)?;
        Self::from_table(
            table.as_ref(),
            plugin::env("PYBALL_API_URL"),
            plugin::env("PYBALL_API_TOKEN"),
        )
    }

    fn from_table(
        t: Option<&toml::Table>,
        api_url: Option<String>,
        api_token: Option<String>,
    ) -> Result<Self> {
        let api_token = plugin::api_token(api_token)?;

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

        Ok(Self {
            api_url: plugin::api_url(api_url),
            api_token,
            team_algorithm,
            schedule: Schedule {
                weekday,
                time,
                timezone,
            },
            state_file: plugin::data_dir(NAME).join("state.json"),
            event_id_file: plugin::data_dir(NAME).join("last_event_id"),
            telegram: Telegram::from_table(t, NAME)?,
        })
    }
}

fn string(t: Option<&toml::Table>, key: &str) -> Result<Option<String>> {
    plugin::string(t, NAME, key)
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
        assert_eq!(cfg.api_url, plugin::DEFAULT_API_URL);
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

[telegram]
bot_token = "123:abc"
chat_id = -1001234
message_thread_id = 0
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
