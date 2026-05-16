"""Admin CRUD — maps, lineups, tactics lifecycle."""

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


@allure.feature("Admin Dashboard")
class TestDashboard:

    @allure.title("Dashboard returns counts")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_dashboard(self, admin_client):
        status, body = admin_client.admin_dashboard()
        attach_body(body)
        assert_status(status, 200)
        for k in ("maps", "tactics", "lineups", "users"):
            assert_has_key(body, k)
            assert isinstance(body[k], int), f"{k} should be int, got {type(body[k])}"


@allure.feature("Admin Maps")
class TestAdminMaps:

    @allure.title("List all maps (including non-published)")
    def test_list_maps(self, admin_client):
        status, maps = admin_client.admin_list_maps()
        attach_body(maps)
        assert_status(status, 200)
        assert_not_empty(maps)

    @allure.title("Create → update map lifecycle")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_map_lifecycle(self, admin_client):
        payload = {
            "name": f"Test Map {uuid.uuid4().hex[:6]}",
            "slug": "",
            "overview": "Auto-test created map",
            "cover_url": "",
            "layout_url": "",
            "callout_color": "#00ff00",
            "order": 99,
            "status": "draft",
            "active_pool": False,
        }
        # Create
        status, created = admin_client.admin_create_map(payload)
        attach_body(created)
        assert_status(status, 200)
        map_id = created["id"]
        assert map_id > 0

        # Update
        payload["name"] = payload["name"] + " (updated)"
        payload["slug"] = ""
        status, updated = admin_client.admin_update_map(map_id, payload)
        assert_status(status, 200)
        assert payload["name"] in updated["name"]

    @allure.title("Non-admin cannot access admin endpoints")
    def test_non_admin_forbidden(self, player_client):
        status, body = player_client.admin_dashboard()
        assert status == 403, f"Expected 403, got {status}: {body}"


@allure.feature("Admin Lineups")
class TestAdminLineups:

    def _first_map_id(self, admin_client):
        status, maps = admin_client.admin_list_maps()
        assert_status(status, 200)
        assert maps, "No maps in DB"
        return maps[0]["id"]

    def _first_point_id(self, admin_client, map_id: int):
        from utils.api_client import Client
        status, points = admin_client._do("GET", f"/api/admin/points?map_id={map_id}")
        assert_status(status, 200)
        if not points:
            # Create a temp point
            pt_payload = {
                "map_id": map_id,
                "name": "Test Point",
                "x": 0.5,
                "y": 0.5,
                "kind": "default",
            }
            status, point = admin_client._do("POST", "/api/admin/points", json=pt_payload)
            assert_status(status, 200)
            return point["id"]
        return points[0]["id"]

    @allure.title("Create lineup and verify detail")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_lineup_lifecycle(self, admin_client):
        map_id = self._first_map_id(admin_client)
        point_id = self._first_point_id(admin_client, map_id)

        payload = {
            "map_id": map_id,
            "title": f"Test Lineup {uuid.uuid4().hex[:6]}",
            "slug": "",
            "utility_type": "smoke",
            "start_point_id": point_id,
            "aim_point_id": point_id,
            "land_point_id": point_id,
            "throw_style": "jumpthrow",
            "description": "Auto-test lineup",
            "status": "draft",
        }
        status, created = admin_client.admin_create_lineup(payload)
        attach_body(created)
        assert_status(status, 200)
        lineup_id = created["id"]
        assert lineup_id > 0
        assert_has_key(created, "start_point")

        # Archive
        status, _ = admin_client.admin_archive_lineup(lineup_id)
        assert_status(status, 200)

        # Delete archived lineup
        status, _ = admin_client.admin_delete_lineup(lineup_id)
        assert_status(status, 200)


@allure.feature("Admin Tactics")
class TestAdminTactics:

    def _first_map_id(self, admin_client):
        status, maps = admin_client.admin_list_maps()
        assert_status(status, 200)
        return maps[0]["id"]

    @allure.title("Create → update → publish → archive tactic lifecycle")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_tactic_lifecycle(self, admin_client):
        import uuid
        map_id = self._first_map_id(admin_client)
        title = f"Test Tactic {uuid.uuid4().hex[:6]}"

        payload = {
            "map_id": map_id,
            "title": title,
            "slug": "",
            "side": "T",
            "goal": "A 点爆弹",
            "phase": "exec",
            "difficulty": "medium",
            "players": 3,
            "summary": "Auto-test tactic",
            "note": "",
            "tags": ["test", "auto"],
            "cover_url": "",
            "featured": False,
            "status": "draft",
            "step_items": [
                {"order": 1, "role": "主道具位", "type": "utility", "instruction": "补首颗烟", "lineup_id": None},
            ],
            "routes": [],
            "screenshots": [],
        }
        # Create
        status, created = admin_client.admin_create_tactic(payload)
        attach_body(created)
        assert_status(status, 200)
        tactic_id = created["id"]
        assert created["slug"], "Slug should be auto-generated"

        # Update
        payload["title"] = title + " (updated)"
        status, updated = admin_client.admin_update_tactic(tactic_id, payload)
        assert_status(status, 200)
        assert "updated" in updated["title"]

        # Publish
        status, _ = admin_client.admin_publish_tactic(tactic_id)
        assert_status(status, 200)

        # Verify visible in public list
        from utils.api_client import Client as C
        status, pub_data = C().list_tactics({"search": title})
        assert_status(status, 200)
        pub_ids = [t["id"] for t in pub_data["items"]]
        assert tactic_id in pub_ids, f"Published tactic {tactic_id} not visible in public list"

        # Archive
        status, _ = admin_client.admin_archive_tactic(tactic_id)
        assert_status(status, 200)


@allure.feature("Admin Users")
class TestAdminUsers:

    @allure.title("List users returns player list")
    def test_list_users(self, admin_client):
        status, users = admin_client.admin_list_users()
        attach_body(users)
        assert_status(status, 200)
        for u in users:
            assert_has_key(u, "id")
            assert_has_key(u, "username")
            # Password hash must NOT be in response
            assert "password_hash" not in u, "password_hash leaked in response!"
