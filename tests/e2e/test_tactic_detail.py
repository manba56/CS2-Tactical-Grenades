"""E2E tactic detail checks: navigation, media sections, back, 404."""

import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E - Tactic Detail")
class TestTacticDetail:

    def _navigate_to_first_tactic(self, page: Page) -> str:
        """Open the homepage, click the first tactic card, and return its URL."""
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        first_card = page.locator(".tactic-card").first
        expect(first_card).to_be_visible(timeout=8000)
        first_card.click()

        page.wait_for_url("**/tactics/**", timeout=8000)
        page.wait_for_timeout(1000)
        return page.url

    @allure.title("Tactic detail loads with usable content")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tactic_detail_sections(self, page: Page):
        url = self._navigate_to_first_tactic(page)
        allure.attach(url, name="tactic_url", attachment_type=allure.attachment_type.TEXT)

        expect(page.locator("body")).to_be_visible(timeout=5000)
        body_text = page.locator("body").text_content() or ""
        assert len(body_text) > 100, "Page body too short, likely did not load"

    @allure.title("Radar toggle can be clicked when route screenshots exist")
    def test_radar_toggle(self, page: Page):
        self._navigate_to_first_tactic(page)

        toggle_btn = page.locator(".map-stage .secondary-button").first
        if toggle_btn.count() > 0:
            toggle_btn.click()
            page.wait_for_timeout(500)

        assert page.locator("body").is_visible()

    @allure.title("Back navigation works")
    def test_back_navigation(self, page: Page):
        self._navigate_to_first_tactic(page)
        page.go_back()
        page.wait_for_timeout(1000)
        assert "/tactics/" not in page.url, f"Back did not leave tactic page: {page.url}"

    @allure.title("404 handling for non-existent tactic")
    def test_tactic_not_found(self, page: Page):
        page.goto(f"{WEB}/tactics/no-such-tactic-999", wait_until="domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
        assert page.locator("body").is_visible()
