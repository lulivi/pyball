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
"""The committed plugin contract: plugins/openapi.json, regenerated with `make openapi`."""

from __future__ import annotations

import json
import sys
from pathlib import Path
from typing import Any, cast

from pyball.infrastructure.plugins.api import create_plugin_api
from pyball.infrastructure.plugins.auth import PluginCredentials

SCHEMA_PATH = Path("plugins/openapi.json")


def main() -> None:
    """Write the plugin API schema to the path given, plugins/openapi.json by default."""
    path = Path(sys.argv[1]) if len(sys.argv) > 1 else SCHEMA_PATH
    path.write_text(schema_text(), encoding="utf-8")


def schema_text() -> str:
    """Return the /api/v1 OpenAPI schema as the committed file holds it."""
    # Building the routes reads neither the container nor the notifier: only requests do.
    api = create_plugin_api(cast(Any, None), cast(Any, None), PluginCredentials([]))
    return json.dumps(api.openapi(), indent=2, ensure_ascii=False) + "\n"


if __name__ == "__main__":
    main()
