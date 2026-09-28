# CHANGELOG

<!-- version list -->

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
