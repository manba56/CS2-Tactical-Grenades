from __future__ import annotations

import hashlib
import hmac
import json as _json
import os
import secrets
import shutil
import subprocess
from datetime import datetime, timedelta, timezone
from pathlib import Path
from typing import Any
from uuid import uuid4

from fastapi import BackgroundTasks, Depends, FastAPI, File, Header, HTTPException, Query, Request, Response, UploadFile, status
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
    ClipJobPayload,
    LineupPayload,
    LocalSyncPayload,
    LoginRequest,
    MapPayload,
    PersonalBoardPayload,
    PointPayload,
    ProgressPayload,
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
CLIP_SOURCE_DIR = UPLOAD_DIR / "clips" / "sources"
CLIP_OUTPUT_DIR = UPLOAD_DIR / "clips" / "outputs"
CLIP_WORK_DIR = UPLOAD_DIR / "clips" / "work"
for _clip_dir in (CLIP_SOURCE_DIR, CLIP_OUTPUT_DIR, CLIP_WORK_DIR):
    _clip_dir.mkdir(parents=True, exist_ok=True)

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
        "http://127.0.0.1:5176",
        "http://localhost:5176",
        "http://127.0.0.1:5177",
        "http://localhost:5177",
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


VALID_PROGRESS_STATUSES = {"practicing", "mastered", "match_ready"}


def normalize_user_personal_fields(user: dict[str, Any]) -> dict[str, Any]:
    user.setdefault("favorite_ids", [])
    user.setdefault("recent_tactic_ids", [])
    user.setdefault("favorite_lineup_ids", [])
    user.setdefault("lineup_progress", {})
    user.setdefault("tactic_progress", {})
    if user["favorite_lineup_ids"] is None:
        user["favorite_lineup_ids"] = []
    if user["lineup_progress"] is None:
        user["lineup_progress"] = {}
    if user["tactic_progress"] is None:
        user["tactic_progress"] = {}
    return user


def clean_progress(progress: dict[str, Any]) -> dict[str, str]:
    return {
        str(key): value
        for key, value in progress.items()
        if value in VALID_PROGRESS_STATUSES
    }


def utc_now() -> datetime:
    return datetime.now(timezone.utc)


def utc_iso(dt: datetime) -> str:
    return dt.astimezone(timezone.utc).isoformat()


def parse_datetime(value: str | None) -> datetime | None:
    if not value:
        return None
    try:
        return datetime.fromisoformat(value.replace("Z", "+00:00"))
    except ValueError:
        return None


def is_token_expired(token_row: dict[str, Any], now: datetime | None = None) -> bool:
    expires_at = parse_datetime(token_row.get("expires_at"))
    return bool(expires_at and expires_at <= (now or utc_now()))


def revoke_token(raw_token: str) -> bool:
    removed = False

    def mutate(state: dict[str, Any]) -> dict[str, bool]:
        nonlocal removed
        kept = []
        for item in state.get("tokens", []):
            if verify_token(raw_token, item["token_hash"]):
                removed = True
                continue
            kept.append(item)
        state["tokens"] = kept
        return {"revoked": removed}

    STORE.mutate(mutate)
    return removed


def get_current_user(token: str = Depends(get_bearer_token)) -> dict[str, Any]:
    if not token:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="未登录")

    state = STORE.snapshot()

    # New token path: lookup by hash
    expired = False
    for t in state.get("tokens", []):
        if verify_token(token, t["token_hash"]):
            if is_token_expired(t):
                expired = True
                break
            user = next((u for u in state["users"] if u["id"] == t["user_id"]), None)
            if user:
                return normalize_user_personal_fields(user)
    if expired:
        revoke_token(token)
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录已过期，请重新登录")

    # Legacy token path: {role}:{user_id} — will be removed after migration
    parsed = parse_legacy_token(token)
    if parsed:
        role, user_id = parsed
        user = next((u for u in state["users"] if u["id"] == user_id and u["role"] == role), None)
        if user:
            return normalize_user_personal_fields(user)

    raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="登录状态失效")


