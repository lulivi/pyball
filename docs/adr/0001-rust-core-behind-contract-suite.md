# The core is rewritten in Rust behind a contract suite

🇬🇧 English | 🇪🇸 [Español](0001-rust-core-behind-contract-suite.es.md)

The core moves from Python to Rust one slice at a time (players, meetups, matches, stats,
plugin hosting), and each slice merges to `main` on its own. The Python core keeps serving
the clubs until the Rust core passes the same black-box suite, `contract/`, which tests a
core only over `/api/v1` and its `data/` files. The suite is written in Rust and uses raw
JSON rather than `clients/pyball-client-rs`, so it shares no code with any core or plugin.
It enables one Cargo feature per area, so a partial core is held to the areas it has.

Once the rewrite is done, the suite stays: it is the core's contract with plugins, the
web UI and the `data/` files, whichever core implements it.

## Considered options

- **Port the Python unit and integration tests.** They test the internals of the Python
  layers, so they could not check a Rust core, and porting them alongside the code checks
  the new code against itself.
- **Rewrite the core in one go.** That would mean a long-lived branch with nothing
  checking it against the running core until the cutover.
