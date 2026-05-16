"""Health endpoint — simplest smoke test."""

import allure

from utils.allure_helper import assert_status, attach_body


@allure.feature("Health")
class TestHealth:

    @allure.story("GET /api/health")
    @allure.title("Health returns status ok")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_health_ok(self, anon_client):
        status, body = anon_client.health()
        attach_body(body)
        assert_status(status, 200)
        assert body.get("status") == "ok", f"status={body.get('status')}"
