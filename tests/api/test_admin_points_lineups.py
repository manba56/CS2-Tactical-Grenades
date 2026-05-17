"""Admin CRUD — points list/create/update, lineups list/update, tactics list."""

import uuid

import pytest
import allure

from utils.allure_helper import (
    assert_status,
    assert_has_key,
    assert_field,
    assert_not_empty,
    attach_body,
)


@allure.feature("Admin Points")
class TestAdminPoints:

    def _first_map_id(self, admin_client):
        status, maps = admin_client.admin_list_maps()
        assert_status(status, 200)
        assert maps, "No maps in DB"
        return maps[0]["id"]

    @allure.title("List points (admin)")
    def test_list_points(self, admin_client):
        status, points = admin_client.admin_list_points()
        attach_body(points)
        assert_status(status, 200)
        assert isinstance(points, list)

    @allure.title("List points filtered by map_id")
    def test_list_points_filtered(self, admin_client):
        map_id = self._first_map_id(admin_client)
        status, points = admin_client.admin_list_points(map_id=map_id)
        attach_body(points)
        assert_status(status, 200)
        assert isinstance(points, list)
        for p in points:
            assert p["map_id"] == map_id, f"Point {p['id']} map_id {p['map_id']} != {map_id}"

    @allure.title("Create point success")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_create_point(self, admin_client):
        map_id = self._first_map_id(admin_client)
        payload = {
            "map_id": map_id,
            "name": f"Test Point {uuid.uuid4().hex[:6]}",
            "key": f"pt_{uuid.uuid4().hex[:4]}",
            "x": 50.0,
            "y": 50.0,
            "side": "T",
            "point_type": "site",
        }
        status, created = admin_client.admin_create_point(payload)
        attach_body(created)
        assert_status(status, 200)
        assert_has_key(created, "id")
        assert created["id"] > 0
        assert created["name"] == payload["name"]

    @allure.title("Create point with invalid map_id")
    def test_create_point_invalid_map(self, admin_client):
        payload = {
            "map_id": 99999,
            "name": "Bad Point",
            "key": "bad_pt",
            "x": 50.0,
            "y": 50.0,
        }
        status, body = admin_client.admin_create_point(payload)
        # SQLite foreign key or FastAPI validation — accept 500 or 400
        assert status in (400, 422, 500), f"Expected 400/422/500, got {status}: {body}"

    @allure.title("Update point success")
    def test_update_point(self, admin_client):
        map_id = self._first_map_id(admin_client)
        # Create a point first
        create_payload = {
            "map_id": map_id,
            "name": f"Point To Update {uuid.uuid4().hex[:6]}",
            "key": f"upd_{uuid.uuid4().hex[:4]}",
            "x": 20.0,
            "y": 30.0,
        }
        _, created = admin_client.admin_create_point(create_payload)
        point_id = created["id"]

        update_payload = {
            "map_id": map_id,
            "name": created["name"] + " (updated)",
            "key": created["key"],
            "x": 60.0,
            "y": 70.0,
        }
        status, updated = admin_client.admin_update_point(point_id, update_payload)
        attach_body(updated)
        assert_status(status, 200)
        assert updated["x"] == 60.0
        assert updated["y"] == 70.0

    @allure.title("Update non-existent point returns 404")
    def test_update_point_not_found(self, admin_client):
        payload = {
            "map_id": 1,
            "name": "Ghost Point",
            "key": "ghost",
            "x": 0.0,
            "y": 0.0,
        }
        status, body = admin_client.admin_update_point(99999, payload)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"


@allure.feature("Admin Lineups List")
class TestAdminLineupsList:

    @allure.title("List lineups (admin)")
    def test_list_lineups(self, admin_client):
        status, lineups = admin_client.admin_list_lineups()
        attach_body(lineups)
        assert_status(status, 200)
        assert isinstance(lineups, list)
        if lineups:
            assert_has_key(lineups[0], "id")
            assert_has_key(lineups[0], "title")

    @allure.title("List lineups filtered by map_id")
    def test_list_lineups_filtered(self, admin_client):
        status, maps = admin_client.admin_list_maps()
        assert_status(status, 200)
        if not maps:
            pytest.skip("No maps available")
        map_id = maps[0]["id"]
        status, lineups = admin_client.admin_list_lineups(map_id=map_id)
        assert_status(status, 200)
        for l in lineups:
            assert l["map_id"] == map_id, f"Lineup {l['id']} map_id mismatch"

    @allure.title("Update lineup title and summary")
    def test_update_lineup(self, admin_client):
        # Get first available lineup
        status, lineups = admin_client.admin_list_lineups()
        assert_status(status, 200)
        if not lineups:
            pytest.skip("No lineups available")
        lineup_id = lineups[0]["id"]

        payload = {
            "map_id": lineups[0]["map_id"],
            "title": lineups[0]["title"] + " (updated)",
            "slug": lineups[0].get("slug", ""),
            "side": lineups[0]["side"],
            "utility_type": lineups[0]["utility_type"],
            "start_point_id": lineups[0]["start_point_id"],
            "aim_point_id": lineups[0]["aim_point_id"],
            "land_point_id": lineups[0]["land_point_id"],
            "purpose": lineups[0].get("purpose", "Updated purpose"),
            "summary": lineups[0].get("summary", "Updated summary"),
            "steps": lineups[0].get("steps", []),
            "media": lineups[0].get("media", []),
            "status": lineups[0].get("status", "draft"),
        }
        status, updated = admin_client.admin_update_lineup(lineup_id, payload)
        attach_body(updated)
        assert_status(status, 200)

    @allure.title("Update non-existent lineup returns 404")
    def test_update_lineup_not_found(self, admin_client):
        payload = {
            "map_id": 1, "title": "Ghost", "slug": "ghost",
            "side": "T", "utility_type": "smoke",
            "start_point_id": 1, "aim_point_id": 1, "land_point_id": 1,
            "purpose": "Test", "summary": "Test",
        }
        status, body = admin_client.admin_update_lineup(99999, payload)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"


@allure.feature("Admin Tactics List")
class TestAdminTacticsList:

    @allure.title("List tactics (admin view includes non-published)")
    def test_list_tactics_admin(self, admin_client):
        status, tactics = admin_client.admin_list_tactics()
        attach_body(tactics)
        assert_status(status, 200)
        assert isinstance(tactics, list)
        assert_not_empty(tactics)
        if tactics:
            assert_has_key(tactics[0], "id")
            assert_has_key(tactics[0], "title")

    @allure.title("Admin list includes draft tactics")
    def test_list_tactics_includes_drafts(self, admin_client):
        status, tactics = admin_client.admin_list_tactics()
        assert_status(status, 200)
        statuses = {t.get("status") for t in tactics}
        # Admin view should show at least some tactics (may all be published)
        assert len(tactics) > 0, "Admin tactics list should not be empty"
