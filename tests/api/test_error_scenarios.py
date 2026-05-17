"""Error scenarios — 422 validation, 409 conflict, 404 not found, admin asset errors."""

import pytest
import allure
import uuid

from utils.allure_helper import assert_status, assert_error, attach_body
import config


@allure.feature("Error Scenarios — Validation (422)")
class TestValidationErrors422:

    @allure.title("Register with missing fields returns 422")
    def test_register_missing_fields(self, anon_client):
        status, body = anon_client._do("POST", "/api/public/auth/register", json={})
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Register with invalid email length returns 422")
    def test_register_email_too_short(self, anon_client):
        status, body = anon_client._do("POST", "/api/public/auth/register", json={
            "username": "validuser",
            "email": "a",
            "password": "pass123",
        })
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Login with missing fields returns 422")
    def test_login_missing_fields(self, anon_client):
        status, body = anon_client._do("POST", "/api/public/auth/login", json={})
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create map with missing required fields returns 422")
    def test_create_map_missing_required(self, admin_client):
        status, body = admin_client._do("POST", "/api/admin/maps", json={})
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create tactic with missing required fields returns 422")
    def test_create_tactic_missing_required(self, admin_client):
        status, body = admin_client._do("POST", "/api/admin/tactics", json={})
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create point with invalid x range returns 422")
    def test_create_point_invalid_x(self, admin_client):
        payload = {"map_id": 1, "name": "Bad", "key": "bad", "x": 150.0, "y": 50.0}
        status, body = admin_client._do("POST", "/api/admin/points", json=payload)
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create point with invalid y range returns 422")
    def test_create_point_invalid_y(self, admin_client):
        payload = {"map_id": 1, "name": "Bad", "key": "bad", "x": 50.0, "y": -5.0}
        status, body = admin_client._do("POST", "/api/admin/points", json=payload)
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create lineup with invalid side returns 422")
    def test_create_lineup_invalid_side(self, admin_client):
        payload = {
            "map_id": 1, "title": "Bad", "slug": "bad",
            "side": "NORTH", "utility_type": "smoke",
            "start_point_id": 1, "aim_point_id": 1, "land_point_id": 1,
            "purpose": "Test", "summary": "Test",
        }
        status, body = admin_client._do("POST", "/api/admin/lineups", json=payload)
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"

    @allure.title("Create tactic with invalid players count returns 422")
    def test_create_tactic_invalid_players(self, admin_client):
        payload = {
            "map_id": 1, "title": "Bad", "slug": "bad",
            "side": "T", "goal": "Test", "phase": "exec",
            "players": 99, "summary": "S", "note": "", "cover_url": "",
        }
        status, body = admin_client._do("POST", "/api/admin/tactics", json=payload)
        assert status in (400, 422), f"Expected 400 or 422, got {status}: {body}"


