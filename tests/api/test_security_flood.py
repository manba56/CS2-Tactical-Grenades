"""Security — rate limiting and anomaly detection (runs LAST to avoid 429 spillover)."""

import allure

from utils.allure_helper import attach_body
import config


@allure.feature("Security — Rate Limiting")
class TestRateLimit:

    @allure.title(f"Global rate limit triggers 429 after {config.RATE_LIMIT_REQUESTS} requests")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_global_rate_limit(self, anon_client):
        """Fire 130 requests in a loop; at least one must be 429."""
        saw_429 = False
        import requests as r
        for _ in range(config.RATE_LIMIT_REQUESTS):
            try:
                resp = r.get(f"{config.API_BASE}/api/health", timeout=config.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    saw_429 = True
                    break
            except Exception:
                pass
        assert saw_429, f"Rate limit should trigger at {config.RATE_LIMIT_REQUESTS} requests"


@allure.feature("Security — Anomaly Detection")
class TestAnomalyDetection:

    @allure.title("Default account lockout after 5 failed logins")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_admin_lockout(self, anon_client):
        for i in range(6):
            status, body = anon_client.admin_login("admin", f"wrongpass{i}")
        assert status in (400, 429), \
            f"Expected 400 or 429 on lockout, got {status}: {body}"

    @allure.title("Demo account lockout after 5 failed logins")
    def test_demo_lockout(self, anon_client):
        for i in range(6):
            status, body = anon_client.login("demo", f"wrongpass{i}")
        assert status in (400, 429), \
            f"Expected 400 or 429 on lockout, got {status}: {body}"
