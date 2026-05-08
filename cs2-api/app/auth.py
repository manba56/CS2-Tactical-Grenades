from __future__ import annotations

import hashlib
from typing import Any


def hash_password(password: str) -> str:
    return hashlib.sha256(password.encode("utf-8")).hexdigest()


def verify_password(password: str, password_hash: str) -> bool:
    return hash_password(password) == password_hash


def create_token(role: str, user_id: int) -> str:
    return f"{role}:{user_id}"


def parse_token(token: str | None) -> tuple[str, int] | None:
    if not token or ":" not in token:
        return None

    role, raw_user_id = token.split(":", 1)
    if role not in {"player", "admin"}:
        return None

    try:
        return role, int(raw_user_id)
    except ValueError:
        return None


def public_user_payload(user: dict[str, Any], token: str) -> dict[str, Any]:
    return {
        "token": token,
        "user": {
            "id": user["id"],
            "username": user["username"],
            "email": user["email"],
            "role": user["role"],
        },
    }
