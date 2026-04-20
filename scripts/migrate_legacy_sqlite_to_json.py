#!/usr/bin/env python3
"""Migrate pyball legacy SQLite database (v3) to v4 JSON format.

Usage:
    python scripts/migrate_legacy_sqlite_to_json.py path/to/legacy.db [options]

    Ejemplos:
        # Migración básica con valores por defecto
        python scripts/migrate_legacy_sqlite_to_json.py pyball.db

        # Especificando ubicación y rutas de salida
        python scripts/migrate_legacy_sqlite_to_json.py pyball.db \
            --location "Parque Sur" \
            --players-file data/players.json \
            --meetups-dir data/meetups \
            --telegram-mapping-file data/telegram_mapping.json

Output files (configurable via flags):
    data/players.json           — all players
    data/meetups/<uuid>.json    — one file per match date
    data/telegram_mapping.json  — telegram_id → player UUID

Notes:
    - Player integer IDs are replaced with new UUIDs.
    - assistant_id is set to null for all historical goal events because
      the legacy schema only stored aggregate assist counts, not which scorer
      each assist belonged to.
    - Goal timestamps are reconstructed with 1-minute offsets from the match
      datetime (the legacy schema has no per-goal timestamps).
    - Team names are normalised to "A" / "B" by alphabetical sort of the
      original values found in the database.
"""

import argparse
import json
import sqlite3
from datetime import datetime, timedelta
from pathlib import Path
from uuid import uuid4


def _migrate_players(
    conn: sqlite3.Connection,
    players_file: Path,
    telegram_mapping_file: Path,
) -> dict[int, str]:
    """Write players.json and telegram_mapping.json; return old_id → uuid map."""
    cur = conn.execute("SELECT id, telegram_id, name, main FROM player ORDER BY id")
    rows = cur.fetchall()

    old_id_to_uuid: dict[int, str] = {}
    players = []
    telegram_mapping: dict[str, str] = {}

    for row in rows:
        new_uuid = str(uuid4())
        old_id_to_uuid[row["id"]] = new_uuid
        players.append(
            {
                "id": new_uuid,
                "name": row["name"],
                "group": "regular" if row["main"] else "substitute",
            }
        )
        telegram_mapping[str(row["telegram_id"])] = new_uuid

    players_file.parent.mkdir(parents=True, exist_ok=True)
    with open(players_file, "w", encoding="utf-8") as f:
        json.dump({"players": players}, f, indent=2, ensure_ascii=False)
    print(f"  Jugadores: {len(players)} escritos en {players_file}")

    telegram_mapping_file.parent.mkdir(parents=True, exist_ok=True)
    with open(telegram_mapping_file, "w", encoding="utf-8") as f:
        json.dump(telegram_mapping, f, indent=2)
    print(f"  Telegram mapping: {len(telegram_mapping)} entradas en {telegram_mapping_file}")

    return old_id_to_uuid


def _migrate_meetups(
    conn: sqlite3.Connection,
    meetups_dir: Path,
    old_id_to_uuid: dict[int, str],
    location: str,
) -> None:
    """Write one JSON file per match date found in match_statistic."""
    cur = conn.execute(
        "SELECT date, player_id, team, goals, assists FROM match_statistic ORDER BY date"
    )
    rows = cur.fetchall()

    # Group rows by match date string (the PK already ensures uniqueness per player+date).
    matches: dict[str, list[sqlite3.Row]] = {}
    for row in rows:
        matches.setdefault(row["date"], []).append(row)

    meetups_dir.mkdir(parents=True, exist_ok=True)
    meetup_count = 0

    for date_str, match_rows in matches.items():
        match_dt = datetime.fromisoformat(date_str)
        meetup_uuid = str(uuid4())

        # Collect players per original team name.
        team_players: dict[str, list[str]] = {}
        unknown_players = 0
        for row in match_rows:
            player_uuid = old_id_to_uuid.get(row["player_id"])
            if player_uuid is None:
                print(
                    f"  WARNING: player_id={row['player_id']} no encontrado, "
                    f"omitido del partido {date_str}"
                )
                unknown_players += 1
                continue
            team_players.setdefault(row["team"], [])
            if player_uuid not in team_players[row["team"]]:
                team_players[row["team"]].append(player_uuid)

        if unknown_players and not team_players:
            print(f"  Partido {date_str} sin jugadores reconocidos — omitido.")
            continue

        # Normalise original team names → "A", "B", … by alphabetical sort.
        sorted_orig_names = sorted(team_players.keys())
        letters = ["A", "B", "C", "D"]
        team_name_map = dict(zip(sorted_orig_names, letters))

        all_players = [p for players in team_players.values() for p in players]

        teams_data = [
            {"name": team_name_map[orig], "players": players}
            for orig, players in sorted(team_players.items())
        ]

        # Expand goal counts into individual GoalEvent objects.
        # assistant_id is always null — the legacy schema only stored aggregate counts.
        events = []
        goal_offset = 0
        score: dict[str, int] = {}

        for row in match_rows:
            player_uuid = old_id_to_uuid.get(row["player_id"])
            if player_uuid is None:
                continue
            team_letter = team_name_map[row["team"]]
            for _ in range(row["goals"]):
                events.append(
                    {
                        "scorer_id": player_uuid,
                        "assistant_id": None,
                        "team": team_letter,
                        "timestamp": (match_dt + timedelta(minutes=goal_offset)).isoformat(),
                    }
                )
                score[team_letter] = score.get(team_letter, 0) + 1
                goal_offset += 1

        meetup_data = {
            "id": meetup_uuid,
            "date": match_dt.isoformat(),
            "location": location,
            "players": all_players,
            "teams": teams_data,
            "result": {
                "score_a": score.get("A", 0),
                "score_b": score.get("B", 0),
                "events": events,
            },
        }

        out_path = meetups_dir / f"{meetup_uuid}.json"
        with open(out_path, "w", encoding="utf-8") as f:
            json.dump(meetup_data, f, indent=2, ensure_ascii=False)
        meetup_count += 1

    print(f"  Meetups: {meetup_count} escritos en {meetups_dir}")


