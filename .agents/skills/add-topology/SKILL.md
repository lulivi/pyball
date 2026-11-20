---
name: add-topology
description: Add a new runnable PyBall topology — an integration (WhatsApp, Slack, Discord, ...) with its own entrypoint, optional dependency and Docker image. Use when wiring a new messaging integration beside pyball and pyball-telegram.
---

# Add a topology

A topology is one `pyball/cmd/run_<name>.py` Composition Root plus its packaging. Copy the
`pyball-telegram` topology at every step: it is the reference implementation. The domain,
the application use cases, `pyball/settings.py` and `application/bootstrap.py` stay
unchanged; an integration only adds infrastructure around them.

## Steps

1. **Optional dependency.** Add the integration's library under
   `[project.optional-dependencies]` in `pyproject.toml`, beside `telegram`. Only this
   topology installs it.
2. **Settings.** Create `pyball/infrastructure/<name>/settings.py`, modelled on
   `infrastructure/telegram/settings.py`: a `<Name>Settings` dataclass, a
   `<Name>AppSettings(AppSettings)` that adds it, and a `load_<name>_app_settings()` that
   reads its `[pyball.<name>]` section, applies `PYBALL_<NAME>_<KEY>` env overrides, and
   raises `SettingsValidationError` for missing required values. Every new key follows
   the `add-config-key` skill.
3. **Notifier.** Implement `MatchNotifier` (`application/notifier.py`) for the
   integration, as `infrastructure/telegram/notifications.py` does.
4. **Logging (if the integration has a log sink).** Add
   `infrastructure/<name>/logging.py` with a `config_<name>_logging()`, modelled on
   `infrastructure/telegram/logging.py`.
5. **Entrypoint.** Create `pyball/cmd/run_<name>.py`, modelled on `cmd/run_telegram.py`:
   `--config` and `--bootstrap` arguments, `bootstrap_core()`, the integration's settings
   and logging, the notifier and FastAPI app wired together, and graceful shutdown on
   SIGINT/SIGTERM. Keep the plugin host wiring as `run_telegram.py` has it:
   `CompositeMatchNotifier` with `EventLogNotifier(container.event_log)` first, one
   `PluginCredentials` shared by `create_app()` and `PluginSupervisor`, the supervisor
   started after `wait_until_serving()`, and on shutdown the supervisor stopped before
   `event_log.close_subscribers()` and the server exit.
6. **Script.** Add `pyball-<name> = "pyball.cmd.run_<name>:main"` under
   `[project.scripts]` in `pyproject.toml`, then run `uv sync --all-extras`.
7. **Bootstrap workspace.** Teach `application/init_workspace.py` the new topology: its
   label, `config.toml` extra section, `compose.yaml` and README templates, as it does for
   `"tg"`.
8. **Docker.** Add a final stage to `docker/Dockerfile` modelled on the `telegram` stage
   (install the wheel with the new extra, `ENTRYPOINT ["pyball-<name>"]`), accept the
   topology in `deploy/docker_build.sh`, and add it to the `topology` matrix of the
   `publish-deploy` job in `.github/workflows/ci.yml`.
9. **Docs.** Add the topology to `docs/setup.md`, `docs/development.md` and their `.es.md`
   twins.

Done when `uv run pyball-<name> --bootstrap` generates a working workspace, the new
Docker stage builds, and `make lint` and `make test` pass with tests for the new settings
loader and notifier.
