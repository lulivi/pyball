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

//! siesta: decide fairly who sits out when more players sign up than a meetup takes.
//!
//! PyBall runs `siesta run` as a plugin. At the scheduled time (Monday 10:00 by
//! default) it draws on the active meetup: above its capacity, the excess sits out
//! by the siesta rule (see `draw.rs`) and the rest get teams; at capacity, everyone
//! plays; below it, it opens the substitute search and builds the teams when the
//! search closes with the roster full. It posts each draw to Telegram.

mod api;
mod config;
#[cfg(test)]
mod contract;
mod draw;
mod message;
mod schedule;
mod state;
mod telegram;

use std::path::PathBuf;
use std::time::Duration;

use anyhow::{Context, Result, bail};
use clap::{Parser, Subcommand};

use pyball_client::Frame;
use pyball_client::plugin::{load_event_id, save_event_id};

use crate::api::{Api, Event, Meetup, Player};
use crate::config::Config;
use crate::message::{DrawSummary, MeetupView, SiestaRow};
use crate::state::{Draw, State};

#[derive(Parser)]
#[command(
    version,
    about = "Fair sit-out draw for PyBall, run as a PyBall plugin"
)]
struct Cli {
    /// PyBall's config.toml, for the [pyball.plugins.siesta] table.
    #[arg(short, long, default_value = "config.toml", global = true)]
    config: PathBuf,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Run as a PyBall plugin: draw at the scheduled time and follow the event stream.
    Run,
    /// Draw on the active meetup now.
    Draw {
        /// Show what would happen without changing PyBall, the list, or Telegram.
        #[arg(long)]
        dry_run: bool,
    },
    /// Give a spot to a player who was left out (they get their +1 back).
    Reinstate {
        /// Name (or start of the name) of the left-out player who now plays.
        player: String,
        /// Player who dropped out; removed from the meetup. Omit if they already left.
        #[arg(long)]
        instead_of: Option<String>,
        #[arg(long)]
        dry_run: bool,
    },
    /// Set a regular's count by hand, e.g. `set ivan 1`.
    Set { player: String, outs: u32 },
    /// Print the siesta list.
    Status,
}

fn main() {
    let cli = Cli::parse();
    if let Err(err) = run(cli) {
        eprintln!("error: {err:#}");
        std::process::exit(1);
    }
}

fn run(cli: Cli) -> Result<()> {
    let mut ctx = Ctx::load(&cli.config)?;
    match cli.command {
        Command::Run => cmd_run(&mut ctx),
        Command::Draw { dry_run } => match ctx.api.active_meetup()? {
            Some(meetup) => draw(&mut ctx, meetup, dry_run),
            None => {
                println!("No active meetup in PyBall; nothing to do.");
                Ok(())
            }
        },
        Command::Reinstate {
            player,
            instead_of,
            dry_run,
        } => cmd_reinstate(&mut ctx, &player, instead_of.as_deref(), dry_run),
        Command::Set { player, outs } => cmd_set(&mut ctx, &player, outs),
        Command::Status => {
            ctx.save()?; // keeps newly added regulars
            cmd_status(&ctx);
            Ok(())
        }
    }
}

/// Everything the commands need.
struct Ctx {
    cfg: Config,
    api: Api,
    state: State,
    players: Vec<Player>,
}

impl Ctx {
    fn load(config_path: &std::path::Path) -> Result<Self> {
        let cfg = Config::load(config_path)?;
        let api = Api::new(&cfg.api_url, &cfg.api_token);
        let mut ctx = Self {
            state: State::load(&cfg.state_file)?,
            cfg,
            api,
            players: Vec::new(),
        };
        ctx.refresh()?;
        Ok(ctx)
    }

    /// Re-read the list (a command may have changed it) and the players from PyBall.
    fn refresh(&mut self) -> Result<()> {
        self.state = State::load(&self.cfg.state_file)?;
        self.players = self
            .api
            .players()
            .with_context(|| format!("PyBall at {}", self.cfg.api_url))?;
        let regulars: Vec<String> = self
            .players
            .iter()
            .filter(|p| p.is_regular())
            .map(|p| p.id.clone())
            .collect();
        let added = self.state.sync_regulars(&regulars);
        if !added.is_empty() {
            println!(
                "New regulars on the siesta list: {}",
                self.names(&added).join(", ")
            );
        }
        Ok(())
    }

    fn save(&self) -> Result<()> {
        self.state.save(&self.cfg.state_file)
    }

    fn name(&self, id: &str) -> String {
        self.players
            .iter()
            .find(|p| p.id == id)
            .map_or_else(|| id.to_string(), |p| p.name.clone())
    }

