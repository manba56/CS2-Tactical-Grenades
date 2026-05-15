"""SQLite-based storage for CS2 Tactics Suite.

Replaces the single JSON file with a proper SQLite database while
keeping the same dict-of-lists state shape so main.py needs no changes.
"""

from __future__ import annotations

import json
import sqlite3
from pathlib import Path
from typing import Any

from .seed import build_seed_state

SCHEMA_SQL = """
CREATE TABLE IF NOT EXISTS maps (
    id INTEGER PRIMARY KEY,
    name TEXT, slug TEXT, overview TEXT,
    cover_url TEXT, layout_url TEXT,
    callout_color TEXT, "order" INTEGER,
    status TEXT, active_pool INTEGER
);

CREATE TABLE IF NOT EXISTS points (
    id INTEGER PRIMARY KEY,
    map_id INTEGER, name TEXT, key TEXT,
    x REAL, y REAL, side TEXT, point_type TEXT,
    tags TEXT
);

CREATE TABLE IF NOT EXISTS lineups (
    id INTEGER PRIMARY KEY,
    map_id INTEGER, title TEXT, slug TEXT,
    side TEXT, utility_type TEXT,
    start_point_id INTEGER, aim_point_id INTEGER, land_point_id INTEGER,
    purpose TEXT, difficulty TEXT, summary TEXT,
    steps TEXT, media TEXT, status TEXT
);

CREATE TABLE IF NOT EXISTS tactics (
    id INTEGER PRIMARY KEY,
    map_id INTEGER, title TEXT, slug TEXT,
    side TEXT, goal TEXT, phase TEXT, difficulty TEXT,
    players INTEGER, summary TEXT, note TEXT,
    tags TEXT, cover_url TEXT, featured INTEGER, status TEXT,
    created_at TEXT,
    step_items TEXT, routes TEXT, screenshots TEXT
);

CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY,
    username TEXT, email TEXT, password_hash TEXT, role TEXT,
    favorite_ids TEXT, recent_tactic_ids TEXT
);

CREATE TABLE IF NOT EXISTS assets (
    id INTEGER PRIMARY KEY,
    filename TEXT, original_name TEXT, url TEXT,
    width INTEGER, height INTEGER, type TEXT
);

CREATE TABLE IF NOT EXISTS tokens (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER NOT NULL,
    token_hash TEXT NOT NULL UNIQUE,
    created_at TEXT NOT NULL,
    expires_at TEXT
);

CREATE TABLE IF NOT EXISTS login_log (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    user_id INTEGER,
    username TEXT,
    ip TEXT,
    success INTEGER,
    created_at TEXT NOT NULL
);

CREATE TABLE IF NOT EXISTS counters (
    table_name TEXT PRIMARY KEY,
    next_id INTEGER
);
"""

# Columns for each table (excluding id — it's auto-generated).
# JSON columns are stored as TEXT and serialized/deserialized automatically.
TABLE_COLUMNS: dict[str, list[str]] = {
    "maps":      ["name", "slug", "overview", "cover_url", "layout_url",
                  "callout_color", "order", "status", "active_pool"],
    "points":    ["map_id", "name", "key", "x", "y", "side", "point_type", "tags"],
    "lineups":   ["map_id", "title", "slug", "side", "utility_type",
                  "start_point_id", "aim_point_id", "land_point_id",
                  "purpose", "difficulty", "summary", "steps", "media", "status"],
    "tactics":   ["map_id", "title", "slug", "side", "goal", "phase", "difficulty",
                  "players", "summary", "note", "tags", "cover_url", "featured",
                  "status", "created_at", "step_items", "routes", "screenshots"],
    "users":     ["username", "email", "password_hash", "role",
                  "favorite_ids", "recent_tactic_ids"],
    "assets":    ["filename", "original_name", "url", "width", "height", "type"],
    "tokens":    ["user_id", "token_hash", "created_at", "expires_at"],
    "login_log": ["user_id", "username", "ip", "success", "created_at"],
}

# Columns that store JSON arrays/objects and need json.loads / json.dumps
JSON_COLUMNS: dict[str, set[str]] = {
    "points":    {"tags"},
    "lineups":   {"steps", "media"},
    "tactics":   {"tags", "step_items", "routes", "screenshots"},
    "users":     {"favorite_ids", "recent_tactic_ids"},
}


