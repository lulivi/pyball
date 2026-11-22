//! siesta: decide every week who sits out so matches stay at 5 vs 5.
//!
//! Run `draw` from cron on Monday at 10:00 in your PyBall workspace. It reads
//! PyBall's config.toml, takes the callup from the API, leaves out the excess
//! players fairly (see `draw.rs`), trims the meetup, builds the teams, updates
//! the siesta list and posts a summary to the group's main chat.

mod config;
mod draw;
mod message;
mod pyball;
mod state;
mod telegram;

use std::path::PathBuf;

use anyhow::{Context, Result, bail};
use clap::{Parser, Subcommand};

use crate::config::Config;
use crate::message::{DrawSummary, SiestaRow};
use crate::pyball::{ActiveMeetup, Player, PyBall};
use crate::state::{Draw, State};
use crate::telegram::Telegram;

#[derive(Parser)]
#[command(version, about = "Fair weekly sit-out draw for PyBall")]
struct Cli {
    /// PyBall's config.toml.
    #[arg(short, long, default_value = "config.toml", global = true)]
    config: PathBuf,
    #[command(subcommand)]
    command: Command,
}

#[derive(Subcommand)]
enum Command {
    /// Run this week's draw on the active meetup (what cron runs on Monday).
    Draw {
        /// Show what would happen without changing PyBall, the list, or Telegram.
        #[arg(long)]
        dry_run: bool,
    },
    /// Give a spot to a player who was left out this week (they get their +1 back).
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

/// Everything the commands need, loaded once.
struct Ctx {
    cfg: Config,
    api: PyBall,
    state: State,
    players: Vec<Player>,
}

impl Ctx {
    fn load(config_path: &std::path::Path) -> Result<Self> {
        let cfg = Config::load(config_path)?;
        let api = PyBall::new(&cfg.api_url, &cfg.manage_token)?;
        let players = api
            .players()
            .with_context(|| format!("PyBall at {} (from {})", cfg.api_url, cfg.api_url_source))?;
        let mut state = State::load(&cfg.state_file)?;
        let added = state.sync_regulars(&regular_ids(&players));
        let ctx = Self {
            cfg,
            api,
            state,
            players,
        };
        if !added.is_empty() {
            println!(
                "New regulars on the siesta list: {}",
                ctx.names(&added).join(", ")
            );
        }
        Ok(ctx)
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

    fn announce(&self, html: &str) -> Result<()> {
        match &self.cfg.telegram {
            Some(tg) => {
                Telegram {
                    bot_token: tg.bot_token.clone(),
                    chat_id: tg.chat_id.clone(),
                    thread_id: tg.thread_id,
                }
                .send_html(html)
                .context("PyBall and the list are updated, but posting to Telegram failed")?;
                println!("Posted to Telegram.");
            }
            None => println!(
                "\n(no [pyball.telegram] chat configured; message not sent)\n\n{}",
                message::to_plain(html)
            ),
        }
        Ok(())
    }
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
        Command::Draw { dry_run } => cmd_draw(&mut ctx, dry_run),
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

fn cmd_draw(ctx: &mut Ctx, dry_run: bool) -> Result<()> {
    let Some(meetup) = ctx.api.active_meetup()? else {
        println!("No active meetup in PyBall; nothing to do.");
        return Ok(());
    };
    if meetup
        .teams
        .as_ref()
        .is_some_and(|t| t.has_recorded_results)
    {
        bail!(
            "meetup {} already has a recorded result; not touching it",
            meetup.date
        );
    }
    if let Some(prev) = ctx.state.draw_for(&meetup.date) {
        println!(
            "Already drew for {} at {} (left out: {}). Nothing to do.",
            meetup.date,
            prev.drawn_at,
            list_or_nobody(&ctx.names(&prev.left_out))
        );
        return Ok(());
    }

    let signed_up: Vec<String> = meetup.players.iter().map(|p| p.id.clone()).collect();
    if signed_up.len() < ctx.cfg.max_players {
        // Not recorded as a draw and no teams (they'd close signup): substitutes still need
        // to join. Run `draw` again once it's full.
        let msg = message::not_full_message(&meetup, ctx.cfg.max_players);
        if dry_run {
            println!("[dry run] nothing changed. This is the message that would be sent:\n");
            println!("{}", message::to_plain(&msg));
            return Ok(());
        }
        return ctx.announce(&msg);
    }
    let left_out = draw::pick_left_out(
        &signed_up,
        &ctx.state.outs_map(),
        ctx.cfg.max_players,
        &mut rand::rng(),
    );
    let playing: Vec<String> = signed_up
        .iter()
        .filter(|id| !left_out.contains(id))
        .cloned()
        .collect();

    let mut next = ctx.state.clone();
    for id in &left_out {
        next.add_out(id);
    }

    if dry_run {
        let mut preview = meetup.clone();
        preview.players.retain(|p| playing.contains(&p.id));
        if !left_out.is_empty() {
            preview.teams = None;
        }
        println!("[dry run] nothing changed. This is the message that would be sent:\n");
        println!(
            "{}",
            message::to_plain(&message::draw_message(&DrawSummary {
                meetup: &preview,
                signed_up: signed_up.len(),
                left_out: ctx.names(&left_out),
                siesta: ctx.siesta_rows(&next),
            }))
        );
        return Ok(());
    }

    // 1. Trim the meetup in PyBall. This also clears any teams.
    if !left_out.is_empty() {
        ctx.api
            .set_roster(&meetup.date, &playing)
            .context("trimming the meetup roster")?;
    }
    // 2. Record the draw right away, so a later failure can never double-count it.
    next.draws.push(Draw {
        meetup: meetup.date.clone(),
        drawn_at: chrono::Local::now().to_rfc3339(),
        signed_up: signed_up.clone(),
        left_out: left_out.clone(),
        reinstated: Vec::new(),
    });
    ctx.state = next;
    ctx.save()?;
    println!("Left out: {}", list_or_nobody(&ctx.names(&left_out)));

    // 3. Teams (keep ones made by hand if nobody had to be left out).
    if !left_out.is_empty() || meetup.teams.is_none() {
        ctx.api.generate_teams(&meetup.date, &ctx.cfg.team_algorithm).context(
            "roster is trimmed and the list saved, but building teams failed; make them in /manage",
        )?;
    }

    // 4. Tell the group.
    let fresh = ctx.api.active_meetup()?.unwrap_or(meetup);
    ctx.announce(&message::draw_message(&DrawSummary {
        meetup: &fresh,
        signed_up: signed_up.len(),
        left_out: ctx.names(&left_out),
        siesta: ctx.siesta_rows(&ctx.state),
    }))
}

fn cmd_reinstate(
    ctx: &mut Ctx,
    player: &str,
    instead_of: Option<&str>,
    dry_run: bool,
) -> Result<()> {
    let meetup: ActiveMeetup = ctx
        .api
        .active_meetup()?
        .context("no active meetup in PyBall")?;
    let draw = ctx
        .state
        .draw_for(&meetup.date)
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
        .map(|p| (p.id.clone(), p.name.clone()))
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
    if new_roster.len() > ctx.cfg.max_players {
        bail!(
            "that would make {} players; say who dropped out with --instead-of <name>",
            new_roster.len()
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

    ctx.api.set_roster(&meetup.date, &new_roster)?;
    ctx.state.refund_out(&in_id);
    if let Some(d) = ctx.state.draw_for_mut(&meetup.date) {
        d.reinstated.push(in_id.clone());
    }
    ctx.save()?;
    ctx.api
        .generate_teams(&meetup.date, &ctx.cfg.team_algorithm)
        .context("roster and list updated, but building teams failed; make them in /manage")?;

    let fresh = ctx.api.active_meetup()?.unwrap_or(meetup);
    let out_name = out.map(|(_, n)| n);
    ctx.announce(&message::reinstate_message(
        &fresh,
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
            last.meetup,
            list_or_nobody(&ctx.names(&last.left_out))
        );
    }
}

fn regular_ids(players: &[Player]) -> Vec<String> {
    players
        .iter()
        .filter(|p| p.is_regular())
        .map(|p| p.id.clone())
        .collect()
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
