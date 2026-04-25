# QR Code on Match Start — Implementation Plan

> **For agentic workers:** REQUIRED SUB-SKILL: Use superpowers:subagent-driven-development (recommended) or superpowers:executing-plans to implement this plan task-by-task. Steps use checkbox (`- [ ]`) syntax for tracking.

**Goal:** When `/start_match` is executed, send a QR code image to each admin with the match tracking URL as the photo caption, replacing the current plain-text message.

**Architecture:** Add `qrcode[pil]` dependency, introduce a pure `generate_qr_bytes(url)` helper in the meetup handler module, and swap `send_message` for `send_photo` in `start_match_handler`.

**Tech Stack:** `qrcode[pil]>=8,<9`, `python-telegram-bot>=22`

---

## Files

- Modify: `pyproject.toml` — add `qrcode[pil]` dependency
- Modify: `pyball/bot/handlers/meetup.py` — add `generate_qr_bytes`, update `start_match_handler`
- Modify: `tests/unit/bot/handlers/test_meetup_handlers.py` — add tests

---

### Task 1: Add `qrcode[pil]` dependency

**Files:**
- Modify: `pyproject.toml`

- [ ] **Step 1: Add dependency**

In `pyproject.toml`, add `qrcode[pil]>=8,<9` to the `dependencies` list (after `pymupdf`):

```toml
dependencies = [
    "python-telegram-bot>=22,<23",
    "pydantic>=2.0,<3",
    "fastapi>=0.110",
    "uvicorn[standard]>=0.29",
    "jinja2>=3.1,<4",
    "weasyprint>=61,<70",
    "pymupdf>=1.24,<2",
    "qrcode[pil]>=8,<9",
]
```

- [ ] **Step 2: Sync the environment**

```bash
pip install -e ".[dev]"
```

Expected: `Successfully installed qrcode-...` (or already satisfied).

- [ ] **Step 3: Verify import works**

```bash
python -c "import qrcode; print('ok')"
```

Expected: `ok`

- [ ] **Step 4: Commit**

```bash
git add pyproject.toml
git commit -m "chore: add qrcode[pil] dependency"
```

---

### Task 2: Add `generate_qr_bytes` helper

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`
- Modify: `tests/unit/bot/handlers/test_meetup_handlers.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/bot/handlers/test_meetup_handlers.py`:

```python
from io import BytesIO

from pyball.bot.handlers.meetup import generate_qr_bytes


def test_generate_qr_bytes_returns_png_buffer():
    buf = generate_qr_bytes("https://example.com/match?date=2026-04-19")
    assert isinstance(buf, BytesIO)
    header = buf.read(4)
    assert header == b"\x89PNG"
```

- [ ] **Step 2: Run test to verify it fails**

```bash
nox -e test -- tests/unit/bot/handlers/test_meetup_handlers.py::test_generate_qr_bytes_returns_png_buffer -v
```

Expected: FAIL with `ImportError: cannot import name 'generate_qr_bytes'`

- [ ] **Step 3: Add imports and implement helper**

In `pyball/bot/handlers/meetup.py`, add to the existing imports block (after `import logging`):

```python
import qrcode
from io import BytesIO
```

Then add the function after the `logger` line (line 28, before the first handler):

```python

def generate_qr_bytes(url: str) -> BytesIO:
    """Generate a PNG QR code for url and return it as a seeked BytesIO buffer."""
    img = qrcode.make(url)
    buf = BytesIO()
    img.save(buf, format="PNG")
    buf.seek(0)
    return buf
```

- [ ] **Step 4: Run test to verify it passes**

```bash
nox -e test -- tests/unit/bot/handlers/test_meetup_handlers.py::test_generate_qr_bytes_returns_png_buffer -v
```

Expected: PASS

- [ ] **Step 5: Commit**

```bash
git add pyball/bot/handlers/meetup.py tests/unit/bot/handlers/test_meetup_handlers.py
git commit -m "feat: add generate_qr_bytes helper"
```

---

### Task 3: Update `start_match_handler` to send QR photo

**Files:**
- Modify: `pyball/bot/handlers/meetup.py`
- Modify: `tests/unit/bot/handlers/test_meetup_handlers.py`

- [ ] **Step 1: Write the failing test**

Add to `tests/unit/bot/handlers/test_meetup_handlers.py`:

```python
from unittest.mock import AsyncMock, MagicMock, patch

from pyball.bot.handlers.meetup import start_match_handler


@pytest.mark.asyncio
async def test_start_match_handler_sends_qr_photo(mock_update, mock_context):
    url = "https://pyball.example.com/?date=2026-04-19T20%3A00&teamA=Ana&teamB=Bob"
    admin_id = 99999

    container = MagicMock()
    container.start_match.return_value.execute.return_value = url
    mock_context.bot_data["container"] = container
    mock_context.args = ["2026/04/19", "20:00"]
    mock_context.bot_data["settings"].telegram.admins_ids = [admin_id]
    mock_context.bot = AsyncMock()
    mock_context.bot.send_photo = AsyncMock()

    fake_buf = BytesIO(b"fakepng")

    with patch(
        "pyball.bot.handlers.meetup.generate_qr_bytes", return_value=fake_buf
    ) as mock_qr:
        await start_match_handler(mock_update, mock_context)

    mock_qr.assert_called_once_with(url)
    mock_context.bot.send_photo.assert_called_once_with(
        chat_id=admin_id,
        photo=fake_buf,
        caption=f"🔗 Enlace del partido:\n{url}",
    )
```

- [ ] **Step 2: Run test to verify it fails**

```bash
nox -e test -- tests/unit/bot/handlers/test_meetup_handlers.py::test_start_match_handler_sends_qr_photo -v
```

Expected: FAIL — handler calls `send_message`, not `send_photo`.

- [ ] **Step 3: Update the handler**

In `pyball/bot/handlers/meetup.py`, replace the inner loop inside `start_match_handler` (lines 114–122):

```python
        url = container.start_match().execute(date_str)
        qr = generate_qr_bytes(url)
        for admin in telegram_settings.admins_ids:
            try:
                qr.seek(0)
                await context.bot.send_photo(
                    chat_id=admin,
                    photo=qr,
                    caption=f"🔗 Enlace del partido:\n{url}",
                )
            except telegram.error.Forbidden:
                logger.error("Could not send message to '%s' admin", admin)
```

Remove the `disable_web_page_preview=True` kwarg (no longer relevant for photos).

- [ ] **Step 4: Run test to verify it passes**

```bash
nox -e test -- tests/unit/bot/handlers/test_meetup_handlers.py::test_start_match_handler_sends_qr_photo -v
```

Expected: PASS

- [ ] **Step 5: Run full test suite**

```bash
make test
```

Expected: all tests pass, coverage report printed.

- [ ] **Step 6: Run linter**

```bash
make lint
```

Expected: no errors, pylint score 10.00/10.

- [ ] **Step 7: Commit**

```bash
git add pyball/bot/handlers/meetup.py tests/unit/bot/handlers/test_meetup_handlers.py
git commit -m "feat: send QR photo on /start_match instead of plain URL"
```
