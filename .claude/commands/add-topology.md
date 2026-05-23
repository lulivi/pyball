# Add a New Application Topology

Use this skill when adding a new infrastructure integration as a standalone runnable
topology (e.g. WhatsApp, Slack, Discord). This is the **five-step pattern** derived from
the Composition Root architecture.

## Prerequisites

- The new library is available on PyPI.
- You have a settings loader, a `MatchNotifier` implementation, and optionally a logging
  handler for the new integration.

## Step 1 — Optional dependency

In `pyproject.toml`, add the library under `[project.optional-dependencies]`:

```toml
[project.optional-dependencies]
telegram = ["python-telegram-bot>=22,<23"]
whatsapp = ["some-whatsapp-library>=1,<2"]   # ← new
```

Run `uv sync --all-extras` to install.

## Step 2 — Integration settings

Create `pyball/infrastructure/<integration>/settings.py`:

```python
from pyball.settings import AppSettings, SettingsValidationError

@dataclass
class WhatsAppSettings:
    """WhatsApp-specific config (api_key, phone_number_id, etc.)."""
    ...

@dataclass
class WhatsAppAppSettings(AppSettings):
    """Combined settings for the WhatsApp topology."""
    whatsapp: WhatsAppSettings = field(default_factory=WhatsAppSettings)

def load_whatsapp_app_settings(
    base: AppSettings,
    config_path: Path = Path("config.toml"),
) -> WhatsAppAppSettings:
    """Load and validate WhatsApp settings, extending base AppSettings."""
    ...
    # Validate required fields, raise SettingsValidationError if missing
    return WhatsAppAppSettings(pyball=base.pyball, paths=base.paths, whatsapp=whatsapp)
```

## Step 3 — Integration logging (if needed)

Create `pyball/infrastructure/<integration>/logging.py`:

```python
def config_whatsapp_logging(settings: WhatsAppSettings) -> None:
    """Add integration-specific log handler to the root logger if configured."""
    ...
```

## Step 4 — Entrypoint

Create `pyball/cmd/run_<integration>.py`:

```python
from pyball.application.bootstrap import bootstrap_core
from pyball.infrastructure.<integration>.settings import load_whatsapp_app_settings
from pyball.infrastructure.<integration>.logging import config_whatsapp_logging

def main() -> None:
    asyncio.run(_main_async())

async def _main_async() -> None:
    app_settings, container = bootstrap_core()
    tg_settings = load_whatsapp_app_settings(app_settings)
    config_whatsapp_logging(tg_settings.whatsapp)
    # ... wire notifier, FastAPI app, graceful shutdown
    # Graceful shutdown pattern:
    stop_event = asyncio.Event()
    loop = asyncio.get_running_loop()
    for sig in (signal.SIGINT, signal.SIGTERM):
        loop.add_signal_handler(sig, stop_event.set)
    # ... await stop_event.wait() then cleanup
```

## Step 5 — Script entry point

In `pyproject.toml`:

```toml
[project.scripts]
pyball-web       = "pyball.cmd.run_web:main"
pyball-tg        = "pyball.cmd.run_telegram:main"
pyball-whatsapp  = "pyball.cmd.run_whatsapp:main"   # ← new
```

Run `uv sync --all-extras` after editing `pyproject.toml`.

## Files that do NOT change

- `pyball/settings.py` — `AppSettings` and `load_app_settings()` are integration-agnostic.
- `pyball/application/bootstrap.py` — `bootstrap_core()` is shared and stable.
- `pyball/domain/` and `pyball/application/` use cases — zero changes.

## Docker

Add a new final stage in `docker/Dockerfile`:

```dockerfile
FROM base AS whatsapp
RUN WHEEL=$(ls /builder/*.whl) && \
    $VIRTUAL_ENV/bin/pip install --no-cache "${WHEEL}[whatsapp]" \
    && rm -rf /builder
WORKDIR /pyball
COPY static/ static/
RUN chown -R pyballuser:pyballgroup /pyball
USER pyballuser
ENTRYPOINT ["pyball-whatsapp"]
```

Update `deploy/docker_build.sh` to allow `--topology whatsapp`.