    fn names(&self, ids: &[String]) -> Vec<String> {
        ids.iter().map(|id| self.name(id)).collect()
    }

    fn view(&self, meetup: &Meetup) -> MeetupView {
        MeetupView {
            date: meetup.date.clone(),
            location: meetup.location.clone(),
            players: self.names(&meetup.players),
            teams: meetup.teams.as_ref().map(|teams| {
                teams
                    .iter()
                    .map(|t| (t.name.clone(), self.names(&t.players)))
                    .collect()
            }),
        }
    }

    /// The siesta list for current regulars, with names.
    fn siesta_rows(&self, state: &State) -> Vec<SiestaRow> {
        self.players
            .iter()
            .filter(|p| p.is_regular())
            .map(|p| SiestaRow {
                name: p.name.clone(),
                outs: state.outs.get(&p.id).copied().unwrap_or(0),
            })
            .collect()
    }

    fn announce_draw(&self, meetup: &Meetup, draw: &Draw) -> Result<()> {
        self.announce(&message::draw_message(&DrawSummary {
            meetup: &self.view(meetup),
            signed_up: draw.signed_up.len(),
            left_out: self.names(&draw.left_out),
            siesta: self.siesta_rows(&self.state),
        }))
    }

    /// Post to Telegram. A failure is only reported: PyBall and the list are already
    /// updated, and failing would restart the plugin into the same failure.
    fn announce(&self, html: &str) -> Result<()> {
        match &self.cfg.telegram {
            Some(tg) => match tg.send_html(html) {
                Ok(()) => println!("Posted to Telegram."),
                Err(err) => eprintln!(
                    "error: PyBall and the list are updated, but posting to Telegram \
                         failed: {err:#}\n{}",
                    message::to_plain(html)
                ),
            },
            None => println!(
                "(no Telegram chat configured; message not sent)\n{}",
                message::to_plain(html)
            ),
        }
        Ok(())
    }
}

/// The plugin: draw at each scheduled time and follow the event stream, forever.
///
/// The stream sends a keepalive every 15 s, so the schedule is checked at least that
/// often. Any error ends the process; PyBall starts it again, and the missed draw
/// runs then.
fn cmd_run(ctx: &mut Ctx) -> Result<()> {
    println!(
        "Draws every {} at {} ({}).",
        ctx.cfg.schedule.weekday,
        ctx.cfg.schedule.time.format("%H:%M"),
        ctx.cfg.schedule.timezone
    );
    loop {
        check_schedule(ctx)?;
        let mut stream = ctx.api.events(load_event_id(&ctx.cfg.event_id_file)?)?;
        while let Some(frame) = stream.next_frame()? {
            check_schedule(ctx)?;
            if let Frame::Event(event) = frame {
                on_event(ctx, *event)?;
            }
        }
        println!("PyBall closed the event stream; reconnecting.");
        std::thread::sleep(Duration::from_secs(1));
    }
}

/// Draw once for the latest scheduled time, unless it was already handled.
///
/// The very first run only remembers the latest time, so installing siesta never
/// draws on the spot; `siesta draw` does that by hand.
fn check_schedule(ctx: &mut Ctx) -> Result<()> {
    let schedule = ctx.cfg.schedule;
    let now = chrono::Utc::now().with_timezone(&schedule.timezone);
    let slot = schedule::latest_slot(&schedule, now).to_rfc3339();
    let last_slot = State::load(&ctx.cfg.state_file)?.last_slot;
    if last_slot.as_deref() == Some(slot.as_str()) {
        return Ok(());
    }
    ctx.refresh()?;
    match last_slot {
        Some(_) => {
            println!("Scheduled draw ({slot}).");
            match ctx.api.active_meetup()? {
                Some(meetup) => draw(ctx, meetup, false)?,
                None => println!("No active meetup in PyBall; nothing to draw."),
            }
        }
        None => println!("First run: the first draw is at the next scheduled time."),
    }
    ctx.state.last_slot = Some(slot);
    ctx.save()
}

/// Remember the event, and build the teams when a search siesta opened closes full.
fn on_event(ctx: &mut Ctx, event: Event) -> Result<()> {
    let m = &event.meetup;
    let fills_search = event.kind == "substitute_search.closed"
        && !m.closed
        && m.teams.is_none()
        && m.players.len() >= m.capacity;
    if fills_search && State::load(&ctx.cfg.state_file)?.searches.contains(&m.id) {
        println!("The substitute search filled the meetup; drawing.");
        ctx.refresh()?;
        if let Some(active) = ctx.api.active_meetup()?.filter(|a| a.id == m.id) {
            draw(ctx, active, false)?;
        }
    }
    save_event_id(&ctx.cfg.event_id_file, event.id)
}

