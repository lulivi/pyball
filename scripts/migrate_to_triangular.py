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
"""One-time migration: rewrite meetup JSON files from the old teams(2)+result schema
to the new teams(N)+matches+closed schema. Run once before deploying triangular support.

Usage: python -m scripts.migrate_to_triangular <meetups_dir>
"""

from __future__ import annotations

import json
import sys
from pathlib import Path


def migrate_meetup_dict(data: dict) -> dict:
    """Return a copy of a meetup dict rewritten into the new matches/closed schema.

    Idempotent: a dict that already has "matches" is returned unchanged.
    """
    if "matches" in data:
        return data

    migrated = {k: v for k, v in data.items() if k != "result"}
    result = data.get("result")
    teams = data.get("teams")

    if result is not None and teams is not None:
        migrated["matches"] = [
            {
                "teams_playing": [teams[0]["name"], teams[1]["name"]],
                "result": result,
            }
        ]
        migrated["closed"] = True
    else:
        migrated["matches"] = []
        migrated["closed"] = False

    return migrated


def migrate_directory(directory: Path) -> int:
    """Rewrite every *.json file in directory in place. Returns the count migrated."""
    count = 0
    for file_path in directory.glob("*.json"):
        with open(file_path, encoding="utf-8") as f:
            data = json.load(f)
        migrated = migrate_meetup_dict(data)
        if migrated is not data:
            with open(file_path, "w", encoding="utf-8") as f:
                json.dump(migrated, f, indent=2)
            count += 1
    return count


def main() -> None:
    """CLI entry point."""
    if len(sys.argv) != 2:
        print("Usage: python -m scripts.migrate_to_triangular <meetups_dir>")
        sys.exit(1)
    directory = Path(sys.argv[1])
    count = migrate_directory(directory)
    print(f"Migrated {count} meetup file(s) in {directory}")


if __name__ == "__main__":
    main()
