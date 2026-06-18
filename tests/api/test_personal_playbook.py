"""Personal playbook API: lineup favorites and training progress."""

import pytest
import allure

from utils.allure_helper import assert_status, assert_has_key, attach_body


def _first_lineup_id(anon_client) -> int:
    status, detail = anon_client.map_detail("mirage")
    assert_status(status, 200)
    lineups = detail.get("lineups", [])
    if not lineups:
        pytest.skip("No published lineups available")
    return lineups[0]["id"]


def _first_tactic_id(anon_client) -> int:
    status, data = anon_client.list_tactics({"page_size": 1})
    assert_status(status, 200)
    items = data.get("items", [])
    if not items:
        pytest.skip("No tactics available")
    return items[0]["id"]


@allure.feature("Personal Playbook")
class TestPersonalPlaybook:

    @allure.title("Favorites bundle includes lineups and progress fields")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_bundle_structure(self, player_client):
        status, body = player_client.get_favorites()
        attach_body(body)
        assert_status(status, 200)
        for key in (
            "favorites",
            "recent",
            "favorite_lineups",
            "lineup_progress",
            "tactic_progress",
        ):
            assert_has_key(body, key)
        assert isinstance(body["favorite_lineups"], list)
        assert isinstance(body["lineup_progress"], dict)
        assert isinstance(body["tactic_progress"], dict)

    @allure.title("Lineup favorite is idempotent and removable")
    def test_lineup_favorite_lifecycle(self, player_client, anon_client):
        lineup_id = _first_lineup_id(anon_client)

        status, _ = player_client.add_lineup_favorite(lineup_id)
        assert_status(status, 200)
        status, _ = player_client.add_lineup_favorite(lineup_id)
        assert_status(status, 200)

        status, body = player_client.get_favorites()
        assert_status(status, 200)
        favorite_ids = [item["id"] for item in body["favorite_lineups"]]
        assert favorite_ids.count(lineup_id) == 1

        status, _ = player_client.remove_lineup_favorite(lineup_id)
        assert_status(status, 200)
        status, body = player_client.get_favorites()
        favorite_ids = [item["id"] for item in body["favorite_lineups"]]
        assert lineup_id not in favorite_ids

    @allure.title("Lineup and tactic progress can be set and cleared")
    def test_progress_lifecycle(self, player_client, anon_client):
        lineup_id = _first_lineup_id(anon_client)
        tactic_id = _first_tactic_id(anon_client)

        status, _ = player_client.set_lineup_progress(lineup_id, "match_ready")
        assert_status(status, 200)
        status, _ = player_client.set_tactic_progress(tactic_id, "mastered")
        assert_status(status, 200)

        status, body = player_client.get_favorites()
        assert_status(status, 200)
        assert body["lineup_progress"][str(lineup_id)] == "match_ready"
        assert body["tactic_progress"][str(tactic_id)] == "mastered"

        status, _ = player_client.set_lineup_progress(lineup_id, None)
        assert_status(status, 200)
        status, _ = player_client.set_tactic_progress(tactic_id, None)
        assert_status(status, 200)

        status, body = player_client.get_favorites()
        assert str(lineup_id) not in body["lineup_progress"]
        assert str(tactic_id) not in body["tactic_progress"]

    @allure.title("Invalid training status is rejected")
    def test_invalid_progress_status(self, player_client, anon_client):
        lineup_id = _first_lineup_id(anon_client)
        status, body = player_client.set_lineup_progress(lineup_id, "done")
        assert status == 422, f"Expected 422, got {status}: {body}"

    @allure.title("sync-local merges local lineup favorites and progress")
    def test_sync_local(self, player_client, anon_client):
        lineup_id = _first_lineup_id(anon_client)
        tactic_id = _first_tactic_id(anon_client)

        status, body = player_client.sync_local_playbook({
            "favorite_lineup_ids": [lineup_id],
            "lineup_progress": {str(lineup_id): "practicing"},
            "tactic_progress": {str(tactic_id): "match_ready"},
        })
        attach_body(body)
        assert_status(status, 200)

        status, body = player_client.get_favorites()
        assert_status(status, 200)
        assert lineup_id in [item["id"] for item in body["favorite_lineups"]]
        assert body["lineup_progress"][str(lineup_id)] == "practicing"
        assert body["tactic_progress"][str(tactic_id)] == "match_ready"
