# CHANGELOG

<!-- version list -->

## v10.0.1 (2026-11-28)

### Bug Fixes

- **api**: Document the error replies of /api/v1 ([#47](https://github.com/lulivi/pyball/pull/47),
  [`c173e8b`](https://github.com/lulivi/pyball/commit/c173e8b7eb03f45a2ff048a9c835acd1636a44e9))

- **api**: Subscribe /events before its 200 and document error replies
  ([#47](https://github.com/lulivi/pyball/pull/47),
  [`c173e8b`](https://github.com/lulivi/pyball/commit/c173e8b7eb03f45a2ff048a9c835acd1636a44e9))

- **api**: Subscribe the event stream before sending its 200
  ([#47](https://github.com/lulivi/pyball/pull/47),
  [`c173e8b`](https://github.com/lulivi/pyball/commit/c173e8b7eb03f45a2ff048a9c835acd1636a44e9))

### Continuous Integration

- Run the contract suite against the Python core ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

### Documentation

- Document the contract suite and the Rust core ADR
  ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

### Testing

- **contract**: Add the black-box contract suite for the core
  ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Add the black-box contract suite harness and players area
  ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Cover a lineup's event and a search on a meetup with teams
  ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Cover the events area ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Cover the matches and stats areas ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Cover the meetups area ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Drop the fixed wait from the no-backlog stream test
  ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))

- **contract**: Run the suite in the slim CI image ([#46](https://github.com/lulivi/pyball/pull/46),
  [`66150fe`](https://github.com/lulivi/pyball/commit/66150fe8ba0cbfdd4307593e60543054aeca80eb))


## v10.0.0 (2026-11-28)

### Documentation

- Remove web signup from the documentation ([#43](https://github.com/lulivi/pyball/pull/43),
  [`bc8060a`](https://github.com/lulivi/pyball/commit/bc8060a2a9f697851baf65837e910ce100da5e68))

### Features

- Remove web signup ([#43](https://github.com/lulivi/pyball/pull/43),
  [`bc8060a`](https://github.com/lulivi/pyball/commit/bc8060a2a9f697851baf65837e910ce100da5e68))


## v9.0.1 (2026-11-23)

### Bug Fixes

- **images**: Import pymupdf instead of the deprecated fitz
  ([#31](https://github.com/lulivi/pyball/pull/31),
  [`1148fa3`](https://github.com/lulivi/pyball/commit/1148fa38553e4e09d3719703e53570d2d4c8bf5a))


## v9.0.0 (2026-11-23)

### Chores

- Add the license header to every source file ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

### Features

- Run Telegram only as the telegram plugin ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

- Run the Telegram bot as a bundled plugin on the plugin API
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

- **clients**: Add the Python plugin client pyball-client-py
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

- **plugins**: Add the bundled telegram plugin ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

- **plugins**: Serve team colors, meetup lookup by date, summary, stats and settings
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

### Refactoring

- Move the Rust plugin client to clients/pyball-client-rs
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

- **deploy**: Name the one PyBall image in compose.app.yaml
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))

### Testing

- Find source files without git in the license header check
  ([#29](https://github.com/lulivi/pyball/pull/29),
  [`3d70ff5`](https://github.com/lulivi/pyball/commit/3d70ff52e45b75b743cc4e9181ca739a42acb2cf))


## v8.0.0 (2026-11-23)

### Documentation

- **activity**: Say date_format writes names in English, and list crates/ in AGENTS.md
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

### Features

- Post the activity feed from a bundled plugin and share the Rust plugin client
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

- **activity**: Post the activity feed from a bundled plugin
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

- **activity**: Read the Telegram chat from a [pyball.plugins.activity.telegram] table
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

- **siesta**: Read the Telegram chat from a [pyball.plugins.siesta.telegram] table
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

- **telegram**: Remove the activity feed from the Telegram notifier
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))

### Refactoring

- **siesta**: Move the plugin API client to a shared pyball-client crate
  ([#28](https://github.com/lulivi/pyball/pull/28),
  [`5b880e8`](https://github.com/lulivi/pyball/commit/5b880e8daf0d713ad70733adb7259021a80c2163))


## v7.3.0 (2026-11-22)

### Documentation

- Point plugins at the committed schema and the contract checks
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

### Features

- **plugins**: Commit the plugin API schema and check siesta against it
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

- **plugins**: Commit the plugin API schema as plugins/openapi.json
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

- **plugins**: Declare the 404 of GET /meetups/active in the contract
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

- **plugins**: Serve /api/v1/events with FastAPI's native server-sent events
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

### Refactoring

- **siesta**: Declare each call's request body in the endpoints! table
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

- **siesta**: Decode each answer as the type its endpoint declares
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

- **siesta**: Send every PyBall call through one endpoints! table
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))

### Testing

- **siesta**: Check siesta's calls against the committed plugin contract
  ([#27](https://github.com/lulivi/pyball/pull/27),
  [`5c73485`](https://github.com/lulivi/pyball/commit/5c734857450040b500f788ea0cae5aada34bc0ba))


## v7.2.0 (2026-11-22)

### Bug Fixes

- **alerts**: Keep an alert whose send failed free to retry
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Keep an alert's first word visible in Telegram
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Name the real source line of the shutdown alert
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Send HTTP server errors to the alert chat
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

### Features

- **alerts**: Post to the alert chat when PyBall starts and stops
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Rate-limit repeated alerts so a plugin crash loop stays bounded
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Send core warnings and errors to [pyball.alerts.telegram]
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))

- **alerts**: Send core warnings and errors to an alert channel in every topology
  ([#26](https://github.com/lulivi/pyball/pull/26),
  [`8f65181`](https://github.com/lulivi/pyball/commit/8f651815b817b3c355d3c7616ae9113f69c03044))


## v7.1.0 (2026-11-22)

### Bug Fixes

- **siesta**: Keep manual commands' changes while the plugin runs
  ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

### Build System

- **docker**: Ship siesta in the PyBall images ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

### Chores

- **siesta**: Import the siesta tool into plugins/siesta
  ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

### Continuous Integration

- Check bundled plugins with make plugins-check ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

### Documentation

- Document bundled plugins and siesta ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

### Features

- **siesta**: Run siesta as a scheduled plugin on the plugin API
  ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))

- **siesta**: Run siesta as a scheduled plugin shipped with PyBall
  ([#25](https://github.com/lulivi/pyball/pull/25),
  [`d2d9b47`](https://github.com/lulivi/pyball/commit/d2d9b47436c1b7468f93c83579367f5dd9cda3fd))


## v7.0.0 (2026-11-22)

### Bug Fixes

- **plugins**: Harden supervision and make reopening a search a no-op
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **settings**: Resolve workspace paths from the folder holding config.toml
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

### Build System

- **ci**: Install uv and nox with --root-user-action=ignore
  ([#16](https://github.com/lulivi/pyball/pull/16),
  [`21037dc`](https://github.com/lulivi/pyball/commit/21037dc3520c75b4913b55ae01b709173ffe1e6e))

### Continuous Integration

- Move actions off Node.js 20 and clear the pipeline warnings
  ([#16](https://github.com/lulivi/pyball/pull/16),
  [`21037dc`](https://github.com/lulivi/pyball/commit/21037dc3520c75b4913b55ae01b709173ffe1e6e))

- Move every action to its Node.js 24 major ([#16](https://github.com/lulivi/pyball/pull/16),
  [`21037dc`](https://github.com/lulivi/pyball/commit/21037dc3520c75b4913b55ae01b709173ffe1e6e))

### Documentation

- **plugins**: Keep each plugin's state in data/plugins/<name>/
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **plugins**: Show a neutral long-running plugin in the examples
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

### Features

- Expose a versioned plugin API with an event stream and host plugins
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **api**: Declare bearer authentication in the plugin API schema
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **api**: Expose a versioned plugin API at /api/v1 with an event stream
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **events**: Record every meetup event in a persistent, ordered log
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **manage**: Set a meetup's capacity and open or close its substitute search
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **meetup**: Give meetups a capacity and a substitute search
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **plugins**: Give each declared plugin its own scoped credential
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **plugins**: Run declared plugins as supervised child processes
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **signup**: Announce web joins and leaves like Telegram ones
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **telegram**: Post the substitutes callup when the core opens a search
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

### Refactoring

- Drop dead code and transition wording ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))

- **telegram**: Refresh the callups from the join and leave hooks
  ([#21](https://github.com/lulivi/pyball/pull/21),
  [`7f23574`](https://github.com/lulivi/pyball/commit/7f235740de83e397a801568364710dd7817dbad0))


## v6.10.0 (2026-11-19)

### Build System

- Run nox through uvx ([#12](https://github.com/lulivi/pyball/pull/12),
  [`3b1d2e6`](https://github.com/lulivi/pyball/commit/3b1d2e6122d9963cd122e3156731440baa260919))

### Chores

- Remove graphify and Superpowers tooling ([#12](https://github.com/lulivi/pyball/pull/12),
  [`3b1d2e6`](https://github.com/lulivi/pyball/commit/3b1d2e6122d9963cd122e3156731440baa260919))

- **agents**: Move agent skills to .agents/skills ([#12](https://github.com/lulivi/pyball/pull/12),
  [`3b1d2e6`](https://github.com/lulivi/pyball/commit/3b1d2e6122d9963cd122e3156731440baa260919))

### Continuous Integration

- Deploy every club with one compose file and one SSH call
  ([#13](https://github.com/lulivi/pyball/pull/13),
  [`7bf8041`](https://github.com/lulivi/pyball/commit/7bf8041340f18036a7dc8b19af5c81d59af58679))

### Documentation

- Add contributing and development guides ([#12](https://github.com/lulivi/pyball/pull/12),
  [`3b1d2e6`](https://github.com/lulivi/pyball/commit/3b1d2e6122d9963cd122e3156731440baa260919))

- **agents**: Slim down AGENTS.md ([#12](https://github.com/lulivi/pyball/pull/12),
  [`3b1d2e6`](https://github.com/lulivi/pyball/commit/3b1d2e6122d9963cd122e3156731440baa260919))

### Features

- **caddy**: Route clubs through one templated Caddyfile
  ([#15](https://github.com/lulivi/pyball/pull/15),
  [`a57f65f`](https://github.com/lulivi/pyball/commit/a57f65fdac1b6f9a6a897b478a384053cc3201dc))

### Testing

- **caddy**: Cover funnelbot's club discovery and routing state
  ([#15](https://github.com/lulivi/pyball/pull/15),
  [`a57f65f`](https://github.com/lulivi/pyball/commit/a57f65fdac1b6f9a6a897b478a384053cc3201dc))


## v6.9.1 (2026-11-17)

### Bug Fixes

- Point contributor conventions and bootstrap docs links at GitHub
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))

- **bootstrap**: Link the generated workspace README to the docs on GitHub
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))

### Continuous Integration

- Add GitHub Actions checks workflow with GHCR CI image
  ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Disable the GitLab pipeline until the move to GitHub Actions
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))

- Let the release job push to main past the required checks
  ([#10](https://github.com/lulivi/pyball/pull/10),
  [`1426289`](https://github.com/lulivi/pyball/commit/1426289c4c51b3ef3a132c666e1e80f9278ec12e))

- Lint the GitHub Actions workflows with actionlint ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Move checks, release, publish and deploy to GitHub Actions
  ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Push releases to main with a deploy key that bypasses the ruleset
  ([#10](https://github.com/lulivi/pyball/pull/10),
  [`1426289`](https://github.com/lulivi/pyball/commit/1426289c4c51b3ef3a132c666e1e80f9278ec12e))

- Release, publish and deploy from GitHub Actions ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Remove GitLab CI pipeline ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Run the checks only on pull requests and main ([#9](https://github.com/lulivi/pyball/pull/9),
  [`c5c8898`](https://github.com/lulivi/pyball/commit/c5c88987b365a529f42505bcbeb2b5c2b6b3d23b))

- Trust the workspace in the release job's container
  ([#10](https://github.com/lulivi/pyball/pull/10),
  [`1426289`](https://github.com/lulivi/pyball/commit/1426289c4c51b3ef3a132c666e1e80f9278ec12e))

### Documentation

- Drop references to the previous commit convention from AGENTS.md
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))

- Point the AGENTS.md commit, branch and PR conventions at GitHub
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))

### Testing

- **bootstrap**: Only assert the GitHub docs link in the generated README
  ([#6](https://github.com/lulivi/pyball/pull/6),
  [`62ccec5`](https://github.com/lulivi/pyball/commit/62ccec5d6fd9a1760a4bb6e68844919eeac6f668))


## v6.9.0 (2026-10-26)

### Features

- **GL-238**: Rank stats standings by points, then fewest matches played
  ([`551e4b6`](https://gitlab.com/lulivi/pyball/-/commit/551e4b613340a08760f640eadf1aa8a738cf9b30))


## v6.8.0 (2026-09-30)

### Features

- **GL-236..GL-237**: Add test-sound buttons and an idle clock screen to /match
  ([`04d05a5`](https://gitlab.com/lulivi/pyball/-/commit/04d05a5a6e94b8159c562128eeafebec90aefbc0))


## v6.7.0 (2026-09-28)

### Features

- **GL-235**: Reuse the teams edit mode for the signup roster in /manage
  ([`93348fe`](https://gitlab.com/lulivi/pyball/-/commit/93348fe629ef48e7fe91fd6a716d85f72053f661))


## v6.6.0 (2026-09-28)

### Features

- **GL-233..GL-234**: Close the substitute search automatically when its target is reached
  ([`6f4117b`](https://gitlab.com/lulivi/pyball/-/commit/6f4117b5dcdcaf49e5fe1f40f2f69a3d7a18e254))


## v6.5.0 (2026-09-23)

### Features

- **GL-232**: Restyle timer tab into titled cards with matching time size
  ([`ac363aa`](https://gitlab.com/lulivi/pyball/-/commit/ac363aa5667f87b19305a46a06e08d5c2a70dc8e))


## v6.4.0 (2026-09-23)

### Features

- **GL-230..GL-231**: Distinct match whistles and remove meetup lock
  ([`cee5247`](https://gitlab.com/lulivi/pyball/-/commit/cee52470fd643f2081d8f7f4de3d18927380ce59))

### Refactoring

- **GL-228..GL-229**: Unify season-boundary and match-outcome duplication
  ([`1df9698`](https://gitlab.com/lulivi/pyball/-/commit/1df96983bc48f634a83b2ded0bdf8e98d81f103c))


## v6.3.0 (2026-09-19)

### Features

- **GL-222..GL-227**: Add pitch-time warning alarm to /match Tiempo tab
  ([`3ac0434`](https://gitlab.com/lulivi/pyball/-/commit/3ac0434cd3c73f17ef755a5ba71d0bd34fc7cbf8))


## v6.2.0 (2026-09-16)

### Features

- **GL-218..GL-221**: Add copyable roster panel with unified convocatoria header format
  ([`f27af01`](https://gitlab.com/lulivi/pyball/-/commit/f27af01eb91acee2948e6c346b36a7d2bc06d293))


## v6.1.1 (2026-09-15)

### Bug Fixes

- **GL-217**: Pin match save button as fixed footer with scrollable events list
  ([`a637b4d`](https://gitlab.com/lulivi/pyball/-/commit/a637b4d1b0539438855ade61dbcc32f8cae86fab))


## v6.1.0 (2026-09-10)

### Features

- **GL-214..GL-216**: Meetup lifecycle activity feed and logging review
  ([`a7e706f`](https://gitlab.com/lulivi/pyball/-/commit/a7e706f0ef60e58c29b5cdca3d7a4e636168f56c))


## v6.0.0 (2026-09-10)

### Features

- **GL-210..GL-213**: Uniform Telegram ChatConfig tree for every message destination
  ([`4f6bb2a`](https://gitlab.com/lulivi/pyball/-/commit/4f6bb2a3ceed5673fbcc15be246291960027afb5))

### Breaking Changes

- **GL-210..GL-213**: Telegram `config.toml` keys change. `[pyball.telegram.regulars]`
  (`chat_id`/`meetups_thread_id`/`stats_thread_id`), `[pyball.telegram.substitutes]` `chat_id`,
  `[pyball.telegram.management]` `chat_id` and `[pyball.telegram.activity]` are replaced by
  `[pyball.telegram.regulars.meetups]`, `[pyball.telegram.regulars.stats]`,
  `[pyball.telegram.substitutes.meetups]`, `[pyball.telegram.management.logging]` and
  `[pyball.telegram.management.activity]`, each with `chat_id` + optional `message_thread_id`.
  Required: `telegram.regulars.meetups.chat_id` and `telegram.substitutes.meetups.chat_id`.


## v5.6.0 (2026-09-09)

### Features

- **GL-207..GL-209**: Notify activity chat on player join/leave
  ([`b359420`](https://gitlab.com/lulivi/pyball/-/commit/b359420bcb7684e220e864b4fe56521aa9c017e6))


## v5.5.0 (2026-09-09)

### Features

- **GL-203..GL-206**: Add a rotation timer to the /match wall
  ([`9145eed`](https://gitlab.com/lulivi/pyball/-/commit/9145eedbaf2d6284f42015e6490436bebd88183a))


## v5.4.2 (2026-09-08)

### Bug Fixes

- **GL-201**: Agrupar el panel de detalle de convocatoria pasada en /manage
  ([`407243a`](https://gitlab.com/lulivi/pyball/-/commit/407243a5f35a9ee1aa665ad41ec78c65569137ce))


## v5.4.1 (2026-09-07)

### Bug Fixes

- **GL-197..GL-200**: Remove suppressed native dialogs from the match page and make it
  offline-capable
  ([`36f121d`](https://gitlab.com/lulivi/pyball/-/commit/36f121d7ca099ca3900be1e419b9d686dd2bb938))


## v5.4.0 (2026-09-07)

### Features

- **GL-193..GL-196**: Self-contained copy-teams message + swap-teams in /manage
  ([`f2a0ca0`](https://gitlab.com/lulivi/pyball/-/commit/f2a0ca0fd4fac49a7cc10490e2a14bdb2a8e9c64))


## v5.3.2 (2026-09-07)

### Bug Fixes

- **GL-191**: Honor a 2-color team_colors list instead of silently defaulting
  ([`c88c9de`](https://gitlab.com/lulivi/pyball/-/commit/c88c9def2c203a9775e8d9a4d4021f13e9fec1cd))

### Testing

- **GL-192**: Derive season-boundary test dates from the current season
  ([`ed510ca`](https://gitlab.com/lulivi/pyball/-/commit/ed510ca7eaeacb49497365a71bc6815e986c89bc))


## v5.3.1 (2026-08-21)

### Bug Fixes

- **GL-190**: Precache page shells and add /manage offline screen
  ([`998c5fb`](https://gitlab.com/lulivi/pyball/-/commit/998c5fb2652bda76b664e752089d83d7d08ec08e))


## v5.3.0 (2026-08-12)

### Features

- **GL-185..GL-189**: Simplify sharing signup codes and links from /manage
  ([`89c8026`](https://gitlab.com/lulivi/pyball/-/commit/89c802669b1735405e2701d240cd81fc913748c2))


## v5.2.0 (2026-08-01)

### Documentation

- **GL-181**: Document self-hosting without a VPS (Windows WSL2 + deployment guide)
  ([`cf20078`](https://gitlab.com/lulivi/pyball/-/commit/cf20078a37262761c8e0de1de768519c3d44ecb2))

### Features

- **GL-182..GL-184**: Add pages reference docs and goalkeeper indicators in /manage
  ([`841f224`](https://gitlab.com/lulivi/pyball/-/commit/841f224c8387ca568ef8e7c1e6d24c724405e9ee))


## v5.1.0 (2026-07-17)

### Features

- **GL-177..GL-180**: Add signup code copy modal and improve /signup team visuals
  ([`40d741b`](https://gitlab.com/lulivi/pyball/-/commit/40d741bee805dc98b5e59ec435270ec09689f237))


## v5.0.0 (2026-07-17)

### Features

- **GL-153..GL-176**: Add self-service /signup and unify FastAPI topologies
  ([`9c64ada`](https://gitlab.com/lulivi/pyball/-/commit/9c64adaac3a340d6b738894f834c4376cdb7d9e7))


## v4.19.0 (2026-07-16)

### Features

- **GL-144..GL-152**: Add meetup signup lock, destroy-teams, and /meetup_show
  ([`60528d6`](https://gitlab.com/lulivi/pyball/-/commit/60528d6a18df37073d0294bcf5c81515f986f28c))


## v4.18.0 (2026-07-15)

### Features

- **GL-117..GL-143**: Move meetup management to /manage, keep Telegram for signup/search/stats
  ([`7cfa10e`](https://gitlab.com/lulivi/pyball/-/commit/7cfa10eec9ec44e64871453fabff0af1f8d25474))


## v4.17.1 (2026-07-14)

### Bug Fixes

- **GL-103..GL-108**: Refactor balanced algorithm, fix scoring bugs, cache pair keys
  ([`e670a3c`](https://gitlab.com/lulivi/pyball/-/commit/e670a3c5f6faf7da80891f3f2c4d5e0995342b06))


## v4.17.0 (2026-07-13)

### Features

- **GL-92..GL-102**: Add player positions and a per-team goalkeeper
  ([`d49219c`](https://gitlab.com/lulivi/pyball/-/commit/d49219c393954efa79eb880fb4b1cafd67d53fe2))


## v4.16.0 (2026-07-11)

### Features

- **GL-88,GL-89,GL-90**: Unify Telegram subs header, add search + separator keyboard buttons
  ([`85dfca7`](https://gitlab.com/lulivi/pyball/-/commit/85dfca71cedc34ee5577f8d030a02f0b1c10ab88))


## v4.15.0 (2026-07-10)

### Features

- **GL-60..GL-87**: Add triangular (3-team) tournament support
  ([`9e5a46b`](https://gitlab.com/lulivi/pyball/-/commit/9e5a46b09c14822b16e1f33fa15e7e2adc8aed7c))


## v4.14.0 (2026-07-06)

### Features

- **GL-47,GL-48,GL-49**: Add --bootstrap command for first-time deployment setup
  ([`5e2a4a8`](https://gitlab.com/lulivi/pyball/-/commit/5e2a4a813453b7c11cc2219391101451e0443531))


## v4.13.0 (2026-06-17)

### Features

- **GL-46**: Refresh Telegram messages from web UI meetup mutations
  ([`d5837c4`](https://gitlab.com/lulivi/pyball/-/commit/d5837c4c7411e29454950c61f783f543057ee8fb))


## v4.12.0 (2026-06-16)

### Features

- **GL-44,GL-45**: Rename bot commands and fix old Chrome match wall
  ([`f33d1c6`](https://gitlab.com/lulivi/pyball/-/commit/f33d1c6eafe8e2a2b5dd3c072887642d0efca2ed))


## v4.11.3 (2026-06-14)

### Bug Fixes

- **GL-43**: Default funnelbot APPS_DIR to the new pyball layout
  ([`3cd2850`](https://gitlab.com/lulivi/pyball/-/commit/3cd2850594064753c6ada369b805a5b12873307c))


## v4.11.2 (2026-06-14)

### Bug Fixes

- **GL-43**: Adapt funnelbot and deploy to the new VPS layout
  ([`182b05f`](https://gitlab.com/lulivi/pyball/-/commit/182b05fdd5826c971100f8aecd00a01aac990cfa))


## v4.11.1 (2026-06-13)

### Bug Fixes

- **GL-42**: Run tag pipelines and skip caddy deploys when unchanged
  ([`077b00f`](https://gitlab.com/lulivi/pyball/-/commit/077b00f1c077af1572011b94c36019bb1d55d42b))


## v4.11.0 (2026-06-12)

### Continuous Integration

- **GL-40**: Add semantic-release continuous delivery pipeline
  ([`09c9230`](https://gitlab.com/lulivi/pyball/-/commit/09c92303ec2e44327db6cde2fe073c636d305cf8))

### Features

- **GL-41**: Identify rename target by player name instead of ID
  ([`cbe5e6a`](https://gitlab.com/lulivi/pyball/-/commit/cbe5e6a5a95018f7b9e0a79faa467d7a9f545823))
