//! activity: post PyBall's activity feed (joins, leaves, meetups created, closed or
//! cancelled) from the event stream, run as a PyBall plugin.

mod api;
mod config;
#[cfg(test)]
mod contract;
mod target;
mod telegram;

use std::path::Path;
use std::time::Duration;

use anyhow::Result;
use pyball_client::plugin::{load_event_id, save_event_id};
use pyball_client::{Api, Frame};

use crate::api::{EVENTS, Event};
use crate::config::Config;
use crate::target::{FEED, LogTarget, Target, TelegramTarget};
use crate::telegram::Telegram;

fn main() {
    if let Err(err) = run() {
        eprintln!("error: {err:#}");
        std::process::exit(1);
    }
}

/// Follow the event stream forever, resuming after the last event handled.
///
/// Any error ends the process without remembering the event it failed on; PyBall starts
/// the plugin again, and it posts that event then.
fn run() -> Result<()> {
    let cfg = Config::load(Path::new("config.toml"))?;
    let api = Api::new(&cfg.api_url, &cfg.api_token);
    let target: Box<dyn Target> = match cfg.telegram {
        Some(chat) => {
            println!(
                "Posting the activity feed to Telegram chat {}.",
                chat.chat_id
            );
            Box::new(TelegramTarget {
                chat: Telegram {
                    bot_token: chat.bot_token,
                    chat_id: chat.chat_id,
                    thread_id: chat.thread_id,
                },
                date_format: cfg.date_format,
            })
        }
        None => {
            println!("No Telegram chat configured: the activity feed goes to the log.");
            Box::new(LogTarget {
                date_format: cfg.date_format,
            })
        }
    };
    loop {
        let mut stream = api.events(&EVENTS, load_event_id(&cfg.event_id_file)?)?;
        while let Some(frame) = stream.next_frame()? {
            if let Frame::Event(event) = frame {
                handle(target.as_ref(), &event, &cfg.event_id_file)?;
            }
        }
        println!("PyBall closed the event stream; reconnecting.");
        std::thread::sleep(Duration::from_secs(1));
    }
}

/// Post `event` if it is in the feed, then remember it as handled.
fn handle(target: &dyn Target, event: &Event, event_id_file: &Path) -> Result<()> {
    if FEED.contains(&event.kind.as_str()) {
        target.post(event)?;
    }
    save_event_id(event_id_file, event.id)
}

#[cfg(test)]
mod tests {
    use std::cell::RefCell;

    use anyhow::bail;

    use super::*;
    use crate::api::Meetup;

    /// Records what it posts; fails while `down`.
    #[derive(Default)]
    struct Chat {
        posted: RefCell<Vec<u64>>,
        down: bool,
    }

    impl Target for Chat {
        fn post(&self, event: &Event) -> Result<()> {
            if self.down {
                bail!("Telegram is down");
            }
            self.posted.borrow_mut().push(event.id);
            Ok(())
        }
    }

    fn event(id: u64, kind: &str) -> Event {
        Event {
            id,
            kind: kind.to_string(),
            meetup: Meetup {
                date: "2026-11-25T20:00:00".to_string(),
            },
            player: None,
            is_substitute: None,
        }
    }

    #[test]
    fn remembers_an_event_only_once_posted_and_skips_the_rest_of_the_stream() {
        let dir = std::env::temp_dir().join(format!("activity-{}", std::process::id()));
        let id_file = dir.join("last_event_id");

        let down = Chat {
            down: true,
            ..Chat::default()
        };
        assert!(handle(&down, &event(1, "meetup.created"), &id_file).is_err());
        assert_eq!(
            load_event_id(&id_file).unwrap(),
            None,
            "posted again on restart"
        );

        let chat = Chat::default();
        handle(&chat, &event(1, "meetup.created"), &id_file).unwrap();
        handle(&chat, &event(2, "meetup.updated"), &id_file).unwrap();
        assert_eq!(*chat.posted.borrow(), vec![1]);
        assert_eq!(load_event_id(&id_file).unwrap(), Some(2));
        std::fs::remove_dir_all(dir).unwrap();
    }
}
