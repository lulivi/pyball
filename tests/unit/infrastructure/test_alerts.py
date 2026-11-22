"""Tests for the alert channel: filter, Telegram handler and config_alerts."""

import json
import logging
import sys
from unittest.mock import MagicMock, patch

import pytest

from pyball.infrastructure.alerts import TelegramAlertHandler, _AlertFilter, config_alerts
from pyball.settings import TelegramAlerts


def _record(name: str, level: int) -> logging.LogRecord:
    return logging.LogRecord(
        name=name, level=level, pathname="", lineno=1, msg="msg", args=(), exc_info=None
    )


class TestAlertFilter:
    """Tests for _AlertFilter: pyball.* at WARNING+, any other logger at ERROR+."""

    @pytest.mark.parametrize(
        "name, level",
        [
            ("pyball.infrastructure.plugins.supervisor", logging.WARNING),
            ("pyball.bot", logging.ERROR),
            ("telegram.ext", logging.ERROR),
            ("uvicorn.error", logging.CRITICAL),
            ("", logging.ERROR),
        ],
    )
    def test_alerts_pass(self, name, level):
        """Core warnings and errors from any logger are alerts."""
        assert _AlertFilter().filter(_record(name, level))

    @pytest.mark.parametrize(
        "name, level",
        [
            ("pyball.plugins.siesta", logging.INFO),
            ("pyball.domain", logging.DEBUG),
            ("telegram", logging.WARNING),
            ("httpx", logging.WARNING),
            ("pyball", logging.WARNING),
            ("pyballfoo", logging.WARNING),
        ],
    )
    def test_non_alerts_blocked(self, name, level):
        """Plugin output, debug noise and third-party warnings are not alerts."""
        assert not _AlertFilter().filter(_record(name, level))


class TestTelegramAlertHandler:
    """Tests for TelegramAlertHandler.emit()."""

    _PATCH = "pyball.infrastructure.alerts.urllib.request.urlopen"

    def _make_record(  # pylint: disable=too-many-arguments,too-many-positional-arguments
        self,
        name: str = "pyball.bot",
        level: int = logging.INFO,
        lineno: int = 42,
        msg: str = "test message",
        exc_info=None,
    ) -> logging.LogRecord:
        return logging.LogRecord(
            name=name,
            level=level,
            pathname="",
            lineno=lineno,
            msg=msg,
            args=(),
            exc_info=exc_info,
        )

    def _payload(self, mock_urlopen) -> dict:
        return json.loads(mock_urlopen.call_args.args[0].data)

    def test_posts_to_correct_url(self):
        """emit() uses the configured token in the sendMessage URL."""
        handler = TelegramAlertHandler("mytoken", -100111)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert m.call_args.args[0].full_url == "https://api.telegram.org/botmytoken/sendMessage"

    def test_sends_chat_id(self):
        """emit() includes chat_id in the payload."""
        handler = TelegramAlertHandler("tok", -100999)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["chat_id"] == -100999

    def test_uses_markdownv2(self):
        """emit() sets parse_mode to MarkdownV2."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["parse_mode"] == "MarkdownV2"

    def test_info_emoji(self):
        """INFO records use the ℹ️ emoji."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.INFO))
        assert "ℹ️" in self._payload(m)["text"]

    def test_warning_emoji(self):
        """WARNING records use the ⚠️ emoji."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.WARNING))
        assert "⚠️" in self._payload(m)["text"]

    def test_error_emoji(self):
        """ERROR records use the 🔴 emoji."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.ERROR))
        assert "🔴" in self._payload(m)["text"]

    def test_critical_emoji(self):
        """CRITICAL records use the 💀 emoji."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(level=logging.CRITICAL))
        assert "💀" in self._payload(m)["text"]

    def test_includes_message(self):
        """Text contains the log message."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record(msg="something broke"))
        assert "something broke" in self._payload(m)["text"]

    def test_includes_traceback(self):
        """Text includes the traceback when exc_info is present."""
        handler = TelegramAlertHandler("tok", -1)
        try:
            raise ValueError("kaboom")
        except ValueError:
            exc_info = sys.exc_info()
        record = self._make_record(level=logging.ERROR, exc_info=exc_info)
        with patch(self._PATCH) as m:
            handler.emit(record)
        text = self._payload(m)["text"]
        assert "ValueError" in text
        assert "kaboom" in text

    def test_wraps_in_code_block(self):
        """Text is wrapped in a MarkdownV2 code block."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        text = self._payload(m)["text"]
        assert "```" in text
        assert text.endswith("\n```")

    def test_silences_network_exception(self):
        """Network errors in emit() call handleError, not propagate."""
        handler = TelegramAlertHandler("tok", -1)
        mock_handle_error = MagicMock()
        setattr(handler, "handleError", mock_handle_error)
        record = self._make_record()
        with patch(self._PATCH) as m:
            m.side_effect = OSError("network down")
            handler.emit(record)
        mock_handle_error.assert_called_once_with(record)

    def test_includes_message_thread_id_when_set(self):
        """emit() adds message_thread_id to the payload when configured."""
        handler = TelegramAlertHandler("tok", -100999, message_thread_id=77)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert self._payload(m)["message_thread_id"] == 77

    def test_omits_message_thread_id_when_none(self):
        """emit() leaves message_thread_id out of the payload when not configured."""
        handler = TelegramAlertHandler("tok", -100999)
        with patch(self._PATCH) as m:
            handler.emit(self._make_record())
        assert "message_thread_id" not in self._payload(m)


class TestRepeatedAlerts:
    """Tests for the per-alert REPEAT_WINDOW in TelegramAlertHandler."""

    _URLOPEN = "pyball.infrastructure.alerts.urllib.request.urlopen"
    _CLOCK = "pyball.infrastructure.alerts.time.monotonic"

    def _record(self, plugin: str | None = None, lineno: int = 10) -> logging.LogRecord:
        record = logging.LogRecord(
            "pyball.infrastructure.plugins.supervisor",
            logging.WARNING,
            "",
            lineno,
            "Plugin stopped",
            (),
            None,
        )
        if plugin:
            record.plugin = plugin
        return record

    def _send(self, handler, clock, now: float, record: logging.LogRecord) -> None:
        clock.return_value = now
        handler.emit(record)

    def test_repeats_inside_the_window_are_counted_not_sent(self):
        """A crash loop sends one alert per window, the next one counting the rest."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._URLOPEN) as urlopen, patch(self._CLOCK) as clock:
            for second in range(0, 600, 60):  # ten restarts, one a minute
                self._send(handler, clock, second, self._record("siesta"))
            assert urlopen.call_count == 1
            self._send(handler, clock, 600, self._record("siesta"))
        assert urlopen.call_count == 2
        text = json.loads(urlopen.call_args.args[0].data)["text"]
        assert text.endswith("\\(\\+9 alertas iguales omitidas\\)")

    def test_different_plugins_and_lines_are_separate_alerts(self):
        """One plugin's crash loop does not hide another's, nor a different alert."""
        handler = TelegramAlertHandler("tok", -1)
        with patch(self._URLOPEN) as urlopen, patch(self._CLOCK) as clock:
            self._send(handler, clock, 0, self._record("siesta"))
            self._send(handler, clock, 1, self._record("activity"))
            self._send(handler, clock, 2, self._record("siesta", lineno=99))
            self._send(handler, clock, 3, self._record("siesta"))
        assert urlopen.call_count == 3
        assert "omitidas" not in json.loads(urlopen.call_args.args[0].data)["text"]