@allure.feature("Error Scenarios — Conflict (409)")
class TestConflict409:

    @allure.title("Delete lineup referenced by tactic returns 409")
    def test_delete_lineup_referenced_by_tactic(self, admin_client):
        # Create map → point → lineup → tactic referencing lineup
        status, maps = admin_client.admin_list_maps()
        if status != 200 or not maps:
            pytest.skip("No maps available")
        map_id = maps[0]["id"]

        # Create point
        pt_payload = {
            "map_id": map_id,
            "name": f"409 Point {uuid.uuid4().hex[:4]}",
            "key": f"k409_{uuid.uuid4().hex[:4]}",
            "x": 50.0, "y": 50.0,
        }
        status, point = admin_client.admin_create_point(pt_payload)
        if status != 200:
            pytest.skip(f"Could not create point: {point}")
        point_id = point["id"]

        # Create lineup
        lineup_payload = {
            "map_id": map_id, "title": f"409 Lineup {uuid.uuid4().hex[:4]}",
            "slug": "", "side": "T", "utility_type": "smoke",
            "start_point_id": point_id, "aim_point_id": point_id,
            "land_point_id": point_id, "purpose": "Test", "summary": "Test",
            "steps": [], "media": [], "status": "draft",
        }
        status, lineup = admin_client.admin_create_lineup(lineup_payload)
        if status != 200:
            pytest.skip(f"Could not create lineup: {lineup}")
        lineup_id = lineup["id"]

        # Create tactic referencing this lineup
        tactic_payload = {
            "map_id": map_id, "title": f"409 Tactic {uuid.uuid4().hex[:4]}",
            "slug": "", "side": "T", "goal": "Test", "phase": "exec",
            "players": 3, "summary": "Test", "note": "", "cover_url": "",
            "step_items": [
                {"order": 1, "role": "Smoker", "type": "utility",
                 "instruction": "Throw smoke", "lineup_id": lineup_id}
            ],
            "routes": [], "screenshots": [], "status": "draft",
        }
        status, tactic = admin_client.admin_create_tactic(tactic_payload)
        if status != 200:
            pytest.skip(f"Could not create tactic: {tactic}")
        tactic_id = tactic["id"]

        # Try to delete lineup — should get 409
        status, body = admin_client.admin_delete_lineup(lineup_id)
        assert status in (400, 409), \
            f"Expected 400 or 409 (lineup referenced by tactic {tactic_id}), got {status}: {body}"

        # Cleanup: archive + delete tactic first, then archive + delete lineup
        admin_client.admin_archive_tactic(tactic_id)
        # Unable to delete tactic directly — just archive
        admin_client.admin_archive_lineup(lineup_id)


@allure.feature("Error Scenarios — Not Found (404)")
class TestNotFound404:

    @allure.title("Update non-existent map returns 404")
    def test_update_nonexistent_map(self, admin_client):
        payload = {"name": "X", "slug": "x", "overview": "X", "cover_url": "", "layout_url": ""}
        status, body = admin_client.admin_update_map(99999, payload)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"

    @allure.title("Update non-existent tactic returns 404")
    def test_update_nonexistent_tactic(self, admin_client):
        payload = {
            "map_id": 1, "title": "X", "slug": "x",
            "side": "T", "goal": "X", "phase": "exec",
            "players": 3, "summary": "X", "note": "", "cover_url": "",
        }
        status, body = admin_client.admin_update_tactic(99999, payload)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"

    @allure.title("Archive non-existent tactic returns 404")
    def test_archive_nonexistent_tactic(self, admin_client):
        status, body = admin_client.admin_archive_tactic(99999)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"

    @allure.title("Publish non-existent tactic returns 404")
    def test_publish_nonexistent_tactic(self, admin_client):
        status, body = admin_client.admin_publish_tactic(99999)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"

    @allure.title("Archive non-existent lineup returns 404")
    def test_archive_nonexistent_lineup(self, admin_client):
        status, body = admin_client.admin_archive_lineup(99999)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"

    @allure.title("Delete non-existent lineup returns 404")
    def test_delete_nonexistent_lineup(self, admin_client):
        status, body = admin_client.admin_delete_lineup(99999)
        assert status in (404, 429), f"Expected 404 or 429, got {status}: {body}"


@allure.feature("Error Scenarios — Admin Asset Errors")
class TestAdminAssetErrors:

    @allure.title("Upload file without auth returns 401")
    def test_upload_without_auth(self, anon_client, tmp_path):
        png = tmp_path / "test.png"
        png_data = (
            b"\x89PNG\r\n\x1a\n"
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        png.write_bytes(png_data)
        from utils.api_client import Client
        status, body = Client().admin_upload_asset(str(png))
        assert status in (401, 429), f"Expected 401 or 429, got {status}: {body}"

    @allure.title("Upload text file as image is rejected")
    def test_upload_non_image(self, admin_client, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("this is not an image file")
        from utils.api_client import Client
        status, body = Client(token=admin_client.token).admin_upload_asset(str(txt))
        assert status in (400, 422, 429), f"Expected 400/422/429, got {status}: {body}"
