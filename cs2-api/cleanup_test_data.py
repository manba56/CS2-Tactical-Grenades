"""Delete all test-created data — maps, tactics, lineups, points, users."""

import sqlite3
from pathlib import Path

DB_PATH = Path(__file__).parent / "data" / "db.sqlite"

# Names/patterns that identify test data
TEST_PATTERNS = [
    "test_", "Test ", "reg_", "dup_", "eml_", "wrong_",
    "nouser", "409 ", "Auto-test",
]


def cleanup():
    conn = sqlite3.connect(str(DB_PATH))
    conn.execute("PRAGMA foreign_keys = ON")
    cur = conn.cursor()

    stats: dict[str, int] = {}

    # Build per-table WHERE clauses (tactics/lineups have 'title', maps/points have 'name')
    title_or_slug = " OR ".join(
        f"title LIKE '%{p}%' OR slug LIKE '%{p}%'"
        for p in TEST_PATTERNS
    )
    name_or_key = " OR ".join(
        f"name LIKE '%{p}%' OR key LIKE '%{p}%'"
        for p in TEST_PATTERNS
    )
    map_where = " OR ".join(
        f"name LIKE '%{p}%' OR slug LIKE '%{p}%'"
        for p in TEST_PATTERNS
    )

    # 1. Delete test tactics (title/slug + draft)
    cur.execute(f"DELETE FROM tactics WHERE {title_or_slug} OR status = 'draft'")
    stats["tactics"] = cur.rowcount

    # 2. Delete test lineups (title/slug + draft)
    cur.execute(f"DELETE FROM lineups WHERE {title_or_slug} OR status = 'draft'")
    stats["lineups"] = cur.rowcount

    # 3. Delete test points (name/key)
    cur.execute(f"DELETE FROM points WHERE {name_or_key}")
    stats["points"] = cur.rowcount

    # 4. Delete test maps (name/slug + draft)
    cur.execute(f"DELETE FROM maps WHERE {map_where} OR status = 'draft'")
    stats["maps"] = cur.rowcount

    # 5. Delete test users (keep admin, demo, man)
    cur.execute(
        """DELETE FROM users
           WHERE username LIKE 'test_%'
              OR username LIKE 'reg_%'
              OR username LIKE 'dup_%'
              OR username LIKE 'eml_%'
              OR username LIKE 'wrong_%'
              OR username LIKE 'nouser%'"""
    )
    stats["users"] = cur.rowcount

    # 6. Delete orphaned tokens
    cur.execute(
        """DELETE FROM tokens
           WHERE user_id NOT IN (SELECT id FROM users)"""
    )
    stats["tokens"] = cur.rowcount

    conn.commit()
    conn.close()

    total = sum(stats.values())
    print(f"已删除 {total} 条测试数据:")
    for table, count in stats.items():
        if count:
            print(f"  {table}: {count}")
    if total == 0:
        print("  没有找到测试数据")


if __name__ == "__main__":
    cleanup()
