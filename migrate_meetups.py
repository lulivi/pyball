#!/usr/bin/env python3
"""Migrate meetup files from <uuid>.json to <YYYY-MM-DDTHH:MM>.json.

Usage:
    python migrate_meetups.py [data_dir]   # default: ./data
"""
import json
import sys
from datetime import datetime
from pathlib import Path


def migrate(data_dir: Path) -> None:
    """Rename meetup files to datetime-based names."""
    meetups_dir = data_dir / "meetups"
    if not meetups_dir.exists():
        print(f"ERROR: {meetups_dir} does not exist")
        sys.exit(1)

    files = sorted(meetups_dir.glob("*.json"))
    if not files:
        print("No meetup files found.")
        return

    seen_targets: set[str] = set()
    renames: list[tuple[Path, Path]] = []
    for file in files:
        data = json.loads(file.read_text(encoding="utf-8"))
        dt = datetime.fromisoformat(data["date"])
        new_name = dt.strftime("%Y-%m-%dT%H:%M") + ".json"
        new_path = file.parent / new_name
        if new_name in seen_targets or (new_path.exists() and new_path != file):
            print(f"ERROR: conflict — {new_name} already exists")
            sys.exit(1)
        seen_targets.add(new_name)
        renames.append((file, new_path))

    for old, new in renames:
        print(f"  {old.name}  →  {new.name}")

    confirm = input("\n¿Continuar? [s/N] ")
    if confirm.strip().lower() != "s":
        print("Abortado.")
        sys.exit(0)

    for old, new in renames:
        old.rename(new)

    print(f"\n{len(renames)} archivo(s) migrado(s).")


if __name__ == "__main__":
    migrate(Path(sys.argv[1]) if len(sys.argv) > 1 else Path("data"))