class TestConfigAlerts:
    """Tests for config_alerts."""

    @pytest.fixture
    def root(self):
        """Yield the root logger and remove whatever handlers a test adds to it."""
        root_logger = logging.getLogger()
        before = list(root_logger.handlers)
        yield root_logger
        for handler in root_logger.handlers[:]:
            if handler not in before:
                root_logger.removeHandler(handler)

    def test_warns_and_adds_nothing_when_off(self, root, caplog):
        """Without alerts configured nothing is installed and a warning says so."""
        before = list(root.handlers)
        with caplog.at_level(logging.WARNING, logger="pyball.infrastructure.alerts"):
            config_alerts(None)
        assert root.handlers == before
        assert any("pyball.alerts.telegram no está configurado" in m for m in caplog.messages)

    def test_sends_core_error_through_the_queue(self, root):
        """A core error reaches the configured chat, with no bot and no plugin running."""
        with patch("pyball.infrastructure.alerts.atexit.register") as register, patch(
            "pyball.infrastructure.alerts.urllib.request.urlopen"
        ) as urlopen:
            config_alerts(TelegramAlerts("tok", -100111, 5))
            stop_listener = register.call_args.args[0]
            try:
                raise ValueError("kaboom")
            except ValueError:
                logging.getLogger("pyball.application.x").exception("it broke")
            logging.getLogger("pyball.plugins.siesta").info("plugin chatter")
            stop_listener()  # drains the queue
        (call,) = urlopen.call_args_list
        payload = json.loads(call.args[0].data)
        assert call.args[0].full_url == "https://api.telegram.org/bottok/sendMessage"
        assert payload["chat_id"] == -100111
        assert payload["message_thread_id"] == 5
        assert "it broke" in payload["text"]
        assert "kaboom" in payload["text"]
        assert any(isinstance(h, logging.handlers.QueueHandler) for h in root.handlers)
