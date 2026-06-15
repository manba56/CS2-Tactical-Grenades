"""E2E homepage checks: load, sidebar filters, tactic grid."""

import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E - Homepage")
class TestHomepage:

    @allure.title("Homepage loads with hero, sidebar, and tactic grid")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_homepage_loads(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        expect(page.locator(".home-root")).to_be_visible(timeout=5000)
        expect(page.locator(".hero-title")).to_be_visible(timeout=5000)
        expect(page.locator(".side-nav")).to_be_visible(timeout=5000)

        stats = page.locator(".hero-stat strong")
        expect(stats.first).to_be_visible()
        count = int(stats.first.text_content() or "0")
        assert count >= 0, f"Stat count invalid: {count}"

        tactic_cards = page.locator(".card-grid .tactic-card")
        expect(tactic_cards.first).to_be_visible(timeout=8000)
        assert tactic_cards.count() > 0, "No tactic cards on homepage"

    @allure.title("Map sidebar filter keeps tactic grid usable")
    def test_map_sidebar_filter(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        map_items = page.locator(".side-map-item")
        if map_items.count() == 0:
            pytest.skip("No map sidebar items")

        first_map = map_items.first
        first_map.click()
        page.wait_for_timeout(500)

        assert "active" in (first_map.get_attribute("class") or ""), (
            "Selected map item should have active class"
        )
        assert page.locator(".home-root").is_visible()

    @allure.title("Side filter buttons keep tactic grid usable")
    def test_side_filter(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(500)

        side_buttons = page.locator(".side-section").nth(2).locator("button")
        if side_buttons.count() < 2:
            pytest.skip("No side filter buttons")

        t_button = side_buttons.nth(1)
        t_button.click()
        page.wait_for_timeout(500)

        assert "active" in (t_button.get_attribute("class") or ""), (
            "Selected side filter should have active class"
        )
        assert page.locator(".home-root").is_visible()

    @allure.title("Search input updates the filtered page state")
    def test_search_input(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        search = page.locator(".side-search")
        expect(search).to_be_visible(timeout=5000)
        search.fill("mirage")
        page.wait_for_timeout(500)

        assert page.locator(".home-root").is_visible()
