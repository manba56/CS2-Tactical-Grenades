from __future__ import annotations

from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import Depends, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse
from fastapi.staticfiles import StaticFiles

from .auth import (
    generate_token,
    hash_password,
    needs_rehash,
    parse_legacy_token,
    public_user_payload,
    verify_password,
    verify_token,
)
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
from .rate_limit import check_rate_limit, get_client_ip
from .storage import SqliteStore

BASE_DIR = Path(__file__).resolve().parent.parent
STORE = SqliteStore(BASE_DIR / "data" / "db.sqlite")
UPLOAD_DIR = BASE_DIR / "app" / "static" / "uploads"
UPLOAD_DIR.mkdir(parents=True, exist_ok=True)

STRICT_PATHS = {"/api/public/auth/login", "/api/public/auth/register", "/api/admin/auth/login"}

app = FastAPI(title="CS2 Tactics API", version="0.1.0")


@app.middleware("http")
async def rate_limit_middleware(request: Request, call_next):
    ip = get_client_ip(request)
    path = request.url.path
    strict = any(path.startswith(p) for p in STRICT_PATHS)
    if not check_rate_limit(ip, strict=strict):
        return Response(
            content='{"detail":"请求太频繁，请稍后再试"}',
            status_code=429,
            media_type="application/json",
        )
    return await call_next(request)

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
        # Production domains — add your actual domain below
        # "https://yourdomain.com",
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
    if key not in state["counters"]:
        state["counters"][key] = 1
    entity_id = state["counters"][key]
    state["counters"][key] += 1
    return entity_id


def get_current_user(token: str = Depends(get_bearer_token)) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    state = STORE.snapshot()

    # New token path: lookup by hash
    for t in state.get("tokens", []):
        if verify_token(token, t["token_hash"]):
            user = next((u for u in state["users"] if u["id"] == t["user_id"]), None)
            if user:
                return user

    # Legacy token path: {role}:{user_id} — will be removed after migration
    parsed = parse_legacy_token(token)
    if parsed:
        role, user_id = parsed
        user = next((u for u in state["users"] if u["id"] == user_id and u["role"] == role), None)
        if user:
            return user

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态失效")


def get_admin_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台权限")
    return user


# ═══════════════════════════════════════════════════════════
# AI 辅助生成（DeepSeek Flash）
# ═══════════════════════════════════════════════════════════

import os, json as _json
from concurrent.futures import ThreadPoolExecutor

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
_ai_executor = ThreadPoolExecutor(max_workers=1)


@app.post("/api/admin/ai/generate")
async def ai_generate(payload: dict[str, Any], _: dict[str, Any] = Depends(get_admin_user)):
    """DeepSeek 生成战术内容——摘要、步骤、注意事项。"""
    if not DEEPSEEK_KEY:
        raise HTTPException(status_code=503, detail="未配置 DEEPSEEK_API_KEY")

    side = payload.get("side","T")
    title = payload.get("title","")
    goal = payload.get("goal","")
    map_name = payload.get("map","")
    phase = payload.get("phase","default")
    diff = payload.get("difficulty","medium")
    players = payload.get("players",3)
    util = payload.get("utility_type","smoke")

    if side == "CT":
        prompt = f"""你是CS2职业教练。根据以下核心信息，编写一套CT方防守战术：

【核心信息】
地图：{map_name}
战术名称：{title}
战术目标：{goal}

【辅助信息】
难度：{diff} | 人数：{players}人 | 阶段：{phase} | 道具：{util}

CT方防守要点：拖延进攻节奏、道具分割路线、反清拿信息、站位轮转等回防

按以下格式输出（只输出内容，不要解释）：
摘要：[80-110字，从CT防守视角概括战术思路]
执行步骤：
1. [CT方操作步骤1]
2. [CT方操作步骤2]
3. [CT方操作步骤3]
注意事项：
1. [防守注意1]
2. [防守注意2]"""
    else:
        prompt = f"""你是CS2职业教练。根据以下核心信息，编写一套T方进攻战术：

【核心信息】
地图：{map_name}
战术名称：{title}
战术目标：{goal}

【辅助信息】
难度：{diff} | 人数：{players}人 | 阶段：{phase} | 道具：{util}

T方进攻要点：主动爆弹、道具开道压制、抢占包点下包、控制时间

按以下格式输出（只输出内容，不要解释）：
摘要：[80-110字，从T方进攻视角概括战术思路]
执行步骤：
1. [T方操作步骤1]
2. [T方操作步骤2]
3. [T方操作步骤3]
注意事项：
1. [进攻注意1]
2. [进攻注意2]"""

    def _call():
        import urllib.request, re
        req = urllib.request.Request(
            "https://api.deepseek.com/chat/completions",
            data=_json.dumps({"model":"deepseek-chat","messages":[{"role":"user","content":prompt}],"max_tokens":600,"temperature":0.7}).encode(),
            headers={"Authorization":f"Bearer {DEEPSEEK_KEY}","Content-Type":"application/json"},
        )
        resp = urllib.request.urlopen(req, timeout=30)
        text = _json.loads(resp.read())["choices"][0]["message"]["content"].strip()

        def _extract(label, text):
            m = re.search(rf'{label}[：:]\s*\n?(.+?)(?=\n\S+[：:]|\Z)', text, re.S)
            return m.group(1).strip() if m else ""
        def _lines(label, text):
            part = _extract(label, text)
            return '\n'.join([s.strip().lstrip('1234567890.、)。） ') for s in part.split('\n') if s.strip()])

        return {
            "title": _extract("标题", text),
            "slug": _extract("Slug", text),
            "goal": _extract("目标", text),
            "summary": _extract("摘要", text),
            "steps": _lines("执行步骤", text),
            "note": _lines("注意事项", text),
        }

    try:
        import asyncio
        result = await asyncio.get_event_loop().run_in_executor(_ai_executor, _call)
        return result
    except Exception as e:
        raise HTTPException(status_code=500, detail=f"AI 调用失败: {str(e)}")


