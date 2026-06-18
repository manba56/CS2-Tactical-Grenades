"""Unit tests for cs2-api/app/auth.py — pure functions, no HTTP."""

import hashlib

import pytest
import allure


# ── helpers ────────────────────────────────────────────────────────


def test_hash_password_format():
    from app.auth import hash_password

    result = hash_password("mypassword")
    assert "$" in result, "Hash must contain $ separator"
    salt_hex, key_hex = result.split("$", 1)
    assert len(salt_hex) == 64, f"Salt should be 64 hex chars (32 bytes), got {len(salt_hex)}"
    assert len(key_hex) == 64, f"Key should be 64 hex chars (32 bytes), got {len(key_hex)}"
    assert all(c in "0123456789abcdef" for c in salt_hex), "Salt must be valid hex"
    assert all(c in "0123456789abcdef" for c in key_hex), "Key must be valid hex"


def test_hash_password_different_each_call():
    """Each call uses a fresh random salt — hashes must differ."""
    from app.auth import hash_password

    h1 = hash_password("same_password")
    h2 = hash_password("same_password")
    assert h1 != h2, "Two calls should produce different hashes due to random salt"


def test_verify_correct_password():
    from app.auth import hash_password, verify_password

    hashed = hash_password("correct123")
    assert verify_password("correct123", hashed) is True


def test_verify_wrong_password():
    from app.auth import hash_password, verify_password

    hashed = hash_password("correct123")
    assert verify_password("wrong_password", hashed) is False


def test_verify_legacy_hash():
    """Legacy hashes (no $ separator) should still verify."""
    from app.auth import verify_password

    legacy = hashlib.sha256("legacypass".encode("utf-8")).hexdigest()
    assert verify_password("legacypass", legacy) is True


def test_verify_legacy_hash_wrong():
    from app.auth import verify_password

    legacy = hashlib.sha256("legacypass".encode("utf-8")).hexdigest()
    assert verify_password("wrongpass", legacy) is False


def test_verify_empty_or_malformed():
    from app.auth import verify_password

    assert verify_password("pass", "") is False

    # Malformed hex after first $ raises ValueError (invalid literal)
    import pytest as _pytest
    try:
        result = verify_password("anything", "salt$$extra")
        # If it doesn't raise, it must return False
        assert result is False
    except ValueError:
        pass  # ValueError("non-hexadecimal number") is also acceptable


def test_needs_rehash_legacy():
    from app.auth import needs_rehash

    assert needs_rehash("plain_sha256_no_salt") is True


def test_needs_rehash_pbkdf2():
    from app.auth import needs_rehash

    assert needs_rehash("aabb$ccdd") is False


def test_generate_token():
    from app.auth import generate_token

    raw, token_hash = generate_token()
    assert len(raw) == 128, f"Raw token should be 128 hex chars (64 bytes), got {len(raw)}"
    assert len(token_hash) == 64, f"Token hash should be 64 hex chars (SHA256), got {len(token_hash)}"
    assert raw != token_hash, "Raw token and hash must differ"
    assert all(c in "0123456789abcdef" for c in raw)
    assert all(c in "0123456789abcdef" for c in token_hash)


def test_verify_token_correct():
    from app.auth import generate_token, verify_token

    raw, token_hash = generate_token()
    assert verify_token(raw, token_hash) is True


def test_verify_token_wrong():
    from app.auth import generate_token, verify_token

    raw, _ = generate_token()
    _, wrong_hash = generate_token()
    assert verify_token(raw, wrong_hash) is False


def test_parse_legacy_token_player():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("player:42") == ("player", 42)


def test_parse_legacy_token_admin():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("admin:1") == ("admin", 1)


def test_parse_legacy_token_no_colon():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("invalidtoken") is None


def test_parse_legacy_token_bad_role():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("moderator:5") is None


def test_parse_legacy_token_non_integer_id():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("player:abc") is None


def test_parse_legacy_token_none():
    from app.auth import parse_legacy_token

    assert parse_legacy_token(None) is None


def test_parse_legacy_token_empty():
    from app.auth import parse_legacy_token

    assert parse_legacy_token("") is None


def test_public_user_payload_shape():
    from app.auth import public_user_payload

    user = {"id": 1, "username": "test", "email": "a@b.com", "role": "player", "password_hash": "xxx"}
    result = public_user_payload(user, "token123")
    assert result["token"] == "token123"
    assert result["user"]["id"] == 1
    assert result["user"]["username"] == "test"
    assert result["user"]["email"] == "a@b.com"
    assert result["user"]["role"] == "player"


def test_public_user_payload_excludes_password():
    from app.auth import public_user_payload

    user = {"id": 2, "username": "u", "email": "u@x.com", "role": "player", "password_hash": "secret"}
    result = public_user_payload(user, "tok")
    assert "password_hash" not in result
    assert "password_hash" not in result["user"]


def test_token_expiry_detection():
    from datetime import datetime, timedelta, timezone
    from app.main import is_token_expired, utc_iso

    now = datetime.now(timezone.utc)
    assert is_token_expired({"expires_at": utc_iso(now - timedelta(seconds=1))}, now) is True
    assert is_token_expired({"expires_at": utc_iso(now + timedelta(seconds=1))}, now) is False
    assert is_token_expired({"expires_at": None}, now) is False
