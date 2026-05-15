"""Password hashing and token management.

Passwords: PBKDF2-HMAC-SHA256 with 100,000 iterations and a random
32-byte salt. Stored as $<hex_salt>$<hex_hash>.

Tokens: 64-char random hex string returned to the client. Only the
SHA256 hash is stored in the database. Verification compares hashes.
"""

from __future__ import annotations

import hashlib
import os
import secrets
from typing import Any

# ── Password ─────────────────────────────────────────────────────
PBKDF2_ITERATIONS = 100_000
SALT_BYTES = 32


def hash_password(password: str) -> str:
    """Return a salted PBKDF2 hash. Format: hex_salt$hex_hash"""
    salt = os.urandom(SALT_BYTES)
    key = hashlib.pbkdf2_hmac(
        "sha256", password.encode("utf-8"), salt, PBKDF2_ITERATIONS
    )
    return f"{salt.hex()}${key.hex()}"


def verify_password(password: str, stored: str) -> bool:
    """Compare a plaintext password against a stored salted hash."""
    if "$" not in stored:
        # Legacy SHA256-only hash — auto-upgrade on next login
        return _legacy_verify(password, stored)
    salt_hex, key_hex = stored.split("$", 1)
    key = hashlib.pbkdf2_hmac(
        "sha256",
        password.encode("utf-8"),
        bytes.fromhex(salt_hex),
        PBKDF2_ITERATIONS,
    )
    return secrets.compare_digest(key.hex(), key_hex)


def _legacy_verify(password: str, stored: str) -> bool:
    """Fallback for old unsalted SHA256 hashes. Returns True + caller
    should re-hash the password to upgrade it."""
    return secrets.compare_digest(
        hashlib.sha256(password.encode("utf-8")).hexdigest(), stored
    )


def needs_rehash(stored: str) -> bool:
    """True if the stored hash uses the legacy unsalted format."""
    return "$" not in stored


# ── Token ────────────────────────────────────────────────────────
TOKEN_BYTES = 64


def generate_token() -> tuple[str, str]:
    """Return (raw_token, token_hash). The raw token goes to the client;
    the hash is stored in the database."""
    raw = secrets.token_hex(TOKEN_BYTES)
    token_hash = hashlib.sha256(raw.encode("utf-8")).hexdigest()
    return raw, token_hash


def verify_token(raw: str, token_hash: str) -> bool:
    """Compare a raw token against its stored hash."""
    return secrets.compare_digest(
        hashlib.sha256(raw.encode("utf-8")).hexdigest(), token_hash
    )


# ── Legacy token migration ───────────────────────────────────────
def parse_legacy_token(token: str | None) -> tuple[str, int] | None:
    """Parse old-style {role}:{user_id} tokens. Only used during
    migration; new tokens are random hex strings."""
    if not token or ":" not in token:
        return None
    role, raw_id = token.split(":", 1)
    if role not in {"player", "admin"}:
        return None
    try:
        return role, int(raw_id)
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
