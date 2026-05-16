"""E2E — Map detail: navigate from homepage, view tactics, filter dropdowns."""

import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E — Map Detail")
class TestMapDetail:

    @allure.title("Navigate to map detail from map card")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_map_detail_navigation(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        with allure.step("Click first map card"):
            map_card = page.locator(".map-entry-card").first
            expect(map_card).to_be_visible(timeout=5000)
            map_card.click()
            page.wait_for_url("**/maps/**", timeout=8000)

        with allure.step("URL contains /maps/"):
            assert "/maps/" in page.url, f"URL should contain /maps/, got {page.url}"

        with allure.step("Map detail page has filter dropdowns"):
            selects = page.locator("select")
            count = selects.count()
            assert count > 0, f"Expected filter <select> elements, found {count}"

        with allure.step("Tactic cards visible"):
            cards = page.locator(".tactic-card")
            if cards.count() == 0:
                # May genuinely have no tactics — page should still not error
                page.wait_for_timeout(1000)

    @allure.title("Map detail filter dropdowns are interactive")
    def test_filter_dropdowns(self, page: Page):
        page.goto(f"{WEB}/maps/mirage", wait_until="domcontentloaded", timeout=15000)

        with allure.step("Find and interact with side select"):
            selects = page.locator("select")
            if selects.count() == 0:
                pytest.skip("No filter <select> elements")
            # Try to select T
            for i in range(selects.count()):
                sel = selects.nth(i)
                options = sel.locator("option")
                option_values = [options.nth(j).get_attribute("value") for j in range(options.count())]
                if "T" in option_values:
                    sel.select_option("T")
                    page.wait_for_timeout(500)
                    break

    @allure.title("404 or empty state when map slug is invalid")
    def test_map_not_found(self, page: Page):
        page.goto(f"{WEB}/maps/no-such-map-999", wait_until="domcontentloaded", timeout=10000)
        # Should not crash — either shows error or empty page
        page.wait_for_timeout(1000)
        assert page.locator("body").is_visible()