/// Draw on `meetup`: at most once per meetup, so running it again changes nothing.
fn draw(ctx: &mut Ctx, meetup: Meetup, dry_run: bool) -> Result<()> {
    if meetup.closed || meetup.has_recorded_results() {
        println!(
            "Meetup {} already has a recorded result; not touching it.",
            meetup.date
        );
        return Ok(());
    }
    if let Some(prev) = ctx.state.draw_for(&meetup.id).cloned() {
        if meetup.teams.is_none() && !dry_run {
            // Stopped between recording the draw and building the teams: finish it.
            println!(
                "Finishing the draw for {}: building its teams.",
                meetup.date
            );
            let fresh = ctx
                .api
                .set_lineup(&meetup.id, &prev.playing, &ctx.cfg.team_algorithm)?;
            return ctx.announce_draw(&fresh, &prev);
        }
        println!(
            "Already drew for {} at {} (left out: {}). Nothing to do.",
            meetup.date,
            prev.drawn_at,
            list_or_nobody(&ctx.names(&prev.left_out))
        );
        return Ok(());
    }

    let signed_up = meetup.players.clone();
    if signed_up.len() < meetup.capacity && meetup.teams.is_none() {
        // Teams would close signup: the search fills it first, then on_event draws.
        let msg = message::not_full_message(&ctx.view(&meetup), meetup.capacity);
        if dry_run {
            println!("[dry run] nothing changed. Would open the substitute search and send:\n");
            println!("{}", message::to_plain(&msg));
            return Ok(());
        }
        if !meetup.substitute_search {
            ctx.api.open_substitute_search(&meetup.id)?;
        }
        if !ctx.state.searches.contains(&meetup.id) {
            ctx.state.searches.push(meetup.id.clone());
        }
        ctx.save()?;
        return ctx.announce(&msg);
    }

    let left_out = draw::pick_left_out(
        &signed_up,
        &ctx.state.outs_map(),
        meetup.capacity,
        &mut rand::rng(),
    );
    let playing: Vec<String> = signed_up
        .iter()
        .filter(|id| !left_out.contains(id))
        .cloned()
        .collect();
    let record = Draw {
        meetup: meetup.id.clone(),
        meetup_date: meetup.date.clone(),
        drawn_at: chrono::Local::now().to_rfc3339(),
        signed_up,
        left_out,
        playing,
        reinstated: Vec::new(),
    };
    let mut next = ctx.state.clone();
    for id in &record.left_out {
        next.add_out(id);
    }

    if dry_run {
        let mut preview = meetup.clone();
        preview.players.clone_from(&record.playing);
        if !record.left_out.is_empty() {
            preview.teams = None;
        }
        println!("[dry run] nothing changed. This is the message that would be sent:\n");
        println!(
            "{}",
            message::to_plain(&message::draw_message(&DrawSummary {
                meetup: &ctx.view(&preview),
                signed_up: record.signed_up.len(),
                left_out: ctx.names(&record.left_out),
                siesta: ctx.siesta_rows(&next),
            }))
        );
        return Ok(());
    }

    // 1. Record the draw first, so a crash can never count it twice or lose it.
    next.searches.retain(|id| id != &meetup.id);
    next.draws.push(record.clone());
    ctx.state = next;
    ctx.save()?;
    println!("Left out: {}", list_or_nobody(&ctx.names(&record.left_out)));

    // 2. One lineup call: the roster and the teams (keep teams made by hand if nobody sat out).
    let fresh = if !record.left_out.is_empty() || meetup.teams.is_none() {
        ctx.api
            .set_lineup(&meetup.id, &record.playing, &ctx.cfg.team_algorithm)
            .context("the draw is saved, but building teams failed; it is retried on restart")?
    } else {
        meetup
    };

    // 3. Tell the group.
    ctx.announce_draw(&fresh, &record)
}

