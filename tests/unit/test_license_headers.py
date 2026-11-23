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

"""Every source file carries the license header."""

import re
from pathlib import Path

ROOT = Path(__file__).parents[2]
SOURCES = ("*.py", "*.rs", "*.sh", "*.bash", "Makefile")
SKIPPED = {".git", ".venv", ".nox", "target", "node_modules", "__pycache__"}
NOTICE = re.compile(r"Copyright \(c\) \d{4} Luis Liñán")


def test_every_source_file_starts_with_the_license():
    """Each .py, .rs, .sh and Makefile has the copyright notice in its first lines."""
    sources = [
        path
        for pattern in SOURCES
        for path in ROOT.rglob(pattern)
        if not SKIPPED & set(path.relative_to(ROOT).parts)
    ]
    missing = [
        str(path.relative_to(ROOT))
        for path in sources
        if not NOTICE.search(path.read_text("utf-8")[:300])
    ]
    assert not missing, f"add the license header to: {', '.join(sorted(missing))}"
