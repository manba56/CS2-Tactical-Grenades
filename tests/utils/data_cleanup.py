"""Test data tracker — records test-created entities for cleanup after run."""

from __future__ import annotations

from collections import defaultdict


class TestDataTracker:
    """Singleton tracker for test data lifecycle management.

    Each test that creates persistent entities registers them so a
    session-scoped cleanup fixture can delete them in reverse
    dependency order (tactics → lineups → points → maps).
    """

    _instance: TestDataTracker | None = None

    def __new__(cls) -> TestDataTracker:
        if cls._instance is None:
            cls._instance = super().__new__(cls)
            cls._instance._ids: dict[str, set[int]] = defaultdict(set)
        return cls._instance

    def register_created(self, entity_type: str, entity_id: int) -> None:
        """Track a test-created entity for later cleanup.

        entity_type one of: 'tactic', 'lineup', 'point', 'map'
        """
        self._ids[entity_type].add(entity_id)

    def get_cleanup_ids(self) -> dict[str, set[int]]:
        """Return all tracked IDs grouped by type."""
        return dict(self._ids)

    def clear(self) -> None:
        """Reset all tracked data."""
        self._ids.clear()

    @property
    def cleanup_order(self) -> list[str]:
        """Deletion order: tactics first (may ref lineups), then lineups, points, maps."""
        return ["tactic", "lineup", "point", "map"]


# Convenience accessor
def get_tracker() -> TestDataTracker:
    return TestDataTracker()