@app.get("/api/admin/db/download")
def download_database(_: dict[str, Any] = Depends(get_admin_user)):
    """Download the SQLite database (admin only, backup)."""
    from fastapi.responses import FileResponse

    db_path = BASE_DIR / "data" / "db.sqlite"
    if not db_path.exists():
        raise HTTPException(status_code=404, detail="数据库文件不存在")
    return FileResponse(str(db_path), media_type="application/octet-stream", filename="db.sqlite")


# ═══════════════════════════════════════════════════════════
# GitHub Webhook — auto-deploy on push
# ═══════════════════════════════════════════════════════════

@app.post("/api/webhook/deploy")
async def webhook_deploy(request: Request):
    """GitHub push → auto git pull + deploy (async, responds immediately)."""
    import subprocess

    try:
        body = await request.json()
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    ref = body.get("ref", "")
    if "main" not in ref and "master" not in ref:
        return {"status": "skipped", "ref": ref}

    # Fire deploy.sh in background, output goes to log file
    log_path = BASE_DIR.parent / "deploy.log"
    subprocess.Popen(
        [str(BASE_DIR.parent / "deploy.sh")],
        cwd=str(BASE_DIR.parent),
        stdout=open(str(log_path), "a"), stderr=open(str(log_path), "a"),
        start_new_session=True,
    )

    return {"status": "deploying", "ref": ref}
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
            try:
                lineup = find_by_id(state["lineups"], step["lineup_id"])
                lineup_detail = build_lineup_detail(state, lineup)
                lineups.append(lineup_detail)
            except HTTPException:
                pass  # lineup was deleted, skip gracefully
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
        "screenshots": tactic.get("screenshots", []),
        "video_url": tactic.get("video_url", ""),
        "related": related,
        "is_favorite": tactic["id"] in favorite_ids,
    }


