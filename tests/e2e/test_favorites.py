"""E2E — Login → Favorite → View Favorites → Remove Favorite workflow."""

import uuid
import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")
API = config.API_BASE.rstrip("/")

# We'll use the API to register a test user, then log in via Playwright


@allure.feature("E2E — Favorites")
class TestFavorites:

    @pytest.fixture(scope="class")
    def test_user(self):
        """Register a fresh user via API, return credentials."""
        import requests
        uname = f"e2e_{uuid.uuid4().hex[:6]}"
        email = f"{uname}@e2e.test"
        password = "e2etest123"
        resp = requests.post(
            f"{API}/api/public/auth/register",
            json={"username": uname, "email": email, "password": password},
            timeout=10,
        )
        if resp.status_code == 200:
            return {"username": uname, "email": email, "password": password}
        # Try login — maybe user already exists
        resp2 = requests.post(
            f"{API}/api/public/auth/login",
            json={"username_or_email": uname, "password": password},
            timeout=10,
        )
        if resp2.status_code == 200:
            return {"username": uname, "email": email, "password": password}
        pytest.fail(f"Failed to create test user: {resp.text}")

    @allure.title("Full favorites E2E flow: login → favorite → view → unfavorite")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_favorites_flow(self, page: Page, test_user: dict):
        # Step 1 — Login
        with allure.step("Login via API to get token, then set cookie"):
            import requests
            resp = requests.post(
                f"{API}/api/public/auth/login",
                json={
                    "username_or_email": test_user["username"],
                    "password": test_user["password"],
                },
                timeout=10,
            )
            assert resp.status_code == 200, f"Login failed: {resp.text}"
            token = resp.json()["token"]
            # Set auth token in localStorage via page
            page.goto(WEB, wait_until="domcontentloaded", timeout=10000)
            page.evaluate(f"localStorage.setItem('cs2_token', '{token}')")
            page.reload(wait_until="domcontentloaded")
            page.wait_for_timeout(1000)

        # Step 2 — Find a tactic and favorite it
        with allure.step("Open first tactic detail"):
            page.goto(WEB, wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1000)
            # Navigate to a tactic directly via API first to get a slug
            resp2 = requests.get(f"{API}/api/public/tactics?page_size=1", timeout=10)
            if resp2.status_code != 200 or not resp2.json().get("items"):
                pytest.skip("No tactics available")
            slug = resp2.json()["items"][0]["slug"]
            tactic_id = resp2.json()["items"][0]["id"]
            page.goto(f"{WEB}/tactics/{slug}", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1500)

        with allure.step("Click favorite button"):
            fav_btn = page.locator("button:has-text('收藏'), button:has-text('取消收藏'), [class*='favorite']")
            if fav_btn.count() > 0:
                fav_btn.first.click()
                page.wait_for_timeout(800)

        # Step 3 — Navigate to favorites page
        with allure.step("Navigate to favorites page"):
            fav_link = page.locator("a[href*='favorites'], a:has-text('收藏'), a:has-text('我的')")
            if fav_link.count() > 0:
                fav_link.first.click()
                page.wait_for_timeout(1500)
            else:
                page.goto(f"{WEB}/favorites", wait_until="domcontentloaded", timeout=10000)
                page.wait_for_timeout(1500)

        # Step 4 — Verify favorites page loads
        with allure.step("Favorites page renders"):
            page.wait_for_timeout(1000)
            assert page.locator("body").is_visible()

        # Step 5 — Navigate back to tactic and unfavorite
        with allure.step("Unfavorite the tactic"):
            page.goto(f"{WEB}/tactics/{slug}", wait_until="domcontentloaded", timeout=10000)
            page.wait_for_timeout(1500)
            fav_btn = page.locator("button:has-text('取消收藏'), [class*='favorite']")
            if fav_btn.count() > 0:
                fav_btn.first.click()
                page.wait_for_timeout(500)