def _generate_legacy_stats(
    conn: sqlite3.Connection,
    old_id_to_uuid: dict[int, str],
    output_dir: Path,
) -> None:
    """Generate legacy_stats.json with aggregate goals/assists/matches per player."""
    cur = conn.execute(
        "SELECT player_id, team, goals, assists FROM match_statistic ORDER BY player_id"
    )
    rows = cur.fetchall()

    legacy: dict[str, dict[str, int]] = {"players": {}}

    for row in rows:
        player_uuid = old_id_to_uuid.get(row["player_id"])
        if player_uuid is None:
            continue

        if player_uuid not in legacy["players"]:
            legacy["players"][player_uuid] = {"goals": 0, "assists": 0, "matches": 0}

        legacy["players"][player_uuid]["goals"] += row["goals"]
        legacy["players"][player_uuid]["assists"] += row["assists"]
        legacy["players"][player_uuid]["matches"] += 1

    legacy_file = output_dir / "legacy_stats.json"
    with open(legacy_file, "w", encoding="utf-8") as f:
        json.dump(legacy, f, indent=2, ensure_ascii=False)

    print(f"  Legacy stats: {len(legacy['players'])} players written to {legacy_file}")


def main() -> None:
    """Parse arguments and run the migration."""
    parser = argparse.ArgumentParser(
        description="Migra la base de datos SQLite de pyball v3 al formato JSON de v4."
    )
    parser.add_argument("db", type=Path, help="Ruta al fichero SQLite legado")
    parser.add_argument("--output-dir", type=Path, help="Output directory (e.g. data/)")
    parser.add_argument(
        "--players-file",
        default="players.json",
        help="Destino para players.json (default: players.json)",
    )
    parser.add_argument(
        "--meetups-dir",
        default="meetups",
        help="Directorio destino para los JSON de meetups (default: meetups)",
    )
    parser.add_argument(
        "--telegram-mapping-file",
        default="bot/telegram-uuid.json",
        help="Destino para telegram-uuid.json (default: bot/telegram-uuid.json)",
    )
    parser.add_argument(
        "--location",
        default="Parque Central",
        help="Ubicación a usar en todos los meetups migrados (default: Parque Central)",
    )
    args = parser.parse_args()

    if not args.db.exists():
        parser.error(f"No se encuentra el fichero de base de datos: {args.db}")

    print(f"Migrando {args.db} …")
    conn = sqlite3.connect(args.db)
    conn.row_factory = sqlite3.Row

    args.output_dir.mkdir(parents=True, exist_ok=True)
    players_file_path = args.output_dir.joinpath(args.players_file)
    telegram_mapping_file_path = args.output_dir.joinpath(args.telegram_mapping_file)
    meetups_dir_path = args.output_dir.joinpath(args.meetups_dir)

    try:
        old_id_to_uuid = _migrate_players(conn, players_file_path, telegram_mapping_file_path)
        _migrate_meetups(conn, meetups_dir_path, old_id_to_uuid, args.location)
        _generate_legacy_stats(conn, old_id_to_uuid, args.output_dir)
    finally:
        conn.close()

    print("Migración completada.")


if __name__ == "__main__":
    main()
