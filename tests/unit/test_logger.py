# Copyright (c) 2026 Luis Liñán
#
# Permission is hereby granted, free of charge, to any person obtaining a copy
# of this software and associated documentation files (the "Software"), to deal
# in the Software without restriction, including without limitation the rights
# to use, copy, modify, merge, publish, distribute, sublicense, and/or sell
# copies of the Software, and to permit persons to whom the Software is
# furnished to do so, subject to the following conditions:
#
# The above copyright notice and this permission notice shall be included in all
# copies or substantial portions of the Software.
#
# THE SOFTWARE IS PROVIDED "AS IS", WITHOUT WARRANTY OF ANY KIND, EXPRESS OR
# IMPLIED, INCLUDING BUT NOT LIMITED TO THE WARRANTIES OF MERCHANTABILITY,
# FITNESS FOR A PARTICULAR PURPOSE AND NONINFRINGEMENT. IN NO EVENT SHALL THE
# AUTHORS OR COPYRIGHT HOLDERS BE LIABLE FOR ANY CLAIM, DAMAGES OR OTHER
# LIABILITY, WHETHER IN AN ACTION OF CONTRACT, TORT OR OTHERWISE, ARISING FROM,
# OUT OF OR IN CONNECTION WITH THE SOFTWARE OR THE USE OR OTHER DEALINGS IN THE
# SOFTWARE.

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
