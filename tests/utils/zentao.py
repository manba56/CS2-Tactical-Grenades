"""ZenTao bug reporter — create bugs from failed test cases.

Uses ZenTao REST API (typically /zentao/api.php/v1/).
Set env vars: ZENTAO_URL, ZENTAO_USERNAME, ZENTAO_PASSWORD, ZENTAO_PRODUCT_ID.

Usage:
    from utils.zentao import ZenTao

    zt = ZenTao()
    zt.create_bug(
        title="[Auto] 首页加载失败",
        steps="1. 访问首页\n2. 等待加载",
        severity=2,
        pri=2,
    )
"""

from __future__ import annotations

import os
import requests

import config


class ZenTaoError(Exception):
    pass


class ZenTao:
    def __init__(self) -> None:
        self.url = config.ZENTAO_URL.rstrip("/")
        self.username = config.ZENTAO_USERNAME
        self.password = config.ZENTAO_PASSWORD
        self.product_id = config.ZENTAO_PRODUCT_ID
        self._token: str | None = None
        self._session = requests.Session()

    @property
    def enabled(self) -> bool:
        return bool(self.url and self.username and self.password)

    def _auth(self) -> str:
        """Obtain session token. ZenTao uses cookie-based auth or token header."""
        if self._token:
            return self._token
        try:
            resp = self._session.post(
                f"{self.url}/tokens",
                json={"account": self.username, "password": self.password},
                timeout=10,
            )
            data = resp.json()
            if resp.status_code == 201 and "token" in data:
                self._token = data["token"]
                self._session.headers["Token"] = self._token
                return self._token
            # Fallback: cookie-based login
            resp2 = self._session.post(
                f"{self.url}/users-login.json",
                data={"account": self.username, "password": self.password},
                timeout=10,
            )
            if resp2.status_code == 200:
                self._token = "cookie"
                return self._token
        except Exception as e:
            raise ZenTaoError(f"ZenTao auth failed: {e}")
        raise ZenTaoError("ZenTao auth failed — check credentials")

    def create_bug(
        self,
        title: str,
        steps: str = "",
        severity: int = 3,   # 1=致命 2=严重 3=一般 4=建议
        pri: int = 3,         # 1-4
        module_id: int = 0,
    ) -> int | None:
        """Create a bug in ZenTao. Returns bug ID or None."""
        if not self.enabled:
            print(f"[ZenTao] Skipped (not configured): {title}")
            return None

        self._auth()
        payload = {
            "product": self.product_id,
            "title": title,
            "steps": steps,
            "severity": severity,
            "pri": pri,
            "type": "codeerror",
        }
        if module_id:
            payload["module"] = module_id

        try:
            resp = self._session.post(
                f"{self.url}/bugs",
                json=payload,
                timeout=15,
            )
            if resp.status_code in (200, 201):
                data = resp.json()
                bug_id = data.get("id") or data.get("bug", {}).get("id")
                if bug_id:
                    print(f"[ZenTao] Bug #{bug_id} created: {title}")
                    return int(bug_id)
            # Fallback: form-encoded
            resp2 = self._session.post(
                f"{self.url}/bug-create-{self.product_id}-0-moduleID={module_id}.json",
                data=payload,
                timeout=15,
            )
            if resp2.status_code == 200:
                data2 = resp2.json()
                bug_id2 = data2.get("id")
                if bug_id2:
                    print(f"[ZenTao] Bug #{bug_id2} created (fallback): {title}")
                    return int(bug_id2)
            print(f"[ZenTao] Failed to create bug: status={resp.status_code}, body={resp.text[:200]}")
        except Exception as e:
            print(f"[ZenTao] Error creating bug: {e}")
        return None


# Singleton convenience
_zt_instance: ZenTao | None = None


def get_zentao() -> ZenTao:
    global _zt_instance
    if _zt_instance is None:
        _zt_instance = ZenTao()
    return _zt_instance


def report_on_failure(test_name: str, detail: str, severity: int = 3) -> None:
    """Call from conftest or teardown to auto-report failed tests."""
    zt = get_zentao()
    zt.create_bug(
        title=f"[Auto] {config.API_BASE} — {test_name}",
        steps=detail,
        severity=severity,
    )