def maybe_get_user(token: str | None = Depends(get_bearer_token)) -> dict[str, Any] | None:
    if not token:
        return None

    state = STORE.snapshot()

    # New token path: lookup by hash
    for t in state.get("tokens", []):
        if verify_token(token, t["token_hash"]):
            return next((u for u in state["users"] if u["id"] == t["user_id"]), None)

    # Legacy token path
    parsed = parse_legacy_token(token)
    if parsed:
        role, user_id = parsed
        return next((u for u in state["users"] if u["id"] == user_id and u["role"] == role), None)

    return None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}




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
    collections = []
    for col in state.get("collections", []):
        if col["status"] != "published":
            continue
        tactic_ids = col.get("tactic_ids", [])
        col_tactics = [summarize_tactic(state, t) for t in published_tactics if t["id"] in tactic_ids]
        if col_tactics:
            collections.append({**col, "tactic_count": len(col_tactics)})
    collections = sorted(collections, key=lambda c: c.get("created_at", ""), reverse=True)[:4]
    return {
        "featured_maps": maps,
        "featured_tactics": featured,
        "latest_tactics": latest,
        "utility_quick_links": utility_quick_links,
        "collections": collections,
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
        filtered = []
        for item in tactics:
            if (
                normalized in item["title"].lower()
                or normalized in item["summary"].lower()
                or normalized in " ".join(item["tags"]).lower()
                or normalized in item["goal"].lower()
            ):
                filtered.append(item)
                continue
            # Also search lineup utility type names
            lineup_ids = [step["lineup_id"] for step in item["step_items"] if step.get("lineup_id")]
            util_names = [
                lineup["utility_type"]
                for lineup in state["lineups"]
                if lineup["id"] in lineup_ids
            ]
            if any(normalized in name for name in util_names):
                filtered.append(item)
        tactics = filtered
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


# ── Default account anomaly detection ──────────────────────────
DEFAULT_ACCOUNTS = {"admin", "demo"}
MAX_FAILED_ATTEMPTS = 5
LOCKOUT_WINDOW_MINUTES = 15


def _check_anomaly(state: dict[str, Any], username: str, ip: str) -> None:
    """Block default accounts after too many failed logins."""
    if username not in DEFAULT_ACCOUNTS:
        return
    now_ts = datetime.now(timezone.utc).isoformat()
    cutoff = (datetime.now(timezone.utc) - timedelta(minutes=LOCKOUT_WINDOW_MINUTES)).isoformat()
    recent_fails = [
        e for e in state.get("login_log", [])
        if e["username"] == username and not e["success"] and e["created_at"] > cutoff
    ]
    if len(recent_fails) >= MAX_FAILED_ATTEMPTS:
        raise HTTPException(
            status_code=429,
            detail=f"账号 {username} 因多次登录失败已临时锁定，请 {LOCKOUT_WINDOW_MINUTES} 分钟后重试",
        )


def _record_login(
    state: dict[str, Any], user_id: int | None, username: str, ip: str, success: bool
) -> None:
    entry = {
        "id": next_id(state, "login_log"),
        "user_id": user_id,
        "username": username,
        "ip": ip,
        "success": int(success),
        "created_at": datetime.now(timezone.utc).isoformat(),
    }
    state.setdefault("login_log", []).append(entry)


def _issue_token(state: dict[str, Any], user: dict[str, Any]) -> str:
    """Generate a random token, store its hash, return the raw token."""
    raw, token_hash = generate_token()
    state.setdefault("tokens", []).append({
        "id": next_id(state, "tokens"),
        "user_id": user["id"],
        "token_hash": token_hash,
        "created_at": datetime.now(timezone.utc).isoformat(),
        "expires_at": None,
    })
    return raw


@app.post("/api/public/auth/register")
def register(payload: RegisterRequest, request: Request) -> dict[str, Any]:
    ip = get_client_ip(request)

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        if any(u["username"] == payload.username for u in state["users"]):
            raise HTTPException(status_code=400, detail="用户名已存在")
        if any(u["email"] == payload.email for u in state["users"]):
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
        token = _issue_token(state, user)
        _record_login(state, user["id"], payload.username, ip, True)
        return public_user_payload(user, token)

    return STORE.mutate(mutate)


@app.post("/api/public/auth/login")
def login(payload: LoginRequest, request: Request) -> dict[str, Any]:
    ip = get_client_ip(request)
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

    username = user["username"] if user else payload.username_or_email

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        u = next(
            (item for item in state["users"]
             if item["role"] == "player"
             and (item["username"] == payload.username_or_email or item["email"] == payload.username_or_email)),
            None,
        )
        if not u:
            _check_anomaly(state, username, ip)
            _record_login(state, None, username, ip, False)
            raise HTTPException(status_code=400, detail="账号或密码错误")

        if not verify_password(payload.password, u["password_hash"]):
            _check_anomaly(state, username, ip)
            _record_login(state, u["id"], username, ip, False)
            raise HTTPException(status_code=400, detail="账号或密码错误")

        # Auto-upgrade legacy password hash
        if needs_rehash(u["password_hash"]):
            u["password_hash"] = hash_password(payload.password)

        token = _issue_token(state, u)
        _record_login(state, u["id"], username, ip, True)
        return public_user_payload(u, token)

    return STORE.mutate(mutate)


@app.post("/api/admin/auth/login")
def admin_login(payload: AdminLoginRequest, request: Request) -> dict[str, Any]:
    ip = get_client_ip(request)
    state = STORE.snapshot()
    user = next((item for item in state["users"] if item["username"] == payload.username and item["role"] == "admin"), None)

    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        u = next((item for item in state["users"] if item["username"] == payload.username and item["role"] == "admin"), None)
        if not u:
            _check_anomaly(state, payload.username, ip)
            _record_login(state, None, payload.username, ip, False)
            raise HTTPException(status_code=400, detail="后台账号或密码错误")

        if not verify_password(payload.password, u["password_hash"]):
            _check_anomaly(state, payload.username, ip)
            _record_login(state, u["id"], payload.username, ip, False)
            raise HTTPException(status_code=400, detail="后台账号或密码错误")

        if needs_rehash(u["password_hash"]):
            u["password_hash"] = hash_password(payload.password)

        token = _issue_token(state, u)
        _record_login(state, u["id"], payload.username, ip, True)
        return public_user_payload(u, token)

    return STORE.mutate(mutate)


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


# ═══════════════════════════════════════════════════════════
# Collections
# ═══════════════════════════════════════════════════════════

@app.get("/api/public/collections")
def list_collections() -> list[dict[str, Any]]:
    state = STORE.snapshot()
    result = []
    for col in state.get("collections", []):
        if col["status"] != "published":
            continue
        tactic_ids = col.get("tactic_ids", [])
        tactics = [summarize_tactic(state, t) for t in state["tactics"] if t["id"] in tactic_ids]
        result.append({**col, "tactics": tactics})
    return sorted(result, key=lambda c: c.get("created_at", ""), reverse=True)


@app.get("/api/public/collections/{slug}")
def get_collection(slug: str) -> dict[str, Any]:
    state = STORE.snapshot()
    col = find_by_slug(state.get("collections", []), slug)
    tactic_ids = col.get("tactic_ids", [])
    tactics = [build_tactic_detail(state, t) for t in state["tactics"] if t["id"] in tactic_ids]
    return {**col, "tactics": tactics}


# ═══════════════════════════════════════════════════════════
# Admin Collections
# ═══════════════════════════════════════════════════════════

@app.get("/api/admin/collections")
def admin_collections(_: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    return state.get("collections", [])


@app.post("/api/admin/collections")
def create_collection(payload: dict[str, Any], _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dict(payload)
        item["id"] = next_id(state, "collections")
        item["created_at"] = item.get("created_at", datetime.now(timezone.utc).isoformat())
        item["slug"] = _auto_slug(payload.get("slug", ""), payload.get("title", ""), item["id"])
        state.setdefault("collections", []).append(item)
        return item

    return STORE.mutate(mutate)


@app.put("/api/admin/collections/{col_id}")
def update_collection(col_id: int, payload: dict[str, Any], _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["collections"], col_id)
        item.update(payload)
        item["slug"] = _auto_slug(payload.get("slug", ""), payload.get("title", ""), item["id"])
        return item

    return STORE.mutate(mutate)


@app.delete("/api/admin/collections/{col_id}")
def delete_collection(col_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        state["collections"] = [c for c in state["collections"] if c["id"] != col_id]
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


def _auto_slug(payload_slug: str, payload_title: str, tactic_id: int) -> str:
    if payload_slug.strip():
        return payload_slug.strip()
    if payload_title.strip():
        import re as _re
        base = _re.sub(r"[^\w\-]", "-", payload_title.strip().lower())
        base = _re.sub(r"-{2,}", "-", base).strip("-")
        return f"{base}-{tactic_id}"
    return f"tactic-{tactic_id}"


@app.post("/api/admin/tactics")
def create_tactic(payload: TacticPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "tactics")
        item["slug"] = _auto_slug(payload.slug, payload.title, item["id"])
        item["created_at"] = datetime.now(timezone.utc).isoformat()
        state["tactics"].append(item)
        return item

    return STORE.mutate(mutate)


@app.put("/api/admin/tactics/{tactic_id}")
def update_tactic(tactic_id: int, payload: TacticPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["tactics"], tactic_id)
        original_created_at = item["created_at"]
        item.update(dump_model(payload))
        item["slug"] = _auto_slug(payload.slug, payload.title, item["id"])
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


ALLOWED_EXTENSIONS = {".jpg", ".jpeg", ".png", ".gif", ".webp", ".svg"}
ALLOWED_MIMES = {"image/jpeg", "image/png", "image/gif", "image/webp", "image/svg+xml"}
MAX_UPLOAD_BYTES = 20 * 1024 * 1024  # 20 MB


@app.post("/api/admin/assets")
def upload_asset(file: UploadFile = File(...), _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    suffix = Path(file.filename or "upload.bin").suffix.lower()
    mime = (file.content_type or "").lower()

    if suffix not in ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {suffix}，仅允许图片格式")
    if mime and mime not in ALLOWED_MIMES:
        raise HTTPException(status_code=400, detail=f"不支持的文件类型: {mime}，仅允许图片格式")

    # Read into memory to enforce size limit
    data = file.file.read()
    if len(data) > MAX_UPLOAD_BYTES:
        raise HTTPException(status_code=400, detail="文件过大，最大允许 20 MB")
    if len(data) == 0:
        raise HTTPException(status_code=400, detail="文件为空")

    filename = f"{uuid4().hex}{suffix}"
    target = UPLOAD_DIR / filename
    with target.open("wb") as output:
        output.write(data)

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


