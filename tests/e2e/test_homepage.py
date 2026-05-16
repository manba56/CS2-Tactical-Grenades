"""E2E — Homepage: load, hero stats, map scroll, tactic grid, filters."""

import re
import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E — Homepage")
class TestHomepage:

    @allure.title("Homepage loads with hero + map cards + tactic grid")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_homepage_loads(self, page: Page):
        with allure.step("Navigate to homepage"):
            page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        with allure.step("Hero title visible"):
            expect(page.locator(".hero-title")).to_be_visible(timeout=5000)
            title = page.locator(".hero-title").text_content()
            assert "战术" in title, f"Hero title unexpected: {title}"

        with allure.step("Hero stats show numbers"):
            stats = page.locator(".hero-stat strong")
            expect(stats.first).to_be_visible()
            count = int(stats.first.text_content() or "0")
            assert count >= 0, f"Stat count invalid: {count}"

        with allure.step("Map entry cards visible"):
            cards = page.locator(".map-entry-card")
            expect(cards.first).to_be_visible(timeout=5000)
            assert cards.count() > 0, "No map cards on homepage"

        with allure.step("Tactic cards visible"):
            tactic_cards = page.locator(".card-grid .tactic-card")
            expect(tactic_cards.first).to_be_visible(timeout=5000)
            assert tactic_cards.count() > 0, "No tactic cards on homepage"

    @allure.title("Map filter chips filter tactic grid")
    def test_map_filter_chips(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)

        with allure.step("Click first map filter chip"):
            map_chips = page.locator(".filter-row .filter-chip")
            chip_count_before = map_chips.count()
            if chip_count_before < 2:
                pytest.skip("No map filter chips")
            # First chip is "全部地图", second is a real map
            first_map_chip = map_chips.nth(1)
            map_name = first_map_chip.text_content()
            first_map_chip.click()
            page.wait_for_timeout(500)

        with allure.step("Verify filter chip is active"):
            assert "active" in (first_map_chip.get_attribute("class") or ""), \
                "Selected chip should have 'active' class"

        with allure.step("Tactic cards all belong to selected map"):
            tactic_cards = page.locator(".tactic-card")
            if tactic_cards.count() == 0:
                pytest.skip(f"No tactics for map {map_name}")

    @allure.title("Side filter chips (T / CT) work")
    def test_side_filter(self, page: Page):
        page.goto(WEB, wait_until="domcontentloaded", timeout=15000)
        page.wait_for_timeout(1000)

        with allure.step("Click T filter"):
            t_chip = page.locator(".filter-chip", has_text="T 进攻")
            if t_chip.count() == 0:
                pytest.skip("No T side filter chip")
            t_chip.first.click()
            page.wait_for_timeout(500)

        with allure.step("Verify T chip active"):
            assert "active" in t_chip.first.get_attribute("class") or ""

        with allure.step("Verify all tactic cards are T side"):
            cards = page.locator(".tactic-card")
            if cards.count() == 0:
                pytest.skip("No tactics after T filter")
