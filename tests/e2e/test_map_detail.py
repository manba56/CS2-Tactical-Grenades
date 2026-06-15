"""E2E checks for the map-first utility radar page."""

import pytest
import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


@allure.feature("E2E - Map Utility Radar")
class TestMapUtilityRadar:

    @allure.title("/maps opens the radar browser")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_maps_page_loads_current_utility_browser(self, page: Page):
        page.goto(f"{WEB}/maps?map=mirage", wait_until="domcontentloaded", timeout=15000)

        expect(page.locator(".maps-page")).to_be_visible(timeout=8000)
        expect(page.locator(".maps-sidebar")).to_be_visible(timeout=8000)
        expect(page.locator(".radar-panel")).to_be_visible(timeout=8000)
        expect(page.locator(".radar-stage img")).to_be_visible(timeout=8000)

    @allure.title("Clicking a landing marker shows related utility lineups")
    def test_landing_marker_opens_utility_detail(self, page: Page):
        page.goto(f"{WEB}/maps?map=mirage", wait_until="domcontentloaded", timeout=15000)
        expect(page.locator(".radar-stage img")).to_be_visible(timeout=8000)

        markers = page.locator(".landing-marker")
        if markers.count() == 0:
            pytest.skip("No published utility landing markers on Mirage")

        markers.first.click()
        expect(page.locator(".landing-panel-heading")).to_be_visible(timeout=5000)
        expect(page.locator(".lineup-item").first).to_be_visible(timeout=5000)
        assert "land=" in page.url, f"Landing selection should sync to URL, got {page.url}"

        media_cards = page.locator(".lineup-media-card")
        if media_cards.count() > 0:
            expect(media_cards.first.locator("img")).to_be_visible(timeout=5000)

    @allure.title("Utility filters keep the radar page usable")
    def test_map_utility_filters_are_interactive(self, page: Page):
        page.goto(f"{WEB}/maps?map=mirage", wait_until="domcontentloaded", timeout=15000)
        expect(page.locator(".maps-page")).to_be_visible(timeout=8000)

        selects = page.locator(".map-filter-select")
        assert selects.count() >= 3, f"Expected utility/side/difficulty filters, got {selects.count()}"

        utility_select = selects.nth(0)
        options = utility_select.locator("option")
        if options.count() > 1:
            value = options.nth(1).get_attribute("value")
            utility_select.select_option(value)
            page.wait_for_timeout(300)
            assert f"utility={value}" in page.url

    @allure.title("Invalid map query does not white-screen")
    def test_invalid_map_query_falls_back_or_shows_empty_state(self, page: Page):
        page.goto(f"{WEB}/maps?map=no-such-map-999", wait_until="domcontentloaded", timeout=15000)
        expect(page.locator("body")).to_be_visible(timeout=5000)
        assert len(page.locator("body").text_content() or "") > 20
