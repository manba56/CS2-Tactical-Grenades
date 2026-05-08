from __future__ import annotations

import copy
import json
from pathlib import Path
from threading import RLock
from typing import Any

from .seed import build_seed_state


class JsonStore:
    def __init__(self, path: Path) -> None:
        self.path = path
        self.lock = RLock()
        self.path.parent.mkdir(parents=True, exist_ok=True)
        if not self.path.exists():
            self.write_state(build_seed_state())
            return
        try:
            self.read_state()
        except json.JSONDecodeError:
            self.write_state(build_seed_state())

    def read_state(self) -> dict[str, Any]:
        with self.lock:
            with self.path.open("r", encoding="utf-8") as file:
                return json.load(file)

    def write_state(self, state: dict[str, Any]) -> None:
        with self.lock:
            with self.path.open("w", encoding="utf-8") as file:
                json.dump(state, file, ensure_ascii=False, indent=2)

    def snapshot(self) -> dict[str, Any]:
        return copy.deepcopy(self.read_state())

    def mutate(self, callback):
        state = self.read_state()
        result = callback(state)
        self.write_state(state)
        return result
