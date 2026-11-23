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

//! Post a message to a Telegram chat through the Bot API.

use anyhow::{Context, Result, anyhow, bail};
use pyball_client::plugin;
use serde_json::{Value, json};

#[derive(Debug)]
pub struct Telegram {
    pub bot_token: String,
    pub chat_id: String,
    pub thread_id: Option<i64>,
}

impl Telegram {
    /// The chat in the plugin's `[pyball.plugins.<plugin>.telegram]` table; `None` without
    /// one or with `chat_id = 0`.
    pub fn from_table(t: Option<&toml::Table>, plugin: &str) -> Result<Option<Self>> {
        let name = format!("{plugin}.telegram");
        let t = match t.and_then(|t| t.get("telegram")) {
            None => return Ok(None),
            Some(toml::Value::Table(t)) => Some(t),
            Some(_) => bail!("plugins.{name} must be a table"),
        };
        let Some(chat_id) = plugin::string(t, &name, "chat_id")?.filter(|c| c != "0") else {
            return Ok(None);
        };
        let bot_token = plugin::string(t, &name, "bot_token")?
            .with_context(|| format!("plugins.{name}.bot_token is required with a chat_id"))?;
        let thread_id =
            match plugin::string(t, &name, "message_thread_id")? {
                Some(n) => Some(n.parse::<i64>().with_context(|| {
                    format!("plugins.{name}.message_thread_id must be a number")
                })?)
                .filter(|n| *n != 0),
                None => None,
            };
        Ok(Some(Self {
            bot_token,
            chat_id,
            thread_id,
        }))
    }

    pub fn send_html(&self, text: &str) -> Result<()> {
        let mut body = json!({
            "chat_id": self.chat_id,
            "text": text,
            "parse_mode": "HTML",
            "link_preview_options": { "is_disabled": true },
        });
        if let Some(thread) = self.thread_id {
            body["message_thread_id"] = json!(thread);
        }
        let url = format!("https://api.telegram.org/bot{}/sendMessage", self.bot_token);
        let agent: ureq::Agent = ureq::Agent::config_builder()
            .http_status_as_error(false) // read Telegram's "description" on 4xx too
            .timeout_global(Some(std::time::Duration::from_secs(30))) // fail, retry later
            .build()
            .into();
        let mut resp = agent
            .post(&url)
            .send_json(&body)
            // the URL contains the bot token: keep it out of logs
            .map_err(|e| anyhow!(e.to_string().replace(&self.bot_token, "<bot_token>")))
            .context("cannot reach api.telegram.org")?;
        let status = resp.status();
        let reply: Value = resp.body_mut().read_json().unwrap_or(Value::Null);
        if !status.is_success() || reply["ok"] != json!(true) {
            bail!(
                "Telegram sendMessage failed ({status}): {}",
                reply["description"]
            );
        }
        Ok(())
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn chat(toml: &str) -> Result<Option<Telegram>> {
        let doc: toml::Table = toml::from_str(toml).unwrap();
        Telegram::from_table(Some(&doc), "p")
    }

    #[test]
    fn reads_the_telegram_table() {
        let tg = chat("[telegram]\nbot_token = \"1:a\"\nchat_id = -100\nmessage_thread_id = 7")
            .unwrap()
            .unwrap();
        assert_eq!(
            (tg.bot_token.as_str(), tg.chat_id.as_str()),
            ("1:a", "-100")
        );
        assert_eq!(tg.thread_id, Some(7));
        let tg = chat("[telegram]\nbot_token = \"1:a\"\nchat_id = 5\nmessage_thread_id = 0");
        assert_eq!(
            tg.unwrap().unwrap().thread_id,
            None,
            "0 is the group's main chat"
        );
    }

    #[test]
    fn no_table_or_a_zero_chat_means_no_chat() {
        assert!(chat("").unwrap().is_none());
        assert!(
            chat("[telegram]\nbot_token = \"1:a\"\nchat_id = 0")
                .unwrap()
                .is_none()
        );
    }

    #[test]
    fn rejects_a_chat_without_a_bot_and_bad_values() {
        assert!(chat("[telegram]\nchat_id = -100").is_err());
        assert!(
            chat("[telegram]\nbot_token = \"1:a\"\nchat_id = 5\nmessage_thread_id = \"x\"")
                .is_err()
        );
        assert!(chat("telegram = \"-100\"").is_err());
    }
}
