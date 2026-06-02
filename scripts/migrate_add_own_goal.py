#!/usr/bin/env python3
"""One-shot migration: add is_own_goal=false to all existing goal events."""

import json
from pathlib import Path


def migrate(data_dir: Path) -> None:
    """Add is_own_goal=false to every event that does not have the field."""
    meetups_dir = data_dir / "meetups"
    if not meetups_dir.exists():
        print(f"No meetups directory at {meetups_dir}")
        return

    touched = 0
    for path in sorted(meetups_dir.glob("*.json")):
        with open(path, encoding="utf-8") as f:
            data = json.load(f)

        changed = False
        result = data.get("result") or {}
        for event in result.get("events") or []:
            if "is_own_goal" not in event:
                event["is_own_goal"] = False
                changed = True

        if changed:
            with open(path, "w", encoding="utf-8") as f:
                json.dump(data, f, indent=2)
            touched += 1
            print(f"  Updated: {path.name}")

    print(f"\nDone. {touched} file(s) updated.")


if __name__ == "__main__":
    migrate(Path("data"))
