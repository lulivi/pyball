//! What every PyBall plugin written in Rust shares: the plugin API client and its event
//! stream, the check of a plugin's calls against `plugins/openapi.json`, and how PyBall
//! runs a plugin (its environment, its `config.toml` table and its `data/` folder).

pub mod api;
pub mod contract;
pub mod plugin;

pub use api::{Api, Endpoint, EventStream, Frame};
pub use serde_json;
