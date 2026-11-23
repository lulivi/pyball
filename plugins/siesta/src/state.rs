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

//! The siesta list and what the plugin remembers, in `data/plugins/siesta/state.json`.
//!
//! Player and meetup IDs only: names live in PyBall.

use std::collections::{BTreeMap, HashMap};
use std::fs;
use std::path::Path;

use anyhow::{Context, Result};
use pyball_client::plugin::write_atomic;
use serde::{Deserialize, Serialize};

#[derive(Debug, Clone, Default, Serialize, Deserialize)]
pub struct State {
    /// Regular's player ID -> times left out.
    #[serde(default)]
    pub outs: BTreeMap<String, u32>,
    /// Every draw ever made, oldest first.
    #[serde(default)]
    pub draws: Vec<Draw>,
    /// The latest scheduled draw time already handled (RFC 3339).
    #[serde(default)]
    pub last_slot: Option<String>,
    /// Meetups whose substitute search siesta opened and still has to draw.
    #[serde(default)]
    pub searches: Vec<String>,
}

#[derive(Debug, Clone, Serialize, Deserialize)]
pub struct Draw {
    /// PyBall meetup ID.
    pub meetup: String,
    /// The meetup's date, for people reading the file.
    pub meetup_date: String,
    /// When the draw ran (local time, RFC 3339).
    pub drawn_at: String,
    pub signed_up: Vec<String>,
    /// Players left out (each got +1).
    pub left_out: Vec<String>,
    /// The roster sent to PyBall; sent again if teams are missing after a crash.
    pub playing: Vec<String>,
    /// Left-out players who later got a spot (their +1 was refunded).
    #[serde(default)]
    pub reinstated: Vec<String>,
}

impl State {
    pub fn load(path: &Path) -> Result<Self> {
        if !path.exists() {
            return Ok(Self::default());
        }
        let raw = fs::read_to_string(path)
            .with_context(|| format!("reading siesta list {}", path.display()))?;
        serde_json::from_str(&raw).with_context(|| format!("parsing {}", path.display()))
    }

    /// Write atomically (temp file + rename) so a crash never leaves half a file.
    pub fn save(&self, path: &Path) -> Result<()> {
        write_atomic(path, &(serde_json::to_string_pretty(self)? + "\n"))
    }

    /// Add every current regular who isn't on the list yet, starting at the
    /// lowest count among the regulars already on it (0 for the very first run).
    /// Returns the IDs that were added.
    pub fn sync_regulars(&mut self, regular_ids: &[String]) -> Vec<String> {
        let floor = regular_ids
            .iter()
            .filter_map(|id| self.outs.get(id))
            .min()
            .copied()
            .unwrap_or(0);
        let mut added = Vec::new();
        for id in regular_ids {
            if !self.outs.contains_key(id) {
                self.outs.insert(id.clone(), floor);
                added.push(id.clone());
            }
        }
        added
    }

    pub fn outs_map(&self) -> HashMap<String, u32> {
        self.outs.iter().map(|(id, n)| (id.clone(), *n)).collect()
    }

    pub fn add_out(&mut self, id: &str) {
        *self.outs.entry(id.to_string()).or_default() += 1;
    }

    pub fn refund_out(&mut self, id: &str) {
        if let Some(n) = self.outs.get_mut(id) {
            *n = n.saturating_sub(1);
        }
    }

    pub fn draw_for(&self, meetup: &str) -> Option<&Draw> {
        self.draws.iter().rev().find(|d| d.meetup == meetup)
    }

    pub fn draw_for_mut(&mut self, meetup: &str) -> Option<&mut Draw> {
        self.draws.iter_mut().rev().find(|d| d.meetup == meetup)
    }
}

#[cfg(test)]
mod tests {
    use super::*;

    fn s(v: &[&str]) -> Vec<String> {
        v.iter().map(|x| x.to_string()).collect()
    }

    #[test]
    fn first_sync_starts_everyone_at_zero() {
        let mut st = State::default();
        st.sync_regulars(&s(&["a", "b", "c"]));
        assert!(st.outs.values().all(|n| *n == 0));
    }

    #[test]
    fn newcomers_start_at_the_lowest_count() {
        let mut st = State::default();
        st.outs.insert("a".into(), 2);
        st.outs.insert("b".into(), 3);
        st.outs.insert("gone".into(), 0); // no longer a regular: ignored for the floor
        let added = st.sync_regulars(&s(&["a", "b", "new"]));
        assert_eq!(added, s(&["new"]));
        assert_eq!(st.outs["new"], 2);
        assert_eq!(st.outs["a"], 2, "existing counts are untouched");
    }
}
