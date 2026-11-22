"""Tests for pyball.logger shared utilities."""

from pyball.logger import log_func, timed_rotating_file_handler


class TestLogFunc:
    """Tests for the log_func decorator."""

    def test_wraps_return_value(self):
        """log_func returns the wrapped function's return value."""

        @log_func
        def add(a, b):
            return a + b

        assert add(1, 2) == 3

    def test_preserves_function_name(self):
        """log_func preserves __name__ via functools.wraps."""

        @log_func
        def my_function():
            pass

        assert my_function.__name__ == "my_function"


class TestTimedRotatingFileHandler:
    """Tests for timed_rotating_file_handler."""

    def test_returns_handler_with_filter(self, tmp_path):
        """Returns a handler that has a filter for the given string."""
        handler = timed_rotating_file_handler(tmp_path / "test.log", "pyball.test")
        try:
            assert any(f.name == "pyball.test" for f in handler.filters)
        finally:
            handler.close()
