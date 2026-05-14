from __future__ import annotations

import copy
from pathlib import Path
from threading import RLock
from typing import Any

from .database import Database


class SqliteStore:
    """Thread-safe SQLite-backed store with the same interface as JsonStore.

    Uses snapshot() for reads and mutate(callback) for writes —
    identical API to the old JsonStore so main.py needs no changes.
    """

    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = RLock()
        self._db = Database(path)

    def snapshot(self) -> dict[str, Any]:
        with self.lock:
            return copy.deepcopy(self._db.load_state())

    def mutate(self, callback):
        with self.lock:
            state = self._db.load_state()
            result = callback(state)
            self._db.save_state(state)
            return result

    def write_state(self, state: dict[str, Any]) -> None:
        with self.lock:
            self._db.save_state(state)
