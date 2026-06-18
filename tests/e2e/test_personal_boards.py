"""E2E checks for the personal tactic board workflow."""

import json

import allure
from playwright.sync_api import Page, expect

import config

WEB = config.WEB_BASE.rstrip("/")


def _prepare_board_page(page: Page):
    user = {"id": 1001, "username": "board_e2e", "email": "board_e2e@test.com", "role": "player"}
    page.add_init_script(
        f"""localStorage.setItem('cs2-web-token', 'e2e-token');
localStorage.setItem('cs2-web-user', {json.dumps(json.dumps(user))});""",
    )
    page.route(
        "**/api/public/maps",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([
                {
                    "id": 5,
                    "name": "Mirage",
                    "slug": "mirage",
                    "overview": "Mid control and A execute practice.",
                    "cover_url": "/static/assets/maps/icons/de_mirage.png",
                    "layout_url": "/static/assets/maps/mirage-layout.svg",
                    "callout_color": "#409eff",
                    "order": 5,
                    "status": "published",
                    "active_pool": True,
                    "tactic_count": 1,
                }
            ]),
        ),
    )
    page.route(
        "**/api/public/me/boards",
        lambda route: route.fulfill(
            status=200,
            content_type="application/json",
            body=json.dumps([]) if route.request.method == "GET" else json.dumps({
                "id": 77,
                "user_id": 1001,
                "map_id": 5,
                "title": "E2E Mirage A execute",
                "side": "T",
                "plan_type": "exec",
                "summary": "Window smoke, connector smoke, then split A.",
                "markers": [
                    {"x": 18, "y": 82, "label": "P1", "role": "player", "side": "T"},
                    {"x": 62, "y": 48, "label": "Entry flash", "role": "flash", "side": "BOTH"},
                ],
                "routes": [],
                "created_at": "2026-06-18T00:00:00Z",
                "updated_at": "2026-06-18T00:00:00Z",
                "map": {"id": 5, "name": "Mirage", "slug": "mirage"},
                "map_radar_url": "/static/assets/maps/radars/mirage-radar.png",
                "map_layout_url": "/static/assets/maps/mirage-layout.svg",
            }),
        ),
    )


@allure.feature("E2E - Personal Tactic Board")
class TestPersonalBoardsE2E:

    @allure.title("Player can create a tactic board from the radar")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_personal_board(self, page: Page):
        _prepare_board_page(page)
        page.goto(f"{WEB}/boards", wait_until="domcontentloaded", timeout=15000)

        expect(page.get_by_test_id("board-title")).to_be_visible(timeout=8000)
        expect(page.get_by_test_id("board-map")).to_have_value("5", timeout=8000)
        page.get_by_test_id("board-title").fill("E2E Mirage A execute")
        page.get_by_test_id("marker-role").select_option("flash")
        page.get_by_test_id("marker-label").fill("Entry flash")

        radar = page.get_by_test_id("board-radar")
        expect(radar).to_be_visible(timeout=8000)
        box = radar.bounding_box()
        assert box, "Board radar should have a bounding box"
        page.mouse.click(box["x"] + box["width"] * 0.62, box["y"] + box["height"] * 0.48)

        page.get_by_test_id("save-board").click()
        expect(page.get_by_text("Board created.", exact=True)).to_be_visible(timeout=8000)
        expect(page.get_by_text("E2E Mirage A execute")).to_be_visible(timeout=8000)