def get_admin_user(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    if user["role"] != "admin":
        raise HTTPException(status_code=status.HTTP_403_FORBIDDEN, detail="无后台权限")
    return user


# ═══════════════════════════════════════════════════════════
# AI 辅助生成（DeepSeek Flash）
# ═══════════════════════════════════════════════════════════

from concurrent.futures import ThreadPoolExecutor

DEEPSEEK_KEY = os.getenv("DEEPSEEK_API_KEY", "")
DEPLOY_WEBHOOK_SECRET = os.getenv("DEPLOY_WEBHOOK_SECRET") or os.getenv("GITHUB_WEBHOOK_SECRET")
TOKEN_TTL_DAYS = int(os.getenv("TOKEN_TTL_DAYS", "7"))
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

def verify_deploy_webhook(raw_body: bytes, signature: str | None, deploy_secret: str | None) -> None:
    if not DEPLOY_WEBHOOK_SECRET:
        raise HTTPException(status_code=503, detail="Deploy webhook is not configured")

    if signature:
        prefix = "sha256="
        expected = prefix + hmac.new(
            DEPLOY_WEBHOOK_SECRET.encode("utf-8"),
            raw_body,
            hashlib.sha256,
        ).hexdigest()
        if signature.startswith(prefix) and secrets.compare_digest(signature, expected):
            return

    if deploy_secret and secrets.compare_digest(deploy_secret, DEPLOY_WEBHOOK_SECRET):
        return

    raise HTTPException(status_code=401, detail="Invalid deploy webhook signature")


DEPLOY_IN_PROGRESS = False


def _append_deploy_log(message: str) -> None:
    log_path = BASE_DIR.parent / "deploy.log"
    timestamp = datetime.now().strftime("%Y-%m-%d %H:%M:%S")
    try:
        with log_path.open("a", encoding="utf-8") as log_file:
            log_file.write(f"[{timestamp}] {message}\n")
    except Exception:
        pass


def start_deploy_process(ref: str) -> None:
    global DEPLOY_IN_PROGRESS
    if DEPLOY_IN_PROGRESS:
        _append_deploy_log(f"Deploy already running, skipped duplicate webhook: ref={ref}")
        return

    DEPLOY_IN_PROGRESS = True
    deploy_script = BASE_DIR.parent / "deploy.sh"
    log_path = BASE_DIR.parent / "deploy.log"
    try:
        if not deploy_script.exists():
            _append_deploy_log(f"Deploy script not found: {deploy_script}")
            return

        deploy_runner = Path(os.getenv("DEPLOY_RUNNER", "/usr/local/bin/cs2-deploy-run"))
        if deploy_runner.exists():
            running_as_root = hasattr(os, "geteuid") and os.geteuid() == 0
            command = [str(deploy_runner)] if running_as_root else ["sudo", "-n", str(deploy_runner)]
            subprocess.Popen(
                command,
                cwd=str(BASE_DIR.parent),
                stdin=subprocess.DEVNULL,
                stdout=subprocess.DEVNULL,
                stderr=subprocess.DEVNULL,
                close_fds=True,
                start_new_session=True,
            )
        else:
            log_file = open(str(log_path), "a", encoding="utf-8")
            subprocess.Popen(
                ["bash", str(deploy_script)],
                cwd=str(BASE_DIR.parent),
                stdin=subprocess.DEVNULL,
                stdout=log_file,
                stderr=log_file,
                close_fds=True,
                start_new_session=True,
            )
        _append_deploy_log(f"Deploy process started from webhook: ref={ref}")
    except Exception as exc:
        _append_deploy_log(f"Failed to start deploy script: {exc}")
    finally:
        DEPLOY_IN_PROGRESS = False


@app.post("/api/webhook/deploy")
async def webhook_deploy(request: Request, background_tasks: BackgroundTasks):
    """GitHub push → auto git pull + deploy (async, responds immediately)."""
    raw_body = await request.body()
    verify_deploy_webhook(
        raw_body,
        request.headers.get("x-hub-signature-256"),
        request.headers.get("x-deploy-secret"),
    )

    try:
        body = _json.loads(raw_body.decode("utf-8"))
    except Exception:
        raise HTTPException(status_code=400, detail="Invalid JSON")

    ref = body.get("ref", "")
    if "main" not in ref and "master" not in ref:
        return {"status": "skipped", "ref": ref}

    log_path = BASE_DIR.parent / "deploy.log"
    background_tasks.add_task(start_deploy_process, ref)
    return {"status": "accepted", "ref": ref, "log": str(log_path)}
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
        "lineup_ids": lineup_ids,
    }


