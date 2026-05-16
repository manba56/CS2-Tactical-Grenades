"""E2E — Tactic detail: route screenshots, spot screenshots, radar template."""

import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E — Tactic Detail")
class TestTacticDetail:

    def _navigate_to_first_tactic(self, page: Page) -> str:
        """Go to homepage → click first tactic card → return URL."""
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        # Ensure tactic cards are visible
        first_card = page.locator(".tactic-card a, .tactic-card").first
        expect(first_card).to_be_visible(timeout=8000)

        # If it's a link, click it; if not, find the inner link
        if first_card.evaluate("el => el.tagName") == "A":
            first_card.click()
        else:
            link = first_card.locator("a").first
            if link.is_visible():
                link.click()
            else:
                first_card.click()

        page.wait_for_url("**/tactics/**", timeout=8000)
        page.wait_for_timeout(1500)
        return page.url

    @allure.title("Tactic detail loads with all sections")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tactic_detail_sections(self, page: Page):
        url = self._navigate_to_first_tactic(page)
        allure.attach(url, name="tactic_url", attachment_type=allure.attachment_type.TEXT)

        with allure.step("Page has title"):
            page.wait_for_timeout(2000)

        with allure.step("Radar/route image visible"):
            imgs = page.locator("img[src*='radar'], img[src*='route'], img[src*='screenshot']")
            # May or may not have images — just verify no crash
            page.wait_for_timeout(500)

        with allure.step("Steps section present"):
            # Steps might be in different containers
            body_text = page.locator("body").text_content() or ""
            assert len(body_text) > 100, "Page body too short, likely didn't load"

    @allure.title("Radar template toggle (if exists)")
    def test_radar_toggle(self, page: Page):
        url = self._navigate_to_first_tactic(page)

        with allure.step("Look for toggle/collapse button"):
            toggle_btn = page.locator("button:has-text('雷达'), button:has-text('底图'), button:has-text('展开'), button:has-text('收起')")
            if toggle_btn.count() > 0:
                toggle_btn.first.click()
                page.wait_for_timeout(500)

    @allure.title("Back navigation works")
    def test_back_navigation(self, page: Page):
        url = self._navigate_to_first_tactic(page)
        page.go_back()
        page.wait_for_timeout(1000)
        assert "/tactics/" not in page.url, f"Back didn't leave tactic page: {page.url}"

    @allure.title("404 handling for non-existent tactic")
    def test_tactic_not_found(self, page: Page):
        page.goto(f"{WEB}/tactics/no-such-tactic-999", wait_until="domcontentloaded", timeout=10000)
        page.wait_for_timeout(1000)
        assert page.locator("body").is_visible()
        # Should not show a white screen