fn cmd_reinstate(
    ctx: &mut Ctx,
    player: &str,
    instead_of: Option<&str>,
    dry_run: bool,
) -> Result<()> {
    let meetup = ctx
        .api
        .active_meetup()?
        .context("no active meetup in PyBall")?;
    let draw = ctx
        .state
        .draw_for(&meetup.id)
        .with_context(|| format!("there was no draw for {}", meetup.date))?;

    let waiting: Vec<(String, String)> = draw
        .left_out
        .iter()
        .filter(|id| !draw.reinstated.contains(id))
        .map(|id| (id.clone(), ctx.name(id)))
        .collect();
    let (in_id, in_name) = find_player(&waiting, player)
        .context("that player isn't among this week's left-out players")?;

    let roster: Vec<(String, String)> = meetup
        .players
        .iter()
        .map(|id| (id.clone(), ctx.name(id)))
        .collect();
    let out = match instead_of {
        Some(q) => Some(find_player(&roster, q).context("that player isn't in this meetup")?),
        None => None,
    };

    let mut new_roster: Vec<String> = roster
        .iter()
        .map(|(id, _)| id.clone())
        .filter(|id| out.as_ref().is_none_or(|(out_id, _)| out_id != id))
        .collect();
    new_roster.push(in_id.clone());
    if new_roster.len() > meetup.capacity {
        bail!(
            "that would make {} players for {}; say who dropped out with --instead-of <name>",
            new_roster.len(),
            meetup.capacity
        );
    }

    if dry_run {
        println!(
            "[dry run] would add {in_name}{} and refund their +1.",
            out.as_ref()
                .map(|(_, n)| format!(" instead of {n}"))
                .unwrap_or_default(),
        );
        return Ok(());
    }

    let fresh = ctx
        .api
        .set_lineup(&meetup.id, &new_roster, &ctx.cfg.team_algorithm)?;
    ctx.state.refund_out(&in_id);
    if let Some(d) = ctx.state.draw_for_mut(&meetup.id) {
        d.reinstated.push(in_id.clone());
        d.playing.clone_from(&new_roster);
    }
    ctx.save()?;

    let out_name = out.map(|(_, n)| n);
    ctx.announce(&message::reinstate_message(
        &ctx.view(&fresh),
        &in_name,
        out_name.as_deref(),
        &ctx.siesta_rows(&ctx.state),
    ))
}

fn cmd_set(ctx: &mut Ctx, player: &str, outs: u32) -> Result<()> {
    let regulars: Vec<(String, String)> = ctx
        .players
        .iter()
        .filter(|p| p.is_regular())
        .map(|p| (p.id.clone(), p.name.clone()))
        .collect();
    let (id, name) = find_player(&regulars, player).context("no regular matches that name")?;
    let before = ctx.state.outs.insert(id, outs).unwrap_or(0);
    ctx.save()?;
    println!("{name}: {before} -> {outs}");
    Ok(())
}

fn cmd_status(ctx: &Ctx) {
    let mut rows = ctx.siesta_rows(&ctx.state);
    rows.sort_by(|a, b| {
        b.outs
            .cmp(&a.outs)
            .then_with(|| message::fold(&a.name).cmp(&message::fold(&b.name)))
    });
    println!("Siesta list ({}):\n", ctx.cfg.state_file.display());
    println!("{:>4}  regular", "outs");
    for r in rows {
        println!("{:>4}  {}", r.outs, r.name);
    }
    if let Some(last) = ctx.state.draws.last() {
        println!(
            "\nLast draw: {} (left out: {})",
            last.meetup_date,
            list_or_nobody(&ctx.names(&last.left_out))
        );
    }
}

fn list_or_nobody(names: &[String]) -> String {
    if names.is_empty() {
        "nobody".into()
    } else {
        names.join(", ")
    }
}

/// Match a player by name: exact (ignoring case/accents) first, then a unique prefix.
fn find_player(players: &[(String, String)], query: &str) -> Option<(String, String)> {
    let q = message::fold(query);
    if let Some(p) = players.iter().find(|(_, n)| message::fold(n) == q) {
        return Some(p.clone());
    }
    let mut hits = players
        .iter()
        .filter(|(_, n)| message::fold(n).starts_with(&q));
    match (hits.next(), hits.next()) {
        (Some(p), None) => Some(p.clone()),
        _ => None,
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn roster() -> Vec<(String, String)> {
        [("1", "José Luis"), ("2", "Jose María"), ("3", "Íñigo")]
            .iter()
            .map(|(i, n)| (i.to_string(), n.to_string()))
            .collect()
    }

    #[test]
    fn finds_players_ignoring_case_and_accents() {
        assert_eq!(find_player(&roster(), "iñigo").unwrap().0, "3");
        assert_eq!(find_player(&roster(), "jose luis").unwrap().0, "1");
        assert_eq!(find_player(&roster(), "jose m").unwrap().0, "2");
        assert!(
            find_player(&roster(), "jose").is_none(),
            "ambiguous prefix must not match"
        );
    }
}
