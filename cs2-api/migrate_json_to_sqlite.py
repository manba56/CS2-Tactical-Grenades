"""One-time migration: copy data from db.json to db.sqlite.

Usage:
    cd cs2-api
    python migrate_json_to_sqlite.py

Keeps the original db.json as db.json.backup.
"""

from __future__ import annotations

import json
import shutil
import sys
from pathlib import Path

from app.database import Database

DATA_DIR = Path(__file__).resolve().parent / "data"
JSON_PATH = DATA_DIR / "db.json"
SQLITE_PATH = DATA_DIR / "db.sqlite"
BACKUP_PATH = DATA_DIR / "db.json.backup"


def migrate() -> None:
    if not JSON_PATH.exists():
        print(f"ERROR: {JSON_PATH} not found — nothing to migrate.")
        sys.exit(1)

    # Backup original
    shutil.copy2(JSON_PATH, BACKUP_PATH)
    print(f"Backed up to {BACKUP_PATH}")

    # Load JSON data
    with JSON_PATH.open("r", encoding="utf-8") as f:
        state = json.load(f)

    count = sum(len(state.get(k, [])) for k in ["maps", "points", "lineups", "tactics", "users", "assets"])
    print(f"Migrating {count} records across {len(state) - 1} tables...")

    # Delete existing SQLite if present
    if SQLITE_PATH.exists():
        SQLITE_PATH.unlink()
        print(f"Removed existing {SQLITE_PATH}")

    # Write to SQLite
    db = Database(SQLITE_PATH)
    db.save_state(state)
    print(f"Migration complete: {SQLITE_PATH}")
    print(f"Original kept at: {JSON_PATH}")
    print(f"Backup at: {BACKUP_PATH}")


if __name__ == "__main__":
    migrate()
