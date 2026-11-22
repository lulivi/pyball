//! Settings: the plugin API from the environment, the rest from activity's own
//! `[pyball.plugins.activity]` table in PyBall's config.toml.

use std::path::{Path, PathBuf};

use anyhow::{Context, Result, bail};
use chrono::format::{Item, StrftimeItems};
use pyball_client::plugin;

/// The plugin's table and its folder under `data/plugins/`.
const NAME: &str = "activity";
/// The core's own default `display_date_format`.
const DEFAULT_DATE_FORMAT: &str = "%Y-%m-%d %H:%M";

#[derive(Debug)]
pub struct Config {
    pub api_url: String,
    pub api_token: String,
    pub date_format: String,
    pub event_id_file: PathBuf,
    pub telegram: Option<TelegramChat>,
}

#[derive(Debug)]
pub struct TelegramChat {
    pub bot_token: String,
    pub chat_id: String,
    /// `None` = the group's main ("General") chat.
    pub thread_id: Option<i64>,
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
        let date_format =
            string(t, "date_format")?.unwrap_or_else(|| DEFAULT_DATE_FORMAT.to_string());
        if StrftimeItems::new(&date_format).any(|item| matches!(item, Item::Error)) {
            bail!("plugins.activity.date_format is not a valid date format: {date_format}");
        }

        let bot_token = string(t, "telegram_bot_token")?;
        let chat_id = string(t, "telegram_chat_id")?.filter(|c| c != "0");
        let thread_id = match string(t, "telegram_message_thread_id")? {
            Some(n) => Some(
                n.parse::<i64>()
                    .context("plugins.activity.telegram_message_thread_id must be a number")?,
            )
            .filter(|n| *n != 0),
            None => None,
        };
        let telegram = match (bot_token, chat_id) {
            (Some(bot_token), Some(chat_id)) => Some(TelegramChat {
                bot_token,
                chat_id,
                thread_id,
            }),
            _ => None,
        };

        Ok(Self {
            api_url: plugin::api_url(api_url),
            api_token: plugin::api_token(api_token)?,
            date_format,
            event_id_file: plugin::data_dir(NAME).join("last_event_id"),
            telegram,
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
    fn defaults_to_the_core_date_format_and_the_log() {
        let cfg = load("").unwrap();
        assert_eq!(cfg.date_format, "%Y-%m-%d %H:%M");
        assert_eq!(cfg.api_url, plugin::DEFAULT_API_URL);
        assert_eq!(
            cfg.event_id_file,
            Path::new("data/plugins/activity/last_event_id")
        );
        assert!(cfg.telegram.is_none());
    }

    #[test]
    fn reads_its_own_table() {
        let cfg = load(
            r#"
date_format = "%d/%m %H:%M"
telegram_bot_token = "123:abc"
telegram_chat_id = -1001234
telegram_message_thread_id = 7
"#,
        )
        .unwrap();
        assert_eq!(cfg.date_format, "%d/%m %H:%M");
        let tg = cfg.telegram.unwrap();
        assert_eq!(tg.chat_id, "-1001234");
        assert_eq!(tg.thread_id, Some(7));
    }

    #[test]
    fn a_zero_chat_or_topic_means_none() {
        let cfg = load("telegram_bot_token = \"1:a\"\ntelegram_chat_id = 0").unwrap();
        assert!(cfg.telegram.is_none());
        let cfg = load(
            "telegram_bot_token = \"1:a\"\ntelegram_chat_id = 5\ntelegram_message_thread_id = 0",
        )
        .unwrap();
        assert_eq!(cfg.telegram.unwrap().thread_id, None);
    }

    #[test]
    fn rejects_bad_values_and_a_missing_token() {
        assert!(load("date_format = \"%Q\"").is_err());
        assert!(load("telegram_message_thread_id = \"general\"").is_err());
        assert!(Config::from_table(None, None, None).is_err());
    }
}
