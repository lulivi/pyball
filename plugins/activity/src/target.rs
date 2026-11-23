//! Where the activity feed is posted. Each target writes the event in its own format.

use anyhow::{Result, bail};
use chrono::NaiveDateTime;

use crate::api::Event;
use crate::telegram::Telegram;

/// The event types in the activity feed; the rest of the stream is skipped.
pub const FEED: [&str; 5] = [
    "player.joined",
    "player.left",
    "meetup.created",
    "match.closed",
    "meetup.cancelled",
];

pub trait Target {
    /// Post one event of the [`FEED`]; an error leaves it to be posted again.
    fn post(&self, event: &Event) -> Result<()>;
}

/// A Telegram chat, in MarkdownV2.
pub struct TelegramTarget {
    pub chat: Telegram,
    pub date_format: String,
}

impl Target for TelegramTarget {
    fn post(&self, event: &Event) -> Result<()> {
        self.chat
            .send_markdown(&markdown(event, &self.date_format)?)
    }
}

/// PyBall's log, when no chat is configured.
pub struct LogTarget {
    pub date_format: String,
}

impl Target for LogTarget {
    fn post(&self, event: &Event) -> Result<()> {
        let date = display_date(&event.meetup.date, &self.date_format);
        match (&event.player, event.is_substitute) {
            (Some(player), Some(sub)) => {
                let status = if sub { "suplente" } else { "titular" };
                println!("{} {date}: {} ({status})", event.kind, player.name);
            }
            _ => println!("{} {date}", event.kind),
        }
        Ok(())
    }
}

/// The message the Telegram notifier in the core used to send for `event`.
pub fn markdown(event: &Event, date_format: &str) -> Result<String> {
    let date = code(&display_date(&event.meetup.date, date_format));
    let player = || match (&event.player, event.is_substitute) {
        (Some(player), Some(sub)) => {
            Ok((code(&player.name), if sub { "suplente" } else { "titular" }))
        }
        _ => bail!("event {} ({}) has no player", event.id, event.kind),
    };
    Ok(match event.kind.as_str() {
        "meetup.created" => {
            format!("🆕 *Convocatoria creada* — nueva convocatoria para el `{date}`\\.")
        }
        "meetup.cancelled" => {
            format!("🚫 *Convocatoria cancelada* — se ha cancelado la convocatoria del `{date}`\\.")
        }
        "match.closed" => {
            format!("🏁 *Convocatoria cerrada* — la convocatoria del `{date}` ha finalizado\\.")
        }
        "player.joined" => {
            let (name, status) = player()?;
            format!(
                "✅ *Alta* — `{name}` se apunta como {status} a la convocatoria del `{date}`\\."
            )
        }
        "player.left" => {
            let (name, status) = player()?;
            format!(
                "❌ *Baja* — `{name}` se desapunta como {status} de la convocatoria del `{date}`\\."
            )
        }
        other => bail!("no activity message for {other}"),
    })
}

/// `date` in `format`, or as PyBall sent it if it is not a plain local date and time.
fn display_date(date: &str, format: &str) -> String {
    match date.parse::<NaiveDateTime>() {
        Ok(dt) => dt.format(format).to_string(),
        Err(_) => date.to_string(),
    }
}

/// Escape backslash and backtick so text is safe inside a MarkdownV2 code span.
fn code(text: &str) -> String {
    text.replace('\\', "\\\\").replace('`', "\\`")
}

#[cfg(test)]
mod tests {
    use super::*;
    use crate::api::{Meetup, Player};

    fn event(kind: &str, player: Option<(&str, bool)>) -> Event {
        Event {
            id: 1,
            kind: kind.to_string(),
            meetup: Meetup {
                date: "2026-11-25T20:00:00".to_string(),
            },
            player: player.map(|(name, _)| Player {
                name: name.to_string(),
            }),
            is_substitute: player.map(|(_, sub)| sub),
        }
    }

    fn text(kind: &str, player: Option<(&str, bool)>) -> String {
        markdown(&event(kind, player), "%Y-%m-%d %H:%M").unwrap()
    }

    #[test]
    fn writes_the_meetup_messages() {
        assert_eq!(
            text("meetup.created", None),
            "🆕 *Convocatoria creada* — nueva convocatoria para el `2026-11-25 20:00`\\."
        );
        assert_eq!(
            text("meetup.cancelled", None),
            "🚫 *Convocatoria cancelada* — se ha cancelado la convocatoria del \
             `2026-11-25 20:00`\\."
        );
        assert_eq!(
            text("match.closed", None),
            "🏁 *Convocatoria cerrada* — la convocatoria del `2026-11-25 20:00` ha finalizado\\."
        );
    }

    #[test]
    fn writes_joins_and_leaves_with_the_player_escaped() {
        assert_eq!(
            text("player.joined", Some(("Ana", false))),
            "✅ *Alta* — `Ana` se apunta como titular a la convocatoria del \
             `2026-11-25 20:00`\\."
        );
        assert_eq!(
            text("player.left", Some(("a`b\\c", true))),
            "❌ *Baja* — `a\\`b\\\\c` se desapunta como suplente de la convocatoria del \
             `2026-11-25 20:00`\\."
        );
    }

    #[test]
    fn uses_the_date_format_and_rejects_what_it_cannot_write() {
        let created = event("meetup.created", None);
        assert!(markdown(&created, "%d/%m").unwrap().contains("`25/11`"));
        assert!(markdown(&event("player.joined", None), "%d").is_err());
        assert!(markdown(&event("meetup.updated", None), "%d").is_err());
        assert_eq!(display_date("not a date", "%d"), "not a date");
    }
}
