//! Post a message to a Telegram chat through the Bot API.

use anyhow::{Context, Result, anyhow, bail};
use serde_json::{Value, json};

pub struct Telegram {
    pub bot_token: String,
    pub chat_id: String,
    pub thread_id: Option<i64>,
}

impl Telegram {
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
