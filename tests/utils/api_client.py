"""Typed API client wrapping the full cs2-api surface."""

from __future__ import annotations

import requests
import config

TIMEOUT = config.REQUEST_TIMEOUT


class ApiError(Exception):
    def __init__(self, status: int, detail: str):
        self.status = status
        self.detail = detail
        super().__init__(f"HTTP {status}: {detail}")


class Client:
    """Thin wrapper: each method → (status_code, json_body)."""

    def __init__(self, base: str = "", token: str | None = None) -> None:
        self.base = (base or config.API_BASE).rstrip("/")
        self.token = token
        self.session = requests.Session()
        if token:
            self.session.headers["Authorization"] = f"Bearer {token}"

    def _url(self, path: str) -> str:
        return f"{self.base}{path}"

    def _do(self, method: str, path: str, **kwargs) -> tuple[int, dict | list]:
        kwargs.setdefault("timeout", TIMEOUT)
        resp = self.session.request(method, self._url(path), **kwargs)
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        return resp.status_code, body

    # ── Public ─────────────────────────────────
    def health(self) -> tuple[int, dict]:
        return self._do("GET", "/api/health")

    def home(self) -> tuple[int, dict]:
        return self._do("GET", "/api/public/home")

    def list_maps(self) -> tuple[int, list]:
        return self._do("GET", "/api/public/maps")

    def map_detail(self, slug: str) -> tuple[int, dict]:
        return self._do("GET", f"/api/public/maps/{slug}")

    def list_tactics(self, params: dict | None = None) -> tuple[int, dict]:
        return self._do("GET", "/api/public/tactics", params=params or {})

    def tactic_detail(self, slug: str) -> tuple[int, dict]:
        return self._do("GET", f"/api/public/tactics/{slug}")

    # ── Auth ───────────────────────────────────
    def login(self, username_or_email: str, password: str) -> tuple[int, dict]:
        return self._do("POST", "/api/public/auth/login", json={
            "username_or_email": username_or_email,
            "password": password,
        })

    def logout(self) -> tuple[int, dict]:
        return self._do("POST", "/api/public/auth/logout")

    def register(self, username: str, email: str, password: str) -> tuple[int, dict]:
        return self._do("POST", "/api/public/auth/register", json={
            "username": username,
            "email": email,
            "password": password,
        })

    def admin_login(self, username: str, password: str) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/auth/login", json={
            "username": username,
            "password": password,
        })

    def admin_logout(self) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/auth/logout")

    # ── User favorites / recent ────────────────
    def get_favorites(self) -> tuple[int, dict]:
        return self._do("GET", "/api/public/me/favorites")

    def add_favorite(self, tactic_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/public/me/favorites/{tactic_id}")

    def remove_favorite(self, tactic_id: int) -> tuple[int, dict]:
        return self._do("DELETE", f"/api/public/me/favorites/{tactic_id}")

    def track_recent(self, tactic_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/public/me/recent/{tactic_id}")

    def add_lineup_favorite(self, lineup_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/public/me/lineups/favorites/{lineup_id}")

    def remove_lineup_favorite(self, lineup_id: int) -> tuple[int, dict]:
        return self._do("DELETE", f"/api/public/me/lineups/favorites/{lineup_id}")

    def set_tactic_progress(self, tactic_id: int, status: str | None) -> tuple[int, dict]:
        return self._do("PUT", f"/api/public/me/progress/tactics/{tactic_id}", json={
            "status": status,
        })

    def set_lineup_progress(self, lineup_id: int, status: str | None) -> tuple[int, dict]:
        return self._do("PUT", f"/api/public/me/progress/lineups/{lineup_id}", json={
            "status": status,
        })

    def sync_local_playbook(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/public/me/sync-local", json=payload)

    def list_personal_boards(self) -> tuple[int, list]:
        return self._do("GET", "/api/public/me/boards")

    def create_personal_board(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/public/me/boards", json=payload)

    def update_personal_board(self, board_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/public/me/boards/{board_id}", json=payload)

    def delete_personal_board(self, board_id: int) -> tuple[int, dict]:
        return self._do("DELETE", f"/api/public/me/boards/{board_id}")

    # ── Admin ──────────────────────────────────
    def admin_dashboard(self) -> tuple[int, dict]:
        return self._do("GET", "/api/admin/dashboard")

    def admin_list_maps(self) -> tuple[int, list]:
        return self._do("GET", "/api/admin/maps")

    def admin_create_map(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/maps", json=payload)

    def admin_update_map(self, map_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/admin/maps/{map_id}", json=payload)

    def admin_list_points(self, map_id: int | None = None) -> tuple[int, list]:
        params = {}
        if map_id is not None:
            params["map_id"] = map_id
        return self._do("GET", "/api/admin/points", params=params)

    def admin_create_point(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/points", json=payload)

    def admin_update_point(self, point_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/admin/points/{point_id}", json=payload)

    def admin_list_lineups(self, map_id: int | None = None) -> tuple[int, list]:
        params = {}
        if map_id is not None:
            params["map_id"] = map_id
        return self._do("GET", "/api/admin/lineups", params=params)

    def admin_create_lineup(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/lineups", json=payload)

    def admin_update_lineup(self, lineup_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/admin/lineups/{lineup_id}", json=payload)

    def admin_archive_lineup(self, lineup_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/admin/lineups/{lineup_id}/archive")

    def admin_delete_lineup(self, lineup_id: int) -> tuple[int, dict]:
        return self._do("DELETE", f"/api/admin/lineups/{lineup_id}")

    def admin_list_tactics(self) -> tuple[int, list]:
        return self._do("GET", "/api/admin/tactics")

    def admin_create_tactic(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/tactics", json=payload)

    def admin_update_tactic(self, tactic_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/admin/tactics/{tactic_id}", json=payload)

    def admin_publish_tactic(self, tactic_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/admin/tactics/{tactic_id}/publish")

    def admin_archive_tactic(self, tactic_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/admin/tactics/{tactic_id}/archive")

    def admin_list_users(self) -> tuple[int, list]:
        return self._do("GET", "/api/admin/users")

    def admin_upload_asset(self, file_path: str) -> tuple[int, dict]:
        with open(file_path, "rb") as fh:
            resp = self.session.post(
                self._url("/api/admin/assets"),
                files={"file": (file_path, fh, "image/png")},
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                timeout=TIMEOUT,
            )
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        return resp.status_code, body

    def admin_list_clips(self) -> tuple[int, list]:
        return self._do("GET", "/api/admin/clips")

    def admin_create_clip(self, payload: dict) -> tuple[int, dict]:
        return self._do("POST", "/api/admin/clips", json=payload)

    def admin_update_clip(self, clip_id: int, payload: dict) -> tuple[int, dict]:
        return self._do("PUT", f"/api/admin/clips/{clip_id}", json=payload)

    def admin_render_clip(self, clip_id: int) -> tuple[int, dict]:
        return self._do("POST", f"/api/admin/clips/{clip_id}/render")

    def admin_delete_clip(self, clip_id: int) -> tuple[int, dict]:
        return self._do("DELETE", f"/api/admin/clips/{clip_id}")

    def admin_upload_clip_source(self, file_path: str, content_type: str = "video/mp4") -> tuple[int, dict]:
        with open(file_path, "rb") as fh:
            resp = self.session.post(
                self._url("/api/admin/clips/source"),
                files={"file": (file_path, fh, content_type)},
                headers={"Authorization": f"Bearer {self.token}"} if self.token else {},
                timeout=TIMEOUT,
            )
        try:
            body = resp.json()
        except Exception:
            body = {"detail": resp.text}
        return resp.status_code, body
