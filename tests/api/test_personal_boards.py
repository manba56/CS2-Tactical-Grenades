"""Personal tactic board API CRUD tests."""

import allure

from utils.allure_helper import assert_status, assert_has_key, attach_body


def _board_payload(title: str = "API Mirage A execute") -> dict:
    return {
        "title": title,
        "map_id": 5,
        "side": "T",
        "plan_type": "exec",
        "summary": "Window smoke, connector smoke, then split A.",
        "markers": [
            {"x": 18, "y": 82, "label": "P1", "role": "player", "side": "T"},
            {"x": 47, "y": 37, "label": "Window", "role": "smoke", "side": "BOTH"},
        ],
        "routes": [],
    }


@allure.feature("Personal Tactic Board")
class TestPersonalBoards:

    @allure.title("Personal board can be created, updated, listed, and deleted")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_personal_board_lifecycle(self, player_client):
        status, created = player_client.create_personal_board(_board_payload())
        attach_body(created)
        assert_status(status, 200)
        assert_has_key(created, "id")
        assert created["map"]["slug"] == "mirage"
        board_id = created["id"]

        status, listed = player_client.list_personal_boards()
        assert_status(status, 200)
        assert board_id in [item["id"] for item in listed]

        payload = _board_payload("API Mirage A execute v2")
        payload["markers"].append({"x": 78, "y": 41, "label": "A hit", "role": "note", "side": "BOTH"})
        status, updated = player_client.update_personal_board(board_id, payload)
        assert_status(status, 200)
        assert updated["title"] == "API Mirage A execute v2"
        assert len(updated["markers"]) == 3

        status, body = player_client.delete_personal_board(board_id)
        assert_status(status, 200)
        assert body["status"] == "ok"

    @allure.title("Invalid board marker is rejected")
    def test_invalid_marker_is_rejected(self, player_client):
        payload = _board_payload()
        payload["markers"] = [{"x": -1, "y": 20, "label": "bad", "role": "smoke", "side": "BOTH"}]

        status, body = player_client.create_personal_board(payload)
        attach_body(body)
        assert status == 422, f"Expected 422, got {status}: {body}"
