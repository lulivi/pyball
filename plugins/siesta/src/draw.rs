//! The fair "siesta" draw: who sits out this week.
//!
//! When more than `max_players` signed up, the excess is chosen by the siesta
//! rule: fewest outs first, random among equals. A player with more outs is
//! therefore shielded until everyone else in the callup has caught up with them.

use std::collections::HashMap;

use rand::seq::SliceRandom;

/// The players who sit out (each gets +1 in the siesta list).
pub fn pick_left_out<R>(
    signed_up: &[String],
    outs: &HashMap<String, u32>,
    max_players: usize,
    rng: &mut R,
) -> Vec<String>
where
    R: rand::Rng + ?Sized,
{
    let Some(excess) = signed_up.len().checked_sub(max_players) else {
        return Vec::new();
    };
    let mut ids = signed_up.to_vec();
    ids.shuffle(rng); // random order inside each tier...
    ids.sort_by_key(|id| outs.get(id).copied().unwrap_or(0)); // ...kept by the stable sort
    ids.truncate(excess);
    ids
}

#[cfg(test)]
mod tests {
    use super::*;
    use rand::SeedableRng;
    use rand::rngs::StdRng;

    fn ids(prefix: &str, n: usize) -> Vec<String> {
        (0..n).map(|i| format!("{prefix}{i}")).collect()
    }

    fn draw(signed_up: &[String], outs: &HashMap<String, u32>, seed: u64) -> Vec<String> {
        pick_left_out(signed_up, outs, 10, &mut StdRng::seed_from_u64(seed))
    }

    #[test]
    fn nobody_out_when_ten_or_fewer() {
        assert!(draw(&ids("r", 10), &HashMap::new(), 1).is_empty());
        assert!(draw(&ids("r", 7), &HashMap::new(), 1).is_empty());
    }

    #[test]
    fn leaves_out_exactly_the_excess() {
        assert_eq!(draw(&ids("r", 12), &HashMap::new(), 3).len(), 2);
    }

    #[test]
    fn shielded_players_are_never_picked_before_others_catch_up() {
        let regs = ids("r", 13);
        let outs: HashMap<String, u32> = regs.iter().take(10).map(|id| (id.clone(), 1)).collect();
        for seed in 0..200 {
            let mut out = draw(&regs, &outs, seed);
            out.sort();
            assert_eq!(out, vec!["r10", "r11", "r12"]);
        }
    }

    #[test]
    fn spills_into_next_tier_at_random() {
        // r0, r1 at 0; r12 at 2; rest at 1. Third out comes from the 1s, never r12.
        let regs = ids("r", 13);
        let outs: HashMap<String, u32> = regs
            .iter()
            .enumerate()
            .map(|(i, id)| {
                (
                    id.clone(),
                    match i {
                        0 | 1 => 0,
                        12 => 2,
                        _ => 1,
                    },
                )
            })
            .collect();
        let mut seen = std::collections::HashSet::new();
        for seed in 0..500 {
            let out = draw(&regs, &outs, seed);
            assert!(out.contains(&"r0".into()) && out.contains(&"r1".into()));
            assert!(!out.contains(&"r12".into()));
            seen.extend(out.into_iter().filter(|id| id != "r0" && id != "r1"));
        }
        assert_eq!(
            seen.len(),
            10,
            "every player in the 1-tier gets picked sometimes"
        );
    }

    #[test]
    fn over_many_weeks_outs_stay_level() {
        let regs = ids("r", 13);
        let mut outs: HashMap<String, u32> = HashMap::new();
        let mut rng = StdRng::seed_from_u64(42);
        for _ in 0..13 {
            for id in pick_left_out(&regs, &outs, 10, &mut rng) {
                *outs.entry(id).or_default() += 1;
            }
        }
        assert!(regs.iter().all(|id| outs.get(id) == Some(&3)));
    }
}
