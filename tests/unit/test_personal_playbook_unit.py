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


def test_personal_bundle_contains_lineups_and_progress(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    response = client.get("/api/public/me/favorites", headers=headers)
    assert response.status_code == 200
    body = response.json()

    assert "favorite_lineups" in body
    assert "lineup_progress" in body
    assert "tactic_progress" in body
    assert isinstance(body["favorite_lineups"], list)
    assert isinstance(body["lineup_progress"], dict)
    assert isinstance(body["tactic_progress"], dict)


def test_lineup_favorite_is_idempotent(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    detail = client.get("/api/public/maps/mirage").json()
    lineup_id = detail["lineups"][0]["id"]

    assert client.post(f"/api/public/me/lineups/favorites/{lineup_id}", headers=headers).status_code == 200
    assert client.post(f"/api/public/me/lineups/favorites/{lineup_id}", headers=headers).status_code == 200
    bundle = client.get("/api/public/me/favorites", headers=headers).json()
    assert [item["id"] for item in bundle["favorite_lineups"]].count(lineup_id) == 1

    assert client.delete(f"/api/public/me/lineups/favorites/{lineup_id}", headers=headers).status_code == 200
    bundle = client.get("/api/public/me/favorites", headers=headers).json()
    assert lineup_id not in [item["id"] for item in bundle["favorite_lineups"]]


def test_set_progress_and_reject_invalid_status(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    detail = client.get("/api/public/maps/mirage").json()
    lineup_id = detail["lineups"][0]["id"]
    tactic = client.get("/api/public/tactics", params={"page_size": 1}).json()["items"][0]

    response = client.put(
        f"/api/public/me/progress/lineups/{lineup_id}",
        json={"status": "match_ready"},
        headers=headers,
    )
    assert response.status_code == 200
    response = client.put(
        f"/api/public/me/progress/tactics/{tactic['id']}",
        json={"status": "mastered"},
        headers=headers,
    )
    assert response.status_code == 200

    bundle = client.get("/api/public/me/favorites", headers=headers).json()
    assert bundle["lineup_progress"][str(lineup_id)] == "match_ready"
    assert bundle["tactic_progress"][str(tactic["id"])] == "mastered"

    response = client.put(
        f"/api/public/me/progress/lineups/{lineup_id}",
        json={"status": "bad"},
        headers=headers,
    )
    assert response.status_code == 422


def test_sync_local_merges_favorites_and_progress(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _auth_headers(client)

    detail = client.get("/api/public/maps/mirage").json()
    lineup_id = detail["lineups"][0]["id"]
    tactic = client.get("/api/public/tactics", params={"page_size": 1}).json()["items"][0]

    response = client.post(
        "/api/public/me/sync-local",
        json={
            "favorite_lineup_ids": [lineup_id],
            "lineup_progress": {str(lineup_id): "practicing"},
            "tactic_progress": {str(tactic["id"]): "match_ready"},
        },
        headers=headers,
    )
    assert response.status_code == 200

    bundle = client.get("/api/public/me/favorites", headers=headers).json()
    assert lineup_id in [item["id"] for item in bundle["favorite_lineups"]]
    assert bundle["lineup_progress"][str(lineup_id)] == "practicing"
    assert bundle["tactic_progress"][str(tactic["id"])] == "match_ready"
