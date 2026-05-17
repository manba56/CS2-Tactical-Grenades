"""Root conftest — shared fixtures for API + E2E tests."""

from __future__ import annotations

import uuid

import pytest
import allure

import config


def _unique_username() -> str:
    return f"test_{uuid.uuid4().hex[:8]}"


# ═══════════════════════════════════════════════════════════
# API clients
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def anon_client():
    """Unauthenticated HTTP client."""
    from utils.api_client import Client
    return Client()


@pytest.fixture(scope="session")
def admin_client():
    """Authenticated admin client (session-scoped, shared)."""
    from utils.api_client import Client
    status, body = Client().admin_login(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
    if status != 200:
        pytest.fail(f"Admin login failed: {body}")
    token = body["token"]
    return Client(token=token)


@pytest.fixture(scope="session")
def player_client():
    """Session-scoped player client — single registration for all tests."""
    from utils.api_client import Client
    username = _unique_username()
    email = f"{username}@test.com"
    status, body = Client().register(username, email, config.PLAYER_PASSWORD)
    if status != 200:
        pytest.fail(f"Player register failed: {body}")
    token = body["token"]
    return Client(token=token)


# ═══════════════════════════════════════════════════════════
# Shared test data helpers
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session")
def first_map_slug(anon_client):
    """Get the slug of the first published map."""
    status, maps = anon_client.list_maps()
    if status == 200 and maps:
        return maps[0]["slug"]
    pytest.skip("No published maps available")


@pytest.fixture(scope="session")
def first_tactic_slug(anon_client):
    """Get the slug of the first published tactic."""
    status, data = anon_client.list_tactics({"page_size": 1})
    if status == 200 and data.get("items"):
        return data["items"][0]["slug"]
    pytest.skip("No published tactics available")


# ═══════════════════════════════════════════════════════════
# ZenTao hook — auto-report failures
# ═══════════════════════════════════════════════════════════

@pytest.hookimpl(tryfirst=True, hookwrapper=True)
def pytest_runtest_makereport(item, call):
    outcome = yield
    report = outcome.get_result()
    if report.when == "call" and report.failed:
        test_name = item.nodeid
        detail = f"Phase: {report.when}\n"
        if report.longrepr:
            detail += str(report.longrepr)[:2000]
        try:
            from utils.zentao import report_on_failure
            report_on_failure(test_name, detail)
        except Exception:
            pass  # never let ZenTao break the test run


# ═══════════════════════════════════════════════════════════
# Test data cleanup
# ═══════════════════════════════════════════════════════════

@pytest.fixture(scope="session", autouse=True)
def cleanup_test_data():
    """Delete test-created entities in reverse dependency order.

    Best-effort: silently skipped when API is not available or
    admin credentials are wrong (unit tests, local dev without server).
    """
    yield  # Wait for all tests to complete

    from utils.data_cleanup import get_tracker
    tracker = get_tracker()
    cleanup_ids = tracker.get_cleanup_ids()

    if not any(cleanup_ids.values()):
        return

    # Try to get admin token for cleanup — skip if API is down
    try:
        from utils.api_client import Client
        import config
        status, body = Client().admin_login(config.ADMIN_USERNAME, config.ADMIN_PASSWORD)
        if status != 200:
            return  # Auth failed, skip cleanup
        admin_client = Client(token=body["token"])
    except Exception:
        return  # API not reachable, skip cleanup

    for entity_type in tracker.cleanup_order:
        ids = cleanup_ids.get(entity_type, set())
        for entity_id in sorted(ids):
            try:
                if entity_type == "tactic":
                    admin_client.admin_archive_tactic(entity_id)
                elif entity_type == "lineup":
                    admin_client.admin_archive_lineup(entity_id)
                    admin_client.admin_delete_lineup(entity_id)
            except Exception:
                pass  # Cleanup is best-effort

    tracker.clear()
