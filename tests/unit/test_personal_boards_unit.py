from fastapi.testclient import TestClient


def _client_with_temp_store(tmp_path, monkeypatch) -> TestClient:
    from app import main
    from app.storage import SqliteStore

    monkeypatch.setattr(main, "STORE", SqliteStore(tmp_path / "db.sqlite"))
    return TestClient(main.app)


def _auth_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/public/auth/login",
        json={"username_or_email": "demo", "password": "demo123"},
    )
    assert response.status_code == 200
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _board_payload(title: str = "Mirage A execute") -> dict:
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


def test_personal_board_requires_login(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)

    assert client.get("/api/public/me/boards").status_code == 401
    assert client.post("/api/public/me/boards", json=_board_payload()).status_code == 401


def test_personal_board_crud(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    created = client.post("/api/public/me/boards", json=_board_payload(), headers=headers)
    assert created.status_code == 200
    board = created.json()
    assert board["title"] == "Mirage A execute"
    assert board["map"]["slug"] == "mirage"
    assert len(board["markers"]) == 2

    listed = client.get("/api/public/me/boards", headers=headers)
    assert listed.status_code == 200
    assert [item["id"] for item in listed.json()] == [board["id"]]

    update_payload = _board_payload("Mirage A execute v2")
    update_payload["markers"].append({"x": 78, "y": 41, "label": "A hit", "role": "note", "side": "BOTH"})
    updated = client.put(f"/api/public/me/boards/{board['id']}", json=update_payload, headers=headers)
    assert updated.status_code == 200
    assert updated.json()["title"] == "Mirage A execute v2"
    assert len(updated.json()["markers"]) == 3

    deleted = client.delete(f"/api/public/me/boards/{board['id']}", headers=headers)
    assert deleted.status_code == 200
    assert client.get("/api/public/me/boards", headers=headers).json() == []


def test_personal_board_validates_payload(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    bad_marker = _board_payload()
    bad_marker["markers"] = [{"x": 120, "y": 20, "label": "bad", "role": "smoke", "side": "BOTH"}]
    response = client.post("/api/public/me/boards", json=bad_marker, headers=headers)
    assert response.status_code == 422

    bad_map = _board_payload()
    bad_map["map_id"] = 9999
    response = client.post("/api/public/me/boards", json=bad_map, headers=headers)
    assert response.status_code == 404