def build_lineup_detail(state: dict[str, Any], lineup: dict[str, Any]) -> dict[str, Any]:
    map_item = find_by_id(state["maps"], lineup["map_id"])
    return {
        **lineup,
        "map": {"id": map_item["id"], "name": map_item["name"], "slug": map_item["slug"]},
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
            if is_token_expired(t):
                revoke_token(token)
                return None
            user = next((u for u in state["users"] if u["id"] == t["user_id"]), None)
            return normalize_user_personal_fields(user) if user else None

    # Legacy token path
    parsed = parse_legacy_token(token)
    if parsed:
        role, user_id = parsed
        return next((u for u in state["users"] if u["id"] == user_id and u["role"] == role), None)

    return None


@app.get("/api/health")
def health() -> dict[str, str]:
    return {"status": "ok"}


@app.get("/sitemap.xml")
def sitemap() -> Response:
    state = STORE.snapshot()
    base_url = os.getenv("SITE_BASE_URL", "https://1338089.xyz").rstrip("/")
    urls = ["/", "/maps"]
    urls.extend(f"/maps/{item['slug']}" for item in state["maps"] if item["status"] == "published")
    urls.extend(f"/tactics/{item['slug']}" for item in state["tactics"] if item["status"] == "published")
    urls.extend(f"/collections/{item['slug']}" for item in state.get("collections", []) if item["status"] == "published")
    body = "\n".join(
        [
            '<?xml version="1.0" encoding="UTF-8"?>',
            '<urlset xmlns="http://www.sitemaps.org/schemas/sitemap/0.9">',
            *[f"  <url><loc>{base_url}{path}</loc></url>" for path in urls],
            "</urlset>",
        ]
    )
    return Response(content=body, media_type="application/xml")




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
    now = utc_now()
    state.setdefault("tokens", []).append({
        "id": next_id(state, "tokens"),
        "user_id": user["id"],
        "token_hash": token_hash,
        "created_at": utc_iso(now),
        "expires_at": utc_iso(now + timedelta(days=TOKEN_TTL_DAYS)),
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
            "favorite_lineup_ids": [],
            "lineup_progress": {},
            "tactic_progress": {},
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


@app.post("/api/public/auth/logout")
def logout(token: str = Depends(get_bearer_token)) -> dict[str, str]:
    if token:
        revoke_token(token)
    return {"status": "ok"}


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


@app.post("/api/admin/auth/logout")
def admin_logout(token: str = Depends(get_bearer_token)) -> dict[str, str]:
    if token:
        revoke_token(token)
    return {"status": "ok"}


@app.get("/api/public/me/favorites")
def get_favorites(user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    state = STORE.snapshot()
    user = normalize_user_personal_fields(user)
    favorites = [build_tactic_detail(state, find_by_id(state["tactics"], tactic_id), user) for tactic_id in user["favorite_ids"] if any(item["id"] == tactic_id for item in state["tactics"])]
    recent = [build_tactic_detail(state, find_by_id(state["tactics"], tactic_id), user) for tactic_id in user["recent_tactic_ids"] if any(item["id"] == tactic_id for item in state["tactics"])]
    favorite_lineups = [
        build_lineup_detail(state, find_by_id(state["lineups"], lineup_id))
        for lineup_id in user["favorite_lineup_ids"]
        if any(item["id"] == lineup_id and item["status"] == "published" for item in state["lineups"])
    ]
    return {
        "favorites": favorites,
        "recent": recent,
        "favorite_lineups": favorite_lineups,
        "lineup_progress": clean_progress(user.get("lineup_progress", {})),
        "tactic_progress": clean_progress(user.get("tactic_progress", {})),
    }


def build_personal_board_detail(state: dict[str, Any], board: dict[str, Any]) -> dict[str, Any]:
    map_item = find_by_id(state["maps"], board["map_id"])
    return {
        **board,
        "map": {"id": map_item["id"], "name": map_item["name"], "slug": map_item["slug"]},
        "map_radar_url": f"/static/assets/maps/radars/{map_item['slug']}-radar.png",
        "map_layout_url": map_item["layout_url"],
    }


@app.get("/api/public/me/boards")
def list_personal_boards(user: dict[str, Any] = Depends(get_current_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    boards = [
        build_personal_board_detail(state, item)
        for item in state.get("personal_boards", [])
        if item["user_id"] == user["id"]
    ]
    return sorted(boards, key=lambda item: item.get("updated_at") or item.get("created_at") or "", reverse=True)


@app.post("/api/public/me/boards")
def create_personal_board(payload: PersonalBoardPayload, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        find_by_id(state["maps"], payload.map_id)
        now = utc_iso(utc_now())
        item = dump_model(payload)
        item.update({
            "id": next_id(state, "personal_boards"),
            "user_id": user["id"],
            "created_at": now,
            "updated_at": now,
        })
        state.setdefault("personal_boards", []).append(item)
        return build_personal_board_detail(state, item)

    return STORE.mutate(mutate)


@app.put("/api/public/me/boards/{board_id}")
def update_personal_board(board_id: int, payload: PersonalBoardPayload, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        find_by_id(state["maps"], payload.map_id)
        item = find_by_id(state.get("personal_boards", []), board_id)
        if item["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="资源不存在")
        original_created_at = item["created_at"]
        item.update(dump_model(payload))
        item["user_id"] = user["id"]
        item["created_at"] = original_created_at
        item["updated_at"] = utc_iso(utc_now())
        return build_personal_board_detail(state, item)

    return STORE.mutate(mutate)


@app.delete("/api/public/me/boards/{board_id}")
def delete_personal_board(board_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        item = find_by_id(state.get("personal_boards", []), board_id)
        if item["user_id"] != user["id"]:
            raise HTTPException(status_code=404, detail="资源不存在")
        state["personal_boards"] = [board for board in state.get("personal_boards", []) if board["id"] != board_id]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/public/me/favorites/{tactic_id}")
def add_favorite(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        normalize_user_personal_fields(db_user)
        find_by_id(state["tactics"], tactic_id)
        if tactic_id not in db_user["favorite_ids"]:
            db_user["favorite_ids"].insert(0, tactic_id)
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.delete("/api/public/me/favorites/{tactic_id}")
def remove_favorite(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        normalize_user_personal_fields(db_user)
        db_user["favorite_ids"] = [item for item in db_user["favorite_ids"] if item != tactic_id]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/public/me/recent/{tactic_id}")
def track_recent(tactic_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = find_by_id(state["users"], user["id"])
        normalize_user_personal_fields(db_user)
        find_by_id(state["tactics"], tactic_id)
        existing = [item for item in db_user["recent_tactic_ids"] if item != tactic_id]
        db_user["recent_tactic_ids"] = [tactic_id, *existing][:8]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/public/me/lineups/favorites/{lineup_id}")
def add_lineup_favorite(lineup_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = normalize_user_personal_fields(find_by_id(state["users"], user["id"]))
        find_by_id(state["lineups"], lineup_id)
        if lineup_id not in db_user["favorite_lineup_ids"]:
            db_user["favorite_lineup_ids"].insert(0, lineup_id)
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.delete("/api/public/me/lineups/favorites/{lineup_id}")
def remove_lineup_favorite(lineup_id: int, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = normalize_user_personal_fields(find_by_id(state["users"], user["id"]))
        db_user["favorite_lineup_ids"] = [item for item in db_user["favorite_lineup_ids"] if item != lineup_id]
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.put("/api/public/me/progress/tactics/{tactic_id}")
def set_tactic_progress(tactic_id: int, payload: ProgressPayload, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = normalize_user_personal_fields(find_by_id(state["users"], user["id"]))
        find_by_id(state["tactics"], tactic_id)
        key = str(tactic_id)
        if payload.status:
            db_user["tactic_progress"][key] = payload.status
        else:
            db_user["tactic_progress"].pop(key, None)
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.put("/api/public/me/progress/lineups/{lineup_id}")
def set_lineup_progress(lineup_id: int, payload: ProgressPayload, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = normalize_user_personal_fields(find_by_id(state["users"], user["id"]))
        find_by_id(state["lineups"], lineup_id)
        key = str(lineup_id)
        if payload.status:
            db_user["lineup_progress"][key] = payload.status
        else:
            db_user["lineup_progress"].pop(key, None)
        return {"status": "ok"}

    return STORE.mutate(mutate)


@app.post("/api/public/me/sync-local")
def sync_local_personal_data(payload: LocalSyncPayload, user: dict[str, Any] = Depends(get_current_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        db_user = normalize_user_personal_fields(find_by_id(state["users"], user["id"]))
        valid_lineup_ids = {item["id"] for item in state["lineups"]}
        valid_tactic_ids = {item["id"] for item in state["tactics"]}

        for lineup_id in payload.favorite_lineup_ids:
            if lineup_id in valid_lineup_ids and lineup_id not in db_user["favorite_lineup_ids"]:
                db_user["favorite_lineup_ids"].insert(0, lineup_id)

        for raw_id, progress in payload.lineup_progress.items():
            try:
                lineup_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if lineup_id in valid_lineup_ids:
                db_user["lineup_progress"][str(lineup_id)] = progress

        for raw_id, progress in payload.tactic_progress.items():
            try:
                tactic_id = int(raw_id)
            except (TypeError, ValueError):
                continue
            if tactic_id in valid_tactic_ids:
                db_user["tactic_progress"][str(tactic_id)] = progress

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


CLIP_ALLOWED_EXTENSIONS = {".mp4", ".mov", ".mkv", ".webm"}
CLIP_ALLOWED_MIMES = {
    "video/mp4",
    "video/quicktime",
    "video/x-matroska",
    "video/webm",
    "application/octet-stream",
}
MAX_CLIP_UPLOAD_BYTES = 2 * 1024 * 1024 * 1024  # 2 GB
CLIP_STATUSES = {"draft", "rendering", "ready", "failed"}


def _clip_public_url(folder: str, filename: str) -> str:
    return f"/static/uploads/clips/{folder}/{filename}"


def _clip_file_from_url(url: str, folder: str) -> Path:
    prefix = f"/static/uploads/clips/{folder}/"
    if not url.startswith(prefix):
        raise HTTPException(status_code=400, detail="视频地址必须来自剪辑中心上传目录")
    name = Path(url[len(prefix):]).name
    path = (UPLOAD_DIR / "clips" / folder / name).resolve()
    root = (UPLOAD_DIR / "clips" / folder).resolve()
    if root not in path.parents or not path.exists() or not path.is_file():
        raise HTTPException(status_code=404, detail="视频文件不存在")
    return path


def _validate_clip_payload(state: dict[str, Any], item: dict[str, Any]) -> None:
    title = (item.get("title") or "").strip()
    if not title:
        raise HTTPException(status_code=400, detail="剪辑标题不能为空")
    if item.get("lineup_id") is not None:
        find_by_id(state["lineups"], int(item["lineup_id"]))
    _clip_file_from_url(item.get("source_url", ""), "sources")
    segments = item.get("segments") or []
    if not segments:
        raise HTTPException(status_code=400, detail="至少需要一个剪辑片段")
    for idx, segment in enumerate(segments, start=1):
        start = float(segment.get("start_seconds", 0))
        end = float(segment.get("end_seconds", 0))
        if start < 0:
            raise HTTPException(status_code=400, detail=f"片段 {idx} 的开始时间不能小于 0")
        if end <= start:
            raise HTTPException(status_code=400, detail=f"片段 {idx} 的结束时间必须大于开始时间")
        duration = end - start
        focus_point = segment.get("focus_point_seconds")
        if focus_point is not None and float(focus_point) > duration:
            raise HTTPException(status_code=400, detail=f"Segment {idx} focus point exceeds segment duration")
        focus_pause = float(segment.get("focus_pause_seconds", 1.0))
        if focus_pause < 0.2 or focus_pause > 5:
            raise HTTPException(status_code=400, detail=f"Segment {idx} focus pause must be between 0.2 and 5 seconds")
        if focus_point is None:
            focus_start = segment.get("focus_start_seconds")
            focus_end = segment.get("focus_end_seconds")
            if focus_start is not None and float(focus_start) > duration:
                raise HTTPException(status_code=400, detail=f"Segment {idx} focus start exceeds segment duration")
            if focus_end is not None and float(focus_end) > duration:
                raise HTTPException(status_code=400, detail=f"Segment {idx} focus end exceeds segment duration")
            if focus_start is not None and focus_end is not None and float(focus_end) <= float(focus_start):
                raise HTTPException(status_code=400, detail=f"Segment {idx} focus end must be greater than focus start")
        focus_width = float(segment.get("focus_width", 0.24))
        focus_height = float(segment.get("focus_height", 0.24))
        focus_x = float(segment.get("focus_x", 0.38))
        focus_y = float(segment.get("focus_y", 0.38))
        if focus_x + focus_width > 1.0001 or focus_y + focus_height > 1.0001:
            raise HTTPException(status_code=400, detail=f"Segment {idx} focus region exceeds the frame")
    if item.get("template_type") != "lineup_tutorial":
        raise HTTPException(status_code=400, detail="暂时只支持道具教学模板")


def _normalize_clip_job(item: dict[str, Any], state: dict[str, Any] | None = None) -> dict[str, Any]:
    result = dict(item)
    result.setdefault("segments", [])
    result.setdefault("template_type", "lineup_tutorial")
    result.setdefault("status", "draft")
    result.setdefault("output_url", "")
    result.setdefault("output_filename", "")
    result.setdefault("error", "")
    lineup_id = result.get("lineup_id")
    result["lineup"] = None
    if state is not None and lineup_id is not None:
        try:
            result["lineup"] = build_lineup_detail(state, find_by_id(state["lineups"], int(lineup_id)))
        except HTTPException:
            result["lineup"] = None
    return result


def _format_ass_time(seconds: float) -> str:
    seconds = max(0, float(seconds))
    hours = int(seconds // 3600)
    minutes = int((seconds % 3600) // 60)
    secs = int(seconds % 60)
    centis = int(round((seconds - int(seconds)) * 100))
    if centis >= 100:
        secs += 1
        centis = 0
    return f"{hours}:{minutes:02d}:{secs:02d}.{centis:02d}"


def _ass_escape(text: str) -> str:
    return (
        (text or "")
        .replace("{", "\\{")
        .replace("}", "\\}")
        .replace("\r", "")
        .replace("\n", "\\N")
    )


def _write_segment_subtitle(path: Path, duration: float, title: str, note: str) -> bool:
    lines = [item.strip() for item in [title, note] if item and item.strip()]
    if not lines:
        return False
    text = "\\N".join(_ass_escape(item) for item in lines)
    content = f"""[Script Info]
ScriptType: v4.00+
PlayResX: 1920
PlayResY: 1080

[V4+ Styles]
Format: Name, Fontname, Fontsize, PrimaryColour, SecondaryColour, OutlineColour, BackColour, Bold, Italic, Underline, StrikeOut, ScaleX, ScaleY, Spacing, Angle, BorderStyle, Outline, Shadow, Alignment, MarginL, MarginR, MarginV, Encoding
Style: Default,Microsoft YaHei,44,&H00FFFFFF,&H000000FF,&HAA000000,&H66000000,0,0,0,0,100,100,0,0,1,2,1,2,72,72,64,1

[Events]
Format: Layer, Start, End, Style, Name, MarginL, MarginR, MarginV, Effect, Text
Dialogue: 0,0:00:00.00,{_format_ass_time(duration)},Default,,0,0,0,,{text}
"""
    path.write_text(content, encoding="utf-8")
    return True


def _filter_escape(text: str) -> str:
    return (
        (text or "")
        .replace("\\", "\\\\")
        .replace(":", "\\:")
        .replace("'", "\\'")
        .replace("%", "\\%")
        .replace("\r", " ")
        .replace("\n", " ")
    )


def _clamp_float(value: Any, minimum: float, maximum: float, default: float) -> float:
    try:
        number = float(value)
    except (TypeError, ValueError):
        number = default
    return max(minimum, min(maximum, number))


def _round_float(value: float) -> float:
    return round(float(value), 2)


def _focus_window(segment: dict[str, Any], duration: float) -> tuple[float, float]:
    focus_point = segment.get("focus_point_seconds")
    if focus_point is not None:
        point = _clamp_float(focus_point, 0, duration, max(0, duration * 0.25))
        pause = _clamp_float(segment.get("focus_pause_seconds"), 0.2, 5, 1.0)
        return _round_float(point), _round_float(point + pause)
    fallback_start = max(0.8, duration * 0.25)
    fallback_end = max(fallback_start + 0.8, duration * 0.78)
    start = _clamp_float(segment.get("focus_start_seconds"), 0, duration, fallback_start)
    end = _clamp_float(segment.get("focus_end_seconds"), 0, duration, fallback_end)
    if end <= start:
        end = min(duration, start + 0.8)
    if end <= start:
        start = max(0, end - 0.1)
    return _round_float(start), _round_float(end)


def _focus_pause_filter(segment: dict[str, Any], duration: float) -> str | None:
    focus_point = segment.get("focus_point_seconds")
    if focus_point is None:
        return None
    fps = 30
    point = _clamp_float(focus_point, 0, duration, max(0, duration * 0.25))
    pause = _clamp_float(segment.get("focus_pause_seconds"), 0.2, 5, 1.0)
    point_frame = max(0, int(round(point * fps)))
    pause_frames = max(1, int(round(pause * fps)))
    return f"fps={fps},loop=loop={pause_frames}:size=1:start={point_frame},setpts=N/({fps}*TB)"


def _focus_rect(segment: dict[str, Any]) -> tuple[float, float, float, float]:
    width = _clamp_float(segment.get("focus_width"), 0.08, 1.0, 0.24)
    height = _clamp_float(segment.get("focus_height"), 0.08, 1.0, 0.24)
    x = _clamp_float(segment.get("focus_x"), 0, 1 - width, 0.38)
    y = _clamp_float(segment.get("focus_y"), 0, 1 - height, 0.38)
    return x, y, width, height


def _focus_overlay_position(position: str) -> str:
    positions = {
        "top_left": "x=58:y=58",
        "bottom_right": "x=W-w-58:y=H-h-58",
        "bottom_left": "x=58:y=H-h-58",
        "center": "x=(W-w)/2:y=(H-h)/2",
    }
    return positions.get(position, "x=(W-w)/2:y=(H-h)/2")


def _teaching_filter(segment: dict[str, Any], duration: float, idx: int, total: int) -> str:
    title = _filter_escape(str(segment.get("title") or f"Step {idx}"))
    note = _filter_escape(str(segment.get("note") or ""))
    focus_mode = segment.get("focus_mode", "auto_center")
    slow_motion = bool(segment.get("slow_motion", True))
    focus_start, focus_end = _focus_window(segment, duration)
    filters = []
    pause_filter = _focus_pause_filter(segment, duration)
    if pause_filter:
        filters.append(pause_filter)
    filters.extend([
        "scale=1920:1080:force_original_aspect_ratio=decrease",
        "pad=1920:1080:(ow-iw)/2:(oh-ih)/2:color=black",
        "setsar=1",
    ])
    if focus_mode == "auto_center":
        focus_x, focus_y, focus_width, focus_height = _focus_rect(segment)
        focus_scale = _clamp_float(segment.get("focus_scale"), 0.8, 2.4, 1.2)
        zoom_width = int(round(720 * focus_scale / 2) * 2)
        zoom_height = int(round(420 * focus_scale / 2) * 2)
        overlay_position = _focus_overlay_position(str(segment.get("focus_position") or "center"))
        filters.append(
            "split=2[base][zoom];"
            f"[zoom]crop=iw*{focus_width:.4f}:ih*{focus_height:.4f}:iw*{focus_x:.4f}:ih*{focus_y:.4f},"
            f"scale={zoom_width}:{zoom_height},"
            "drawbox=x=0:y=0:w=iw:h=ih:color=white@0.9:t=4,"
            f"drawtext=text='AIM ZOOM':x=24:y=24:fontsize=34:fontcolor=white:box=1:boxcolor=black@0.55:enable='between(t,{focus_start:.2f},{focus_end:.2f})'[zoomed];"
            f"[base][zoomed]overlay={overlay_position}:enable='between(t,{focus_start:.2f},{focus_end:.2f})'"
        )
    if slow_motion:
        filters.append(f"drawtext=text='SLOW MOTION':x=W-420:y=450:fontsize=36:fontcolor=#ffd166:box=1:boxcolor=black@0.45:enable='between(t,{focus_start:.2f},{focus_end:.2f})'")
    filters.extend([
        "drawbox=x=44:y=44:w=560:h=126:color=black@0.52:t=fill",
        f"drawtext=text='STEP {idx}/{total}':x=72:y=66:fontsize=30:fontcolor=#ffb34f",
        f"drawtext=text='{title}':x=72:y=108:fontsize=42:fontcolor=white",
    ])
    if note:
        filters.extend([
            f"drawbox=x=0:y=884:w=1920:h=196:color=black@0.66:t=fill:enable='between(t,{focus_start:.2f},{focus_end:.2f})'",
            f"drawtext=text='{note}':x=(w-text_w)/2:y=946:fontsize=48:fontcolor=white:enable='between(t,{focus_start:.2f},{focus_end:.2f})'",
        ])
    return ",".join(filters)


def _run_ffmpeg(command: list[str], cwd: Path | None = None) -> None:
    try:
        completed = subprocess.run(
            command,
            cwd=str(cwd) if cwd else None,
            capture_output=True,
            text=True,
            encoding="utf-8",
            errors="replace",
            timeout=1800,
        )
    except FileNotFoundError:
        raise HTTPException(status_code=503, detail="未找到 ffmpeg，请先安装并加入 PATH")
    except subprocess.TimeoutExpired:
        raise RuntimeError("FFmpeg 渲染超时")
    if completed.returncode != 0:
        message = (completed.stderr or completed.stdout or "FFmpeg 渲染失败").strip()
        raise RuntimeError(message[-1000:])


def _render_clip_job(job: dict[str, Any]) -> dict[str, str]:
    ffmpeg = shutil.which("ffmpeg")
    if not ffmpeg:
        raise HTTPException(status_code=503, detail="未找到 ffmpeg，请先安装并加入 PATH")

    source_path = _clip_file_from_url(job.get("source_url", ""), "sources")
    segments = job.get("segments") or []
    if not segments:
        raise RuntimeError("没有可渲染的片段")

    job_dir = CLIP_WORK_DIR / f"clip-{job['id']}"
    if job_dir.exists():
        shutil.rmtree(job_dir)
    job_dir.mkdir(parents=True, exist_ok=True)

    rendered_files: list[str] = []
    total_segments = len(segments)
    for idx, segment in enumerate(segments, start=1):
        start = float(segment["start_seconds"])
        end = float(segment["end_seconds"])
        duration = end - start
        clip_name = f"segment-{idx:03d}.mp4"
        command = [
            ffmpeg,
            "-y",
            "-ss",
            f"{start:.3f}",
            "-i",
            str(source_path),
            "-t",
            f"{duration:.3f}",
            "-map",
            "0:v:0",
            "-map",
            "0:a?",
            "-c:v",
            "libx264",
            "-preset",
            "veryfast",
            "-crf",
            "20",
            "-pix_fmt",
            "yuv420p",
            "-vf",
            _teaching_filter(segment, duration, idx, total_segments),
        ]
        command.extend(["-c:a", "aac", "-movflags", "+faststart", clip_name])
        _run_ffmpeg(command, cwd=job_dir)
        rendered_files.append(clip_name)

    concat_file = job_dir / "concat.txt"
    concat_file.write_text(
        "\n".join(f"file '{name}'" for name in rendered_files),
        encoding="utf-8",
    )
    output_filename = f"{uuid4().hex}.mp4"
    output_path = CLIP_OUTPUT_DIR / output_filename
    _run_ffmpeg(
        [
            ffmpeg,
            "-y",
            "-f",
            "concat",
            "-safe",
            "0",
            "-i",
            str(concat_file),
            "-c",
            "copy",
            "-movflags",
            "+faststart",
            str(output_path),
        ],
        cwd=job_dir,
    )
    return {"output_filename": output_filename, "output_url": _clip_public_url("outputs", output_filename)}


@app.get("/api/admin/clips")
def admin_clips(_: dict[str, Any] = Depends(get_admin_user)) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    return [
        _normalize_clip_job(item, state)
        for item in sorted(state.get("clip_jobs", []), key=lambda x: x.get("created_at", ""), reverse=True)
    ]


@app.post("/api/admin/clips/source")
def upload_clip_source(file: UploadFile = File(...), _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    suffix = Path(file.filename or "clip.mp4").suffix.lower()
    mime = (file.content_type or "").lower()
    if suffix not in CLIP_ALLOWED_EXTENSIONS:
        raise HTTPException(status_code=400, detail=f"不支持的视频格式: {suffix}")
    if mime and mime not in CLIP_ALLOWED_MIMES and not mime.startswith("video/"):
        raise HTTPException(status_code=400, detail=f"不支持的视频类型: {mime}")

    filename = f"{uuid4().hex}{suffix}"
    target = CLIP_SOURCE_DIR / filename
    total = 0
    try:
        with target.open("wb") as output:
            while True:
                chunk = file.file.read(1024 * 1024)
                if not chunk:
                    break
                total += len(chunk)
                if total > MAX_CLIP_UPLOAD_BYTES:
                    output.close()
                    target.unlink(missing_ok=True)
                    raise HTTPException(status_code=400, detail="视频文件过大，最大允许 2 GB")
                output.write(chunk)
    except HTTPException:
        raise
    except Exception as exc:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=500, detail=f"视频上传失败: {exc}")
    if total == 0:
        target.unlink(missing_ok=True)
        raise HTTPException(status_code=400, detail="视频文件为空")
    return {
        "filename": filename,
        "original_name": file.filename,
        "url": _clip_public_url("sources", filename),
        "size": total,
        "type": file.content_type or "application/octet-stream",
    }


@app.post("/api/admin/clips")
def create_clip_job(payload: ClipJobPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        _validate_clip_payload(state, item)
        now = utc_iso(utc_now())
        item["id"] = next_id(state, "clip_jobs")
        item["status"] = "draft"
        item["output_url"] = ""
        item["output_filename"] = ""
        item["error"] = ""
        item["created_at"] = now
        item["updated_at"] = now
        state.setdefault("clip_jobs", []).append(item)
        return _normalize_clip_job(item, state)

    return STORE.mutate(mutate)


@app.put("/api/admin/clips/{clip_id}")
def update_clip_job(clip_id: int, payload: ClipJobPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state.setdefault("clip_jobs", []), clip_id)
        next_item = {**item, **dump_model(payload)}
        _validate_clip_payload(state, next_item)
        item.update(next_item)
        item["status"] = "draft"
        item["error"] = ""
        item["updated_at"] = utc_iso(utc_now())
        return _normalize_clip_job(item, state)

    return STORE.mutate(mutate)


@app.post("/api/admin/clips/{clip_id}/render")
def render_clip_job(background_tasks: BackgroundTasks, clip_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    state = STORE.snapshot()
    job = _normalize_clip_job(find_by_id(state.get("clip_jobs", []), clip_id), state)
    _validate_clip_payload(state, job)

    def mark_rendering(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["clip_jobs"], clip_id)
        item["status"] = "rendering"
        item["error"] = ""
        item["updated_at"] = utc_iso(utc_now())
        return _normalize_clip_job(item, state)

    job = STORE.mutate(mark_rendering)
    background_tasks.add_task(_render_clip_job_background, clip_id)
    return job


def _render_clip_job_background(clip_id: int) -> None:
    state = STORE.snapshot()
    job = _normalize_clip_job(find_by_id(state.get("clip_jobs", []), clip_id), state)
    try:
        result = _render_clip_job(job)
    except HTTPException as exc:
        def mark_failed(state: dict[str, Any]) -> dict[str, Any]:
            item = find_by_id(state["clip_jobs"], clip_id)
            item["status"] = "failed"
            item["error"] = str(exc.detail)
            item["updated_at"] = utc_iso(utc_now())
            return _normalize_clip_job(item, state)

        STORE.mutate(mark_failed)
        return
    except Exception as exc:
        def mark_failed(state: dict[str, Any]) -> dict[str, Any]:
            item = find_by_id(state["clip_jobs"], clip_id)
            item["status"] = "failed"
            item["error"] = str(exc)
            item["updated_at"] = utc_iso(utc_now())
            return _normalize_clip_job(item, state)

        STORE.mutate(mark_failed)
        return

    def mark_ready(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["clip_jobs"], clip_id)
        item.update(result)
        item["status"] = "ready"
        item["error"] = ""
        item["updated_at"] = utc_iso(utc_now())
        return _normalize_clip_job(item, state)

    STORE.mutate(mark_ready)


@app.delete("/api/admin/clips/{clip_id}")
def delete_clip_job(clip_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        item = find_by_id(state.setdefault("clip_jobs", []), clip_id)
        if item.get("output_url"):
            try:
                _clip_file_from_url(item["output_url"], "outputs").unlink(missing_ok=True)
            except HTTPException:
                pass
        work_dir = CLIP_WORK_DIR / f"clip-{clip_id}"
        if work_dir.exists():
            shutil.rmtree(work_dir, ignore_errors=True)
        state["clip_jobs"] = [clip for clip in state["clip_jobs"] if clip["id"] != clip_id]
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


def _validate_lineup_payload(state: dict[str, Any], item: dict[str, Any]) -> None:
    map_id = item["map_id"]
    find_by_id(state["maps"], map_id)
    for label, point_id in (
        ("起点", item["start_point_id"]),
        ("瞄点", item["aim_point_id"]),
        ("落点", item["land_point_id"]),
    ):
        point = find_by_id(state["points"], point_id)
        if point["map_id"] != map_id:
            raise HTTPException(status_code=400, detail=f"{label}必须属于当前地图")


@app.post("/api/admin/lineups")
def create_lineup(payload: LineupPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        _validate_lineup_payload(state, item)
        item["id"] = next_id(state, "lineups")
        state["lineups"].append(item)
        return build_lineup_detail(state, item)

    return STORE.mutate(mutate)


@app.put("/api/admin/lineups/{lineup_id}")
def update_lineup(lineup_id: int, payload: LineupPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = find_by_id(state["lineups"], lineup_id)
        next_item = {**item, **dump_model(payload)}
        _validate_lineup_payload(state, next_item)
        item.update(next_item)
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


def _validate_tactic_slug(state: dict[str, Any], tactic: dict[str, Any]) -> None:
    slug = tactic.get("slug", "")
    if not slug:
        return
    for item in state["tactics"]:
        if item["id"] != tactic["id"] and item.get("slug") == slug:
            raise HTTPException(status_code=409, detail=f"Slug 已被战术 #{item['id']} 使用")


def _validate_tactic_ready(state: dict[str, Any], tactic: dict[str, Any]) -> None:
    issues: list[str] = []
    if not tactic.get("title", "").strip():
        issues.append("标题不能为空")
    if not tactic.get("summary", "").strip():
        issues.append("摘要不能为空")
    if not tactic.get("cover_url", "").strip():
        issues.append("封面不能为空")
    if not tactic.get("step_items"):
        issues.append("至少需要一个执行步骤")
    for step in tactic.get("step_items", []):
        if not step.get("instruction", "").strip():
            issues.append("执行步骤说明不能为空")
        lineup_id = step.get("lineup_id")
        if lineup_id and not any(lineup["id"] == lineup_id for lineup in state["lineups"]):
            issues.append(f"步骤关联的线路 #{lineup_id} 不存在")
    for shot in tactic.get("screenshots", []):
        if not shot.get("url", "").strip():
            issues.append("截图 URL 不能为空")
    if issues:
        raise HTTPException(status_code=400, detail="；".join(dict.fromkeys(issues)))


@app.post("/api/admin/tactics")
def create_tactic(payload: TacticPayload, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, Any]:
    def mutate(state: dict[str, Any]) -> dict[str, Any]:
        item = dump_model(payload)
        item["id"] = next_id(state, "tactics")
        item["slug"] = _auto_slug(payload.slug, payload.title, item["id"])
        item["created_at"] = datetime.now(timezone.utc).isoformat()
        _validate_tactic_slug(state, item)
        if item["status"] == "published":
            _validate_tactic_ready(state, item)
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
        _validate_tactic_slug(state, item)
        if item["status"] == "published":
            _validate_tactic_ready(state, item)
        return item

    return STORE.mutate(mutate)


@app.post("/api/admin/tactics/{tactic_id}/publish")
def publish_tactic(tactic_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        tactic = find_by_id(state["tactics"], tactic_id)
        _validate_tactic_slug(state, tactic)
        _validate_tactic_ready(state, tactic)
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


@app.get("/api/admin/assets")
def admin_assets(
    _: dict[str, Any] = Depends(get_admin_user),
    q: str | None = None,
    media_type: str | None = None,
) -> list[dict[str, Any]]:
    state = STORE.snapshot()
    assets = list(state.get("assets", []))
    if q:
        needle = q.strip().lower()
        assets = [
            item for item in assets
            if needle in (item.get("original_name") or "").lower()
            or needle in (item.get("url") or "").lower()
        ]
    if media_type and media_type != "all":
        assets = [item for item in assets if (item.get("type") or "").startswith(media_type)]
    return [
        {**item, "used": _asset_is_used(state, item.get("url", ""))}
        for item in sorted(assets, key=lambda item: item.get("id", 0), reverse=True)
    ]


def _asset_is_used(state: dict[str, Any], url: str) -> bool:
    if not url:
        return False
    for item in state["maps"]:
        if url in {item.get("cover_url"), item.get("layout_url")}:
            return True
    for item in state["points"]:
        if url in {item.get("aim_image_url"), item.get("effect_image_url")}:
            return True
    for item in state["lineups"]:
        if url in set(item.get("media", [])):
            return True
    for item in state["tactics"]:
        if url == item.get("cover_url"):
            return True
        if any(url == shot.get("url") for shot in item.get("screenshots", [])):
            return True
    for item in state.get("collections", []):
        if url == item.get("cover_url"):
            return True
    return False


@app.delete("/api/admin/assets/{asset_id}")
def delete_asset(asset_id: int, _: dict[str, Any] = Depends(get_admin_user)) -> dict[str, str]:
    def mutate(state: dict[str, Any]) -> dict[str, str]:
        asset = find_by_id(state["assets"], asset_id)
        if _asset_is_used(state, asset.get("url", "")):
            raise HTTPException(status_code=409, detail="素材正在被内容引用，不能删除")
        state["assets"] = [item for item in state["assets"] if item["id"] != asset_id]
        file_path = UPLOAD_DIR / asset.get("filename", "")
        if file_path.exists() and file_path.is_file():
            file_path.unlink()
        return {"status": "ok"}

    return STORE.mutate(mutate)


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
