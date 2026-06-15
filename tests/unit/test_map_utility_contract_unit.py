from __future__ import annotations

from uuid import uuid4

from fastapi.testclient import TestClient


def _client_with_temp_store(tmp_path, monkeypatch) -> TestClient:
    from app import main
    from app.storage import SqliteStore

    monkeypatch.setattr(main, "STORE", SqliteStore(tmp_path / "db.sqlite"))
    return TestClient(main.app)


def _admin_headers(client: TestClient) -> dict[str, str]:
    response = client.post(
        "/api/admin/auth/login",
        json={"username": "admin", "password": "admin123"},
    )
    assert response.status_code == 200, response.text
    return {"Authorization": f"Bearer {response.json()['token']}"}


def _published_map(client: TestClient, headers: dict[str, str], slug: str = "mirage") -> dict:
    response = client.get("/api/admin/maps", headers=headers)
    assert response.status_code == 200, response.text
    for item in response.json():
        if item["slug"] == slug:
            return item
    raise AssertionError(f"Seed map not found: {slug}")


def _create_point(client: TestClient, headers: dict[str, str], payload: dict) -> dict:
    response = client.post("/api/admin/points", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def _create_lineup(client: TestClient, headers: dict[str, str], payload: dict) -> dict:
    response = client.post("/api/admin/lineups", json=payload, headers=headers)
    assert response.status_code == 200, response.text
    return response.json()


def test_public_map_groups_multiple_lineups_on_one_landing_point(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _admin_headers(client)
    map_item = _published_map(client, headers, "mirage")
    suffix = uuid4().hex[:8]

    aim_point = _create_point(
        client,
        headers,
        {
            "map_id": map_item["id"],
            "name": f"Contract Aim {suffix}",
            "key": f"contract-aim-{suffix}",
            "x": 31,
            "y": 67,
            "side": "T",
            "point_type": "staging",
            "description": "stand by the wall",
            "aim_image_url": "/static/uploads/stand-aim.png",
            "aim_image_description": "站位瞄点说明",
        },
    )
    land_point = _create_point(
        client,
        headers,
        {
            "map_id": map_item["id"],
            "name": f"Contract Land {suffix}",
            "key": f"contract-land-{suffix}",
            "x": 78,
            "y": 42,
            "side": "BOTH",
            "point_type": "site",
            "description": "lands on the box",
            "effect_image_url": "/static/uploads/land-effect.png",
            "effect_image_description": "落点效果说明",
            "video_url": "https://example.com/land.mp4",
        },
    )

    created = [
        _create_lineup(
            client,
            headers,
            {
                "map_id": map_item["id"],
                "title": f"{utility.title()} Contract {suffix}",
                "slug": f"{utility}-contract-{suffix}",
                "side": "T",
                "utility_type": utility,
                "start_point_id": aim_point["id"],
                "aim_point_id": aim_point["id"],
                "land_point_id": land_point["id"],
                "purpose": "contract test",
                "difficulty": "easy",
                "summary": "same landing point can hold more than one utility",
                "steps": ["stand", "aim", "throw"],
                "media": [f"/static/uploads/{utility}-extra.png"],
                "video_url": f"https://example.com/{utility}.mp4",
                "status": "published",
            },
        )
        for utility in ("smoke", "flash")
    ]

    response = client.get(f"/api/public/maps/{map_item['slug']}")
    assert response.status_code == 200, response.text
    detail = response.json()

    lineups_for_landing = [
        item for item in detail["lineups"] if item["land_point_id"] == land_point["id"]
    ]
    assert {item["id"] for item in lineups_for_landing} == {item["id"] for item in created}
    assert {item["utility_type"] for item in lineups_for_landing} == {"smoke", "flash"}

    for lineup in lineups_for_landing:
        assert lineup["start_point_id"] == aim_point["id"]
        assert lineup["aim_point_id"] == aim_point["id"]
        assert lineup["start_point"]["aim_image_url"] == "/static/uploads/stand-aim.png"
        assert lineup["start_point"]["aim_image_description"] == "站位瞄点说明"
        assert lineup["land_point"]["effect_image_url"] == "/static/uploads/land-effect.png"
        assert lineup["land_point"]["effect_image_description"] == "落点效果说明"
        assert lineup["video_url"].startswith("https://example.com/")


def test_tactic_search_matches_chinese_keyword_from_title(tmp_path, monkeypatch):
    client = _client_with_temp_store(tmp_path, monkeypatch)
    headers = _admin_headers(client)
    map_item = _published_map(client, headers, "dust2")
    suffix = uuid4().hex[:8]

    aim_point = _create_point(
        client,
        headers,
        {
            "map_id": map_item["id"],
            "name": f"Dust2 Aim {suffix}",
            "key": f"dust2-aim-{suffix}",
            "x": 20,
            "y": 70,
            "side": "T",
            "point_type": "staging",
        },
    )
    land_point = _create_point(
        client,
        headers,
        {
            "map_id": map_item["id"],
            "name": f"Dust2 Land {suffix}",
            "key": f"dust2-land-{suffix}",
            "x": 80,
            "y": 35,
            "side": "BOTH",
            "point_type": "site",
        },
    )
    lineup = _create_lineup(
        client,
        headers,
        {
            "map_id": map_item["id"],
            "title": f"Dust2 Smoke {suffix}",
            "slug": f"dust2-smoke-{suffix}",
            "side": "T",
            "utility_type": "smoke",
            "start_point_id": aim_point["id"],
            "aim_point_id": aim_point["id"],
            "land_point_id": land_point["id"],
            "purpose": "search contract",
            "difficulty": "medium",
            "summary": "search contract",
            "steps": ["throw"],
            "media": [],
            "status": "published",
        },
    )

    tactic_payload = {
        "map_id": map_item["id"],
        "title": f"炙热沙城搜索契约 {suffix}",
        "slug": f"dust2-search-contract-{suffix}",
        "side": "T",
        "goal": "A execute",
        "phase": "exec",
        "difficulty": "medium",
        "players": 3,
        "summary": "中文搜索应该能命中标题",
        "note": "",
        "tags": ["沙城", "搜索"],
        "cover_url": "/static/uploads/search-cover.png",
        "step_items": [
            {
                "order": 1,
                "role": "1",
                "type": "utility",
                "instruction": "throw smoke",
                "lineup_id": lineup["id"],
            }
        ],
        "routes": [],
        "screenshots": [],
        "status": "published",
        "featured": False,
    }
    created_tactic = client.post("/api/admin/tactics", json=tactic_payload, headers=headers)
    assert created_tactic.status_code == 200, created_tactic.text

    response = client.get("/api/public/tactics", params={"search": "沙城"})
    assert response.status_code == 200, response.text
    slugs = {item["slug"] for item in response.json()["items"]}
    assert tactic_payload["slug"] in slugs
