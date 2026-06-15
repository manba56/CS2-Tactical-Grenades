"""Public API endpoints: home, maps, tactics, tactic detail."""

import pytest
import allure

from utils.allure_helper import (
    assert_status,
    assert_not_empty,
    assert_has_key,
    attach_body,
)


@allure.feature("Public Home")
class TestHome:

    @allure.story("GET /api/public/home")
    @allure.title("Home returns all required sections")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_home_structure(self, anon_client):
        status, body = anon_client.home()
        attach_body(body)
        assert_status(status, 200)
        for key in ("featured_maps", "featured_tactics", "latest_tactics", "utility_quick_links"):
            assert_has_key(body, key)

    @allure.title("Home featured_maps is non-empty")
    def test_home_has_maps(self, anon_client):
        status, body = anon_client.home()
        assert_status(status, 200)
        assert_not_empty(body["featured_maps"])
        map_item = body["featured_maps"][0]
        for key in ("id", "name", "slug", "tactic_count", "cover_url"):
            assert_has_key(map_item, key)


@allure.feature("Public Maps")
class TestMaps:

    @allure.title("List maps returns published maps")
    def test_list_maps(self, anon_client):
        status, maps = anon_client.list_maps()
        attach_body(maps)
        assert_status(status, 200)
        assert_not_empty(maps)

    @allure.title("Map detail with slug returns full info")
    def test_map_detail(self, anon_client, first_map_slug):
        status, body = anon_client.map_detail(first_map_slug)
        attach_body(body)
        assert_status(status, 200)
        for key in ("name", "slug", "points", "lineups", "tactics", "filters"):
            assert_has_key(body, key)

    @allure.title("Map detail 404 for unknown slug")
    def test_map_detail_404(self, anon_client):
        status, body = anon_client.map_detail("no-such-map-999")
        assert status == 404, f"Expected 404, got {status}: {body}"


@allure.feature("Public Tactics")
class TestTactics:

    @allure.title("List tactics returns paginated items")
    def test_list_tactics(self, anon_client):
        status, data = anon_client.list_tactics()
        attach_body(data)
        assert_status(status, 200)
        for key in ("items", "total", "page", "page_size"):
            assert_has_key(data, key)
        assert_not_empty(data["items"])

    @allure.title("Tactic detail returns full structure")
    def test_tactic_detail(self, anon_client, first_tactic_slug):
        status, body = anon_client.tactic_detail(first_tactic_slug)
        attach_body(body)
        assert_status(status, 200)
        for key in (
            "title",
            "slug",
            "steps",
            "lineups",
            "routes",
            "screenshots",
            "map_radar_url",
            "map_layout_url",
            "related",
        ):
            assert_has_key(body, key)

    @allure.title("Tactic detail 404 for non-existent slug")
    def test_tactic_detail_404(self, anon_client):
        status, body = anon_client.tactic_detail("no-such-tactic-999")
        assert status == 404, f"Expected 404, got {status}: {body}"

    @allure.title("Tactic list filter by map_slug")
    @pytest.mark.parametrize("map_slug", ["mirage"], indirect=False)
    def test_filter_by_map(self, anon_client, map_slug):
        status, data = anon_client.list_tactics({"map_slug": map_slug})
        assert_status(status, 200)
        for item in data["items"]:
            assert item["map"]["slug"] == map_slug, (
                f"Tactic {item['id']} on {item['map']['slug']}, expected {map_slug}"
            )

    @allure.title("Tactic list filter by side")
    @pytest.mark.parametrize("side", ["T", "CT"])
    def test_filter_by_side(self, anon_client, side):
        status, data = anon_client.list_tactics({"side": side})
        assert_status(status, 200)
        for item in data["items"]:
            assert item["side"] == side

    @allure.title("Tactic list filter by difficulty")
    def test_filter_by_difficulty(self, anon_client):
        for difficulty in ("easy", "medium", "hard"):
            status, data = anon_client.list_tactics({"difficulty": difficulty})
            assert_status(status, 200)
            for item in data["items"]:
                assert item["difficulty"] == difficulty

    @allure.title("Tactic list search by keyword")
    def test_search(self, anon_client):
        status, _data = anon_client.list_tactics({"search": "smoke"})
        assert_status(status, 200)
        # Results may be empty; just verify search does not error.

    @allure.title("Tactic list pagination")
    def test_pagination(self, anon_client):
        status, page_one = anon_client.list_tactics({"page": 1, "page_size": 3})
        assert_status(status, 200)
        assert len(page_one["items"]) <= 3
        if page_one["total"] > 3:
            status, page_two = anon_client.list_tactics({"page": 2, "page_size": 3})
            assert_status(status, 200)
            ids_one = {tactic["id"] for tactic in page_one["items"]}
            ids_two = {tactic["id"] for tactic in page_two["items"]}
            assert ids_one.isdisjoint(ids_two), "Page 1 and page 2 overlap"
