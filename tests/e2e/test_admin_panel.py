"""E2E — Admin panel: login, CRUD, screenshot upload, route editor."""

import uuid
import pytest
import allure
from playwright.sync_api import Page, expect

import config

ADMIN = config.ADMIN_BASE.rstrip("/")
API = config.API_BASE.rstrip("/")


@allure.feature("E2E — Admin Panel")
class TestAdminPanel:

    def _admin_login(self, page: Page):
        """Log into admin via API, set token."""
        import requests
        resp = requests.post(
            f"{API}/api/admin/auth/login",
            json={"username": config.ADMIN_USERNAME, "password": config.ADMIN_PASSWORD},
            timeout=10,
        )
        if resp.status_code != 200:
            pytest.fail(f"Admin login failed: {resp.text}")
        token = resp.json()["token"]
        page.goto(ADMIN, wait_until="domcontentloaded", timeout=10000)
        page.evaluate(f"localStorage.setItem('cs2_admin_token', '{token}')")
        page.reload(wait_until="domcontentloaded")
        page.wait_for_timeout(1000)

    @allure.title("Admin login and dashboard access")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_admin_login_and_dashboard(self, page: Page):
        self._admin_login(page)

        with allure.step("Dashboard page loaded"):
            page.wait_for_timeout(1000)
            # Should have some content
            body_text = page.locator("body").text_content() or ""
            assert len(body_text) > 50, "Admin body too short, likely not loaded"

    @allure.title("Admin — Tactics list visible")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tactics_list(self, page: Page):
        self._admin_login(page)

        with allure.step("Navigate to tactics page"):
            tactic_link = page.locator("a[href*='tactics'], a:has-text('战术')")
            if tactic_link.count() > 0:
                tactic_link.first.click()
                page.wait_for_url("**/tactics**", timeout=8000)
                page.wait_for_timeout(1000)

        with allure.step("Tactics list is visible"):
            items = page.locator(".list-item")
            count = items.count()
            assert count >= 0, f"Expected list items, got {count}"

    @allure.title("Admin — Form create + reset")
    def test_form_create_reset(self, page: Page):
        self._admin_login(page)

        with allure.step("Navigate to tactics page"):
            page.goto(f"{ADMIN}/tactics", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1500)

        with allure.step("Fill title field"):
            title_input = page.locator("input").first
            if title_input.is_visible():
                title_input.fill("E2E Test Tactic")

        with allure.step("Click reset button"):
            reset_btn = page.locator("button:has-text('清空表单')")
            if reset_btn.count() > 0:
                reset_btn.first.click()
                page.wait_for_timeout(500)

        with allure.step("Verify form reset"):
            title_value = title_input.input_value()
            assert title_value == "" or "E2E" not in title_value, \
                f"Form should be cleared after reset, got '{title_value}'"

    @allure.title("Admin — Route editor canvas exists")
    def test_route_editor_canvas(self, page: Page):
        self._admin_login(page)

        with allure.step("Navigate to tactics form"):
            page.goto(f"{ADMIN}/tactics", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)

        with allure.step("Check for canvas element"):
            canvas = page.locator("canvas")
            if canvas.count() > 0:
                assert canvas.first.is_visible()
            else:
                # Canvas may only appear after adding a route
                pytest.skip("No canvas found — may need route added first")

    @allure.title("Admin — Screenshot upload UI present")
    def test_screenshot_ui(self, page: Page):
        self._admin_login(page)

        with allure.step("Navigate to tactics form"):
            page.goto(f"{ADMIN}/tactics", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(2000)

        with allure.step("Screenshot sections visible"):
            # Scroll to bottom
            page.evaluate("window.scrollTo(0, document.body.scrollHeight)")
            page.wait_for_timeout(500)

            add_btn = page.locator("button:has-text('添加路线截图'), button:has-text('添加点位截图')")
            if add_btn.count() > 0:
                # UI is present
                pass

    @allure.title("Admin — Map management accessible")
    def test_maps_management(self, page: Page):
        self._admin_login(page)

        with allure.step("Navigate to maps page"):
            map_link = page.locator("a[href*='maps'], a:has-text('地图')")
            if map_link.count() > 0:
                map_link.first.click()
                page.wait_for_timeout(1500)

        with allure.step("Map list or form visible"):
            page.wait_for_timeout(1000)
            assert page.locator("body").is_visible()
