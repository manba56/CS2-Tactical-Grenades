from datetime import timedelta

from fastapi.testclient import TestClient


def _client_with_temp_store(tmp_path, monkeypatch) -> TestClient:
    from app import main
    from app.storage import SqliteStore

    monkeypatch.setattr(main, "STORE", SqliteStore(tmp_path / "db.sqlite"))
    return TestClient(main.app)


def test_logout_revokes_current_token(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)

    response = client.post(
        "/api/public/auth/login",
        json={"username_or_email": "demo", "password": "demo123"},
    )
    assert response.status_code == 200
    headers = {"Authorization": f"Bearer {response.json()['token']}"}

    assert client.get("/api/public/me/favorites", headers=headers).status_code == 200
    assert client.post("/api/public/auth/logout", headers=headers).status_code == 200
    assert client.get("/api/public/me/favorites", headers=headers).status_code == 401


def test_expired_token_is_rejected_and_removed(tmp_path, monkeypatch):
    from app import main

    client = _client_with_temp_store(tmp_path, monkeypatch)

    response = client.post(
        "/api/public/auth/login",
        json={"username_or_email": "demo", "password": "demo123"},
    )
    assert response.status_code == 200
    token = response.json()["token"]

    def expire_first_token(state):
        state["tokens"][0]["expires_at"] = main.utc_iso(main.utc_now() - timedelta(seconds=1))
        return {}

    main.STORE.mutate(expire_first_token)

    headers = {"Authorization": f"Bearer {token}"}
    response = client.get("/api/public/me/favorites", headers=headers)
    assert response.status_code == 401
    assert "过期" in response.json()["detail"]
    assert main.STORE.snapshot()["tokens"] == []
