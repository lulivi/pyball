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

//! Settings: the plugin API from the environment, the rest from activity's own
//! `[pyball.plugins.activity]` table in PyBall's config.toml.

use std::path::{Path, PathBuf};

use anyhow::{Result, bail};
use chrono::format::{Item, StrftimeItems};
use pyball_client::plugin;

use crate::telegram::Telegram;

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
    pub telegram: Option<Telegram>,
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

        Ok(Self {
            api_url: plugin::api_url(api_url),
            api_token: plugin::api_token(api_token)?,
            date_format,
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

[telegram]
bot_token = "123:abc"
chat_id = -1001234
"#,
        )
        .unwrap();
        assert_eq!(cfg.date_format, "%d/%m %H:%M");
        assert_eq!(cfg.telegram.unwrap().chat_id, "-1001234");
    }

    #[test]
    fn rejects_bad_values_and_a_missing_token() {
        assert!(load("date_format = \"%Q\"").is_err());
        assert!(load("[telegram]\nchat_id = -100").is_err());
        assert!(Config::from_table(None, None, None).is_err());
    }
}