def _deserialize_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Convert JSON text columns back to Python objects."""
    json_cols = JSON_COLUMNS.get(table, set())
    for col in json_cols:
        if col in row and row[col] is not None:
            try:
                row[col] = json.loads(row[col])
            except (json.JSONDecodeError, TypeError):
                pass
    # Convert SQLite integer 0/1 to Python bool for boolean fields
    if table == "maps":
        row["active_pool"] = bool(row.get("active_pool", True))
    if table == "tactics":
        row["featured"] = bool(row.get("featured", False))
    return row


def _serialize_row(table: str, row: dict[str, Any]) -> dict[str, Any]:
    """Convert Python objects to JSON text for storage."""
    row = dict(row)  # shallow copy
    json_cols = JSON_COLUMNS.get(table, set())
    for col in json_cols:
        if col in row and row[col] is not None and not isinstance(row[col], str):
            row[col] = json.dumps(row[col], ensure_ascii=False)
    # Convert bool to int for SQLite
    if table == "maps" and "active_pool" in row:
        row["active_pool"] = int(row["active_pool"])
    if table == "tactics" and "featured" in row:
        row["featured"] = int(row["featured"])
    return row


def _columns_for_table(table: str) -> list[str]:
    return TABLE_COLUMNS.get(table, [])


def _quote_col(name: str) -> str:
    """Quote column names that are SQLite reserved words."""
    return f'"{name}"'


def _quoted_columns(table: str) -> list[str]:
    return [_quote_col(c) for c in _columns_for_table(table)]


class Database:
    """Manages the SQLite connection and provides load/save operations."""

    def __init__(self, db_path: Path) -> None:
        self.db_path = db_path
        self.db_path.parent.mkdir(parents=True, exist_ok=True)

        conn = self._connect()
        try:
            conn.executescript(SCHEMA_SQL)
            conn.commit()
            # Check if we need to seed (empty database)
            cur = conn.execute("SELECT COUNT(*) FROM counters")
            if cur.fetchone()[0] == 0:
                self._seed(conn)
                conn.commit()
        finally:
            conn.close()

    def _connect(self) -> sqlite3.Connection:
        conn = sqlite3.connect(str(self.db_path))
        conn.row_factory = sqlite3.Row
        conn.execute("PRAGMA journal_mode=WAL")
        conn.execute("PRAGMA foreign_keys=ON")
        return conn

    def _seed(self, conn: sqlite3.Connection) -> None:
        """Populate the database with initial seed data."""
        state = build_seed_state()
        self._write_state(conn, state)

    # ── Read ──────────────────────────────────────────────────
    def load_state(self) -> dict[str, Any]:
        """Return the full state as a dict-of-lists (identical to old JSON shape)."""
        conn = self._connect()
        try:
            return self._load_state(conn)
        finally:
            conn.close()

    def _load_state(self, conn: sqlite3.Connection) -> dict[str, Any]:
        state: dict[str, Any] = {}
        for table in TABLE_COLUMNS:
            rows = conn.execute(f"SELECT * FROM {table} ORDER BY id").fetchall()
            state[table] = [_deserialize_row(table, dict(r)) for r in rows]

        # Load counters
        counters = {}
        for r in conn.execute("SELECT * FROM counters").fetchall():
            counters[r["table_name"]] = r["next_id"]
        state["counters"] = counters
        return state

    # ── Write ─────────────────────────────────────────────────
    def save_state(self, state: dict[str, Any]) -> None:
        """Persist the full state dict to SQLite."""
        conn = self._connect()
        try:
            self._write_state(conn, state)
            conn.commit()
        except Exception:
            conn.rollback()
            raise
        finally:
            conn.close()

    def _write_state(self, conn: sqlite3.Connection, state: dict[str, Any]) -> None:
        for table in TABLE_COLUMNS:
            items = state.get(table, [])
            columns = _columns_for_table(table)
            qcols = _quoted_columns(table)

            # Delete all existing + re-insert. For small datasets this is
            # simpler and faster than diff-based upsert.
            conn.execute(f"DELETE FROM {table}")

            for item in items:
                row = _serialize_row(table, item)
                col_names = ['"id"'] + qcols
                values = [item.get("id")] + [row.get(c) for c in columns]
                placeholders = ", ".join(["?"] * len(col_names))
                conn.execute(
                    f"INSERT INTO {table} ({', '.join(col_names)}) VALUES ({placeholders})",
                    values,
                )

        # Save counters
        conn.execute("DELETE FROM counters")
        counters = state.get("counters", {})
        for key, value in counters.items():
            conn.execute(
                "INSERT INTO counters (table_name, next_id) VALUES (?, ?)",
                (key, value),
            )
