from __future__ import annotations

import shutil
from datetime import datetime
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.staticfiles import StaticFiles

from .auth import create_token, hash_password, parse_token, public_user_payload, verify_password
from .schemas import (
    AdminLoginRequest,
    LineupPayload,
    LoginRequest,
    MapPayload,
    PointPayload,
    RegisterRequest,
    TacticPayload,
    dump_model,
)
from .seed import build_seed_state
from .storage import JsonStore

BASE_DIR = Path(__file__).resolve().parent.parent
STORE = JsonStore(BASE_DIR / "data" / "db.json")
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

app = FastAPI(title="CS2 Tactics API", version="0.1.0")
app.mount("/static", StaticFiles(directory=BASE_DIR / "app" / "static"), name="static")
app.add_middleware(
    CORSMiddleware,
    allow_origins=[
        "http://127.0.0.1:5173",
        "http://localhost:5173",
        "http://127.0.0.1:5174",
        "http://localhost:5174",
        "http://127.0.0.1:5175",
        "http://localhost:5175",
    ],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


def get_bearer_token(authorization: str | None = Header(default=None)) -> str | None:
    if not authorization:
        return None
    prefix = "Bearer "
    if authorization.startswith(prefix):
        return authorization[len(prefix) :].strip()
    return authorization.strip()


def find_by_id(items: list[dict[str, Any]], entity_id: int) -> dict[str, Any]:
    for item in items:
        if item["id"] == entity_id:
            return item
    raise HTTPException(status_code=404, detail="资源不存在")


def find_by_slug(items: list[dict[str, Any]], slug: str) -> dict[str, Any]:
    for item in items:
        if item["slug"] == slug:
            return item
    raise HTTPException(status_code=404, detail="资源不存在")


def next_id(state: dict[str, Any], key: str) -> int:
    entity_id = state["counters"][key]
    state["counters"][key] += 1
    return entity_id


def get_current_user(token: str = Depends(get_bearer_token)) -> dict[str, Any]:
    parsed = parse_token(token)
    if not parsed:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    role, user_id = parsed
    state = STORE.snapshot()
    user = next((item for item in state["users"] if item["id"] == user_id and item["role"] == role), None)
    if not user:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态失效")
    return user


def get_admin_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台权限")
    return user


def summarize_map(state: dict[str, Any], map_item: dict[str, Any]) -> dict[str, Any]:
    tactic_count = sum(1 for tactic in state["tactics"] if tactic["map_id"] == map_item["id"] and tactic["status"] == "published")
    return {
        **map_item,
        "tactic_count": tactic_count,
    }


def summarize_tactic(state: dict[str, Any], tactic: dict[str, Any]) -> dict[str, Any]:
    map_item = find_by_id(state["maps"], tactic["map_id"])
    lineup_ids = [step["lineup_id"] for step in tactic["step_items"] if step.get("lineup_id")]
    utility_types = sorted({lineup["utility_type"] for lineup in state["lineups"] if lineup["id"] in lineup_ids})
    return {
        "id": tactic["id"],
        "slug": tactic["slug"],
        "title": tactic["title"],
        "summary": tactic["summary"],
        "goal": tactic["goal"],
        "phase": tactic["phase"],
        "side": tactic["side"],
        "difficulty": tactic["difficulty"],
        "players": tactic["players"],
        "tags": tactic["tags"],
        "cover_url": tactic["cover_url"],
        "map": {"id": map_item["id"], "name": map_item["name"], "slug": map_item["slug"]},
        "utility_types": utility_types,
        "created_at": tactic["created_at"],
        "status": tactic["status"],
        "featured": tactic["featured"],
    }


def build_lineup_detail(state: dict[str, Any], lineup: dict[str, Any]) -> dict[str, Any]:
    return {
        **lineup,
        "start_point": find_by_id(state["points"], lineup["start_point_id"]),
        "aim_point": find_by_id(state["points"], lineup["aim_point_id"]),
        "land_point": find_by_id(state["points"], lineup["land_point_id"]),
    }


def build_tactic_detail(state: dict[str, Any], tactic: dict[str, Any], user: dict[str, Any] | None = None) -> dict[str, Any]:
    map_item = find_by_id(state["maps"], tactic["map_id"])
    lineups = []
    steps = []
    for step in sorted(tactic["step_items"], key=lambda item: item["order"]):
        lineup_detail = None
        if step.get("lineup_id"):
            lineup = find_by_id(state["lineups"], step["lineup_id"])
            lineup_detail = build_lineup_detail(state, lineup)
            lineups.append(lineup_detail)
        steps.append({**step, "lineup": lineup_detail})

    related = [
        summarize_tactic(state, item)
        for item in state["tactics"]
        if item["map_id"] == tactic["map_id"] and item["id"] != tactic["id"] and item["status"] == "published"
    ][:3]

    favorite_ids = set(user["favorite_ids"]) if user else set()
    return {
        **summarize_tactic(state, tactic),
        "note": tactic["note"],
        "map_layout_url": map_item["layout_url"],
        "map_radar_url": f"/static/assets/maps/radars/{map_item['slug']}-radar.png",
        "map_points": [point for point in state["points"] if point["map_id"] == map_item["id"]],
        "steps": steps,
        "lineups": lineups,
        "routes": tactic.get("routes", []),
        "related": related,
        "is_favorite": tactic["id"] in favorite_ids,
    }


def maybe_get_user(token: str | None = Depends(get_bearer_token)) -> dict[str, Any] | None:
    parsed = parse_token(token)
    if not parsed:
        return None
    role, user_id = parsed
    state = STORE.snapshot()
    return next((item for item in state["users"] if item["id"] == user_id and item["role"] == role), None)


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.post("/api/debug/reset")
def reset_seed() -> dict[str, str]:
    STORE.write_state(build_seed_state())
    return {"status": "reset"}


@app.get("/api/public/home")
def public_home() -> dict[str, Any]:
    state = STORE.snapshot()
    published_tactics = [item for item in state["tactics"] if item["status"] == "published"]
    featured = [summarize_tactic(state, item) for item in published_tactics if item["featured"]][:3]
    latest = [summarize_tactic(state, item) for item in sorted(published_tactics, key=lambda x: x["created_at"], reverse=True)[:4]]
    maps = [summarize_map(state, item) for item in sorted(state["maps"], key=lambda x: x["order"]) if item["status"] == "published"]
    utility_counts: dict[str, int] = {}
    for lineup in state["lineups"]:
        if lineup["status"] != "published":
            continue
        utility_counts[lineup["utility_type"]] = utility_counts.get(lineup["utility_type"], 0) + 1
    utility_quick_links = [{"type": key, "count": value} for key, value in sorted(utility_counts.items())]
    return {
        "featured_maps": maps,
        "featured_tactics": featured,
        "latest_tactics": latest,
        "utility_quick_links": utility_quick_links,
    }


@app.get("/api/public/maps")
def list_maps() -> list[dict[str, Any]]:
    state = STORE.snapshot()
    return [summarize_map(state, item) for item in sorted(state["maps"], key=lambda x: x["order"]) if item["status"] == "published"]


@app.get("/api/public/maps/{slug}")
def get_map_detail(slug: str) -> dict[str, Any]:
    state = STORE.snapshot()
    map_item = find_by_slug(state["maps"], slug)
    tactics = [item for item in state["tactics"] if item["map_id"] == map_item["id"] and item["status"] == "published"]
    lineups = [item for item in state["lineups"] if item["map_id"] == map_item["id"] and item["status"] == "published"]
    filter_options = {
        "sides": sorted({item["side"] for item in tactics}),
        "utility_types": sorted({item["utility_type"] for item in lineups}),
        "goals": sorted({item["goal"] for item in tactics}),
        "phases": sorted({item["phase"] for item in tactics}),
        "difficulties": sorted({item["difficulty"] for item in tactics}),
        "tags": sorted({tag for tactic in tactics for tag in tactic["tags"]}),
    }
    return {
        **summarize_map(state, map_item),
        "points": [item for item in state["points"] if item["map_id"] == map_item["id"]],
        "lineups": [build_lineup_detail(state, item) for item in lineups],
        "filters": filter_options,
        "tactics": [summarize_tactic(state, item) for item in tactics],
    }


@app.get("/api/public/tactics")
def list_tactics(
    map_slug: str | None = None,
    side: str | None = None,
    utility_type: str | None = None,
    goal: str | None = None,
    phase: str | None = None,
    difficulty: str | None = None,
    tag: str | None = None,
    search: str | None = None,
    page: int = Query(default=1, ge=1),
    page_size: int = Query(default=12, ge=1, le=50),
) -> dict[str, Any]:
    state = STORE.snapshot()
    tactics = [item for item in state["tactics"] if item["status"] == "published"]

    if map_slug:
        map_item = find_by_slug(state["maps"], map_slug)
        tactics = [item for item in tactics if item["map_id"] == map_item["id"]]
    if side:
        tactics = [item for item in tactics if item["side"] == side]
    if goal:
        tactics = [item for item in tactics if item["goal"] == goal]
    if phase:
        tactics = [item for item in tactics if item["phase"] == phase]
    if difficulty:
        tactics = [item for item in tactics if item["difficulty"] == difficulty]
    if tag:
        tactics = [item for item in tactics if tag in item["tags"]]
    if search:
        normalized = search.strip().lower()
        tactics = [
            item
            for item in tactics
            if normalized in item["title"].lower()
            or normalized in item["summary"].lower()
            or normalized in " ".join(item["tags"]).lower()
        ]
    if utility_type:
        filtered = []
        for tactic in tactics:
            lineup_ids = [step["lineup_id"] for step in tactic["step_items"] if step.get("lineup_id")]
            lineups = [lineup for lineup in state["lineups"] if lineup["id"] in lineup_ids]
            if any(lineup["utility_type"] == utility_type for lineup in lineups):
                filtered.append(tactic)
        tactics = filtered

    summaries = [summarize_tactic(state, item) for item in sorted(tactics, key=lambda x: x["created_at"], reverse=True)]
    total = len(summaries)
    start = (page - 1) * page_size
    end = start + page_size
    return {"items": summaries[start:end], "total": total, "page": page, "page_size": page_size}


@app.get("/api/public/tactics/{slug}")
def get_tactic_detail(slug: str, user: dict[str, Any] | None = Depends(maybe_get_user)) -> dict[str, Any]:
    state = STORE.snapshot()
    tactic = find_by_slug(state["tactics"], slug)
    if tactic["status"] != "published":
        raise HTTPException(status_code=404, detail="战术不存在")
    return build_tactic_detail(state, tactic, user)


@app.post("/api/public/auth/register")
def register(payload: RegisterRequest) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        if any(user["username"] == payload.username for user in state["users"]):
            raise HTTPException(status_code=400, detail="用户名已存在")
        if any(user["email"] == payload.email for user in state["users"]):
            raise HTTPException(status_code=400, detail="邮箱已存在")
        user = {
            "id": next_id(state, "users"),
            "username": payload.username,
            "email": payload.email,
            "password_hash": hash_password(payload.password),
            "role": "player",
            "favorite_ids": [],
            "recent_tactic_ids": [],
        }
        state["users"].append(user)
        token = create_token("player", user["id"])
        return public_user_payload(user, token)

    return STORE.mutate(mutate)


@app.post("/api/public/auth/login")
def login(payload: LoginRequest) -> dict[str, Any]:
    state = STORE.snapshot()
    user = next(
        (
            item
            for item in state["users"]
            if item["role"] == "player"
            and (item["username"] == payload.username_or_email or item["email"] == payload.username_or_email)
        ),
        None,
    )
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="账号或密码错误")
    return public_user_payload(user, create_token("player", user["id"]))


@app.post("/api/admin/auth/login")
def admin_login(payload: AdminLoginRequest) -> dict[str, Any]:
    state = STORE.snapshot()
    user = next((item for item in state["users"] if item["username"] == payload.username and item["role"] == "admin"), None)
    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status_code=400, detail="后台账号或密码错误")
    return public_user_payload(user, create_token("admin", user["id"]))


@app.get("/api/public/me/favorites")
def get_favorites(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    state = STORE.snapshot()
    favorites = [build_tactic_detail(state, find_by_id(state["tactics"], tactic_id), user) for tactic_id in user["favorite_ids"] if any(item["id"] == tactic_id for item in state["tactics"])]
    recent = [build_tactic_detail(state, find_by_id(state["tactics"], tactic_id), user) for tactic_id in user["recent_tactic_ids"] if any(item["id"] == tactic_id for item in state["tactics"])]
    return {"favorites": favorites, "recent": recent}


@app.post("/api/public/me/favorites/{tactic_id}")
def add_favorite(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        find_by_id(state["tactics"], tactic_id)
        if tactic_id not in db_user["favorite_ids"]:
            db_user["favorite_ids"].insert(0, tactic_id)
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.delete("/api/public/me/favorites/{tactic_id}")
def remove_favorite(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        db_user["favorite_ids"] = [item for item in db_user["favorite_ids"] if item != tactic_id]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/public/me/recent/{tactic_id}")
def track_recent(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        find_by_id(state["tactics"], tactic_id)
        existing = [item for item in db_user["recent_tactic_ids"] if item != tactic_id]
        db_user["recent_tactic_ids"] = [tactic_id, *existing][:8]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.get("/api/admin/dashboard")
def admin_dashboard(_: dict[str, Any] = Depends(get_admin_user)) -> dict[str, int]:
    state = STORE.snapshot()
    return {
        "maps": len(state["maps"]),
        "points": len(state["points"]),
        "lineups": len(state["lineups"]),
        "tactics": len(state["tactics"]),
        "users": len([item for item in state["users"] if item["role"] == "player"]),
        "favorites": sum(len(item["favorite_ids"]) for item in state["users"] if item["role"] == "player"),
    }


@app.get("/api/admin/maps")
def admin_maps(_: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    return [summarize_map(state, item) for item in sorted(state["maps"], key=lambda x: x["order"])]


@app.post("/api/admin/maps")
def create_map(payload: MapPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "maps")
        state["maps"].append(item)
        return summarize_map(state, item)

    return STORE.mutate(mutate)


@app.put("/api/admin/maps/{map_id}")
def update_map(map_id: int, payload: MapPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["maps"], map_id)
        item.update(dump_model(payload))
        return summarize_map(state, item)

    return STORE.mutate(mutate)


@app.get("/api/admin/points")
def admin_points(_: dict[str, Any] = Depends(get_admin_user), map_id: int | None = None) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    points = state["points"]
    if map_id is not None:
        points = [item for item in points if item["map_id"] == map_id]
    return points


@app.post("/api/admin/points")
def create_point(payload: PointPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "points")
        state["points"].append(item)
        return item

    return STORE.mutate(mutate)


@app.put("/api/admin/points/{point_id}")
def update_point(point_id: int, payload: PointPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["points"], point_id)
        item.update(dump_model(payload))
        return item

    return STORE.mutate(mutate)


@app.get("/api/admin/lineups")
def admin_lineups(_: dict[str, Any] = Depends(get_admin_user), map_id: int | None = None) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    lineups = state["lineups"]
    if map_id is not None:
        lineups = [item for item in lineups if item["map_id"] == map_id]
    return [build_lineup_detail(state, item) for item in lineups]


@app.post("/api/admin/lineups")
def create_lineup(payload: LineupPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "lineups")
        state["lineups"].append(item)
        return build_lineup_detail(state, item)

    return STORE.mutate(mutate)


@app.put("/api/admin/lineups/{lineup_id}")
def update_lineup(lineup_id: int, payload: LineupPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["lineups"], lineup_id)
        item.update(dump_model(payload))
        return build_lineup_detail(state, item)

    return STORE.mutate(mutate)


@app.post("/api/admin/lineups/{lineup_id}/archive")
def archive_lineup(lineup_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        lineup = find_by_id(state["lineups"], lineup_id)
        lineup["status"] = "archived"
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.delete("/api/admin/lineups/{lineup_id}")
def delete_lineup(lineup_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        for tactic in state["tactics"]:
            if any(step.get("lineup_id") == lineup_id for step in tactic["step_items"]):
                raise HTTPException(status_code=409, detail="该线路已被战术引用，无法直接删除")
        state["lineups"] = [item for item in state["lineups"] if item["id"] != lineup_id]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.get("/api/admin/tactics")
def admin_tactics(_: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    return sorted(state["tactics"], key=lambda x: x["created_at"], reverse=True)


@app.post("/api/admin/tactics")
def create_tactic(payload: TacticPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "tactics")
        item["created_at"] = datetime.utcnow().isoformat()
        state["tactics"].append(item)
        return item

    return STORE.mutate(mutate)


@app.put("/api/admin/tactics/{tactic_id}")
def update_tactic(tactic_id: int, payload: TacticPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["tactics"], tactic_id)
        original_created_at = item["created_at"]
        item.update(dump_model(payload))
        item["created_at"] = original_created_at
        return item

    return STORE.mutate(mutate)


@app.post("/api/admin/tactics/{tactic_id}/publish")
def publish_tactic(tactic_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        tactic = find_by_id(state["tactics"], tactic_id)
        tactic["status"] = "published"
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/admin/tactics/{tactic_id}/archive")
def archive_tactic(tactic_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        tactic = find_by_id(state["tactics"], tactic_id)
        tactic["status"] = "archived"
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.get("/api/admin/users")
def admin_users(_: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    players = [item for item in state["users"] if item["role"] == "player"]
    return [
        {
            "id": item["id"],
            "username": item["username"],
            "email": item["email"],
            "favorites": len(item["favorite_ids"]),
            "recent": len(item["recent_tactic_ids"]),
        }
        for item in players
    ]


@app.post("/api/admin/assets")
def upload_asset(file: UploadFile = File(...), _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    suffix = Path(file.filename or "upload.bin").suffix
    filename = f"{uuid4().hex}{suffix}"
    target = UPLOAD_DIR / filename
    with target.open("wb") as output:
        shutil.copyfileobj(file.file, output)

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        asset = {
            "id": next_id(state, "assets"),
            "filename": filename,
            "original_name": file.filename,
            "url": f"/static/uploads/{filename}",
            "width": None,
            "height": None,
            "type": file.content_type or "application/octet-stream",
        }
        state["assets"].append(asset)
        return asset

    return STORE.mutate(mutate)


@app.post("/api/admin/assets/batch")
def upload_assets(files: list[UploadFile] = File(...), _: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    results: list[dict[str, Any]] = []
    for file in files:
        suffix = Path(file.filename or "upload.bin").suffix
        filename = f"{uuid4().hex}{suffix}"
        target = UPLOAD_DIR / filename
        with target.open("wb") as output:
            shutil.copyfileobj(file.file, output)

        def mutate(state: dict[str, Any], filename=filename, file=file) -> dict[str, Any]:
            asset = {
                "id": next_id(state, "assets"),
                "filename": filename,
                "original_name": file.filename,
                "url": f"/static/uploads/{filename}",
                "width": None,
                "height": None,
                "type": file.content_type or "application/octet-stream",
            }
            state["assets"].append(asset)
            return asset

        results.append(STORE.mutate(mutate))
    return results


@app.post("/api/admin/assets/import-screenshots")
def import_screenshots(
    map_id: int,
    payload: list[dict[str, Any]],
    _: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, Any]:
    """Batch-import screenshots and associate them with lineups.

    Each payload item: {"asset_url": "/static/uploads/...", "lineup_id": 3}
    Returns summary counts.
    """
    state = STORE.snapshot()
    assigned = 0
    skipped = 0

    for item in payload:
        asset_url = item.get("asset_url")
        lineup_id = item.get("lineup_id")
        if not asset_url or not lineup_id:
            skipped += 1
            continue

        lineup = next((l for l in state["lineups"] if l["id"] == lineup_id and l["map_id"] == map_id), None)
        if not lineup:
            skipped += 1
            continue

        if asset_url not in lineup.setdefault("media", []):
            lineup["media"].append(asset_url)
            assigned += 1
        else:
            skipped += 1

    STORE.write_state(state)
    return {"assigned": assigned, "skipped": skipped}


@app.post("/api/admin/lineups/{lineup_id}/media")
def append_lineup_media(
    lineup_id: int,
    payload: dict[str, str],
    _: dict[str, Any] = Depends(get_admin_user),
) -> dict[str, Any]:
    """Append a media URL to a lineup's media list. Body: {"url": "/static/uploads/..."}"""

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        lineup = find_by_id(state["lineups"], lineup_id)
        url = payload["url"]
        if url not in lineup.setdefault("media", []):
            lineup["media"].append(url)
        return build_lineup_detail(state, lineup)

    return STORE.mutate(mutate)
