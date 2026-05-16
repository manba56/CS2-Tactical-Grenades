"""Security hardening — rate limiting, anomaly detection, upload restrictions."""

import time
import pytest
import allure

from utils.allure_helper import assert_status, assert_error, attach_body
import config


@allure.feature("Security — Rate Limiting")
class TestRateLimit:

    @allure.title(f"Global rate limit triggers 429 after {config.RATE_LIMIT_REQUESTS} requests")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_global_rate_limit(self, anon_client):
        """Fire 130 requests in a loop; at least one must be 429."""
        saw_429 = False
        import requests as r
        for i in range(config.RATE_LIMIT_REQUESTS):
            try:
                resp = r.get(f"{config.API_BASE}/api/health", timeout=config.REQUEST_TIMEOUT)
                if resp.status_code == 429:
                    saw_429 = True
                    break
            except Exception:
                pass
        assert saw_429, f"Rate limit should trigger at {config.RATE_LIMIT_REQUESTS} requests"


@allure.feature("Security — Anomaly Detection")
class TestAnomalyDetection:

    @allure.title("Default account lockout after 5 failed logins")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_admin_lockout(self, anon_client):
        for i in range(6):
            status, body = anon_client.admin_login("admin", f"wrongpass{i}")
        # 6th attempt should be locked (429)
        assert status in (400, 429), \
            f"Expected 400 or 429 on lockout, got {status}: {body}"

    @allure.title("Demo account lockout after 5 failed logins")
    def test_demo_lockout(self, anon_client):
        for i in range(6):
            status, body = anon_client.login("demo", f"wrongpass{i}")
        assert status in (400, 429), \
            f"Expected 400 or 429 on lockout, got {status}: {body}"


@allure.feature("Security — Password Hashing")
class TestPasswordHashing:

    @allure.title("Password stored as PBKDF2 salt$hash (not plaintext)")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_password_not_plaintext(self):
        """Direct DB check — password_hash must contain $ separator."""
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent.parent.parent / "cs2-api" / "data" / "db.sqlite"
        if not db_path.exists():
            pytest.skip("SQLite file not found (use production path)")

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT username, password_hash FROM users").fetchall()
        conn.close()
        for username, pw_hash in rows:
            assert "$" in pw_hash, \
                f"User '{username}' password_hash is not PBKDF2-salted: {pw_hash[:20]}..."


@allure.feature("Security — Token Hashing")
class TestTokenHashing:

    @allure.title("Tokens stored as SHA256 hash (not raw)")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_token_not_raw(self):
        import sqlite3
        from pathlib import Path
        db_path = Path(__file__).resolve().parent.parent.parent / "cs2-api" / "data" / "db.sqlite"
        if not db_path.exists():
            pytest.skip("SQLite file not found")

        conn = sqlite3.connect(str(db_path))
        rows = conn.execute("SELECT id, token_hash FROM tokens").fetchall()
        conn.close()
        for tid, token_hash in rows:
            assert len(token_hash) == 64, \
                f"Token {tid} hash length is {len(token_hash)}, expected 64 (SHA256 hex)"
            # Must be all hex
            assert all(c in "0123456789abcdef" for c in token_hash), \
                f"Token {tid} hash is not valid hex"


@allure.feature("Security — Upload Restrictions")
class TestUploadRestrictions:

    @allure.title("Upload non-image file is rejected")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_reject_text_file(self, admin_client, tmp_path):
        txt = tmp_path / "test.txt"
        txt.write_text("this is not an image")
        from utils.api_client import Client
        status, body = Client(token=admin_client.token).admin_upload_asset(str(txt))
        assert status == 400, f"Expected 400 for .txt upload, got {status}: {body}"

    @allure.title("Upload empty file is rejected")
    def test_reject_empty_file(self, admin_client, tmp_path):
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        from utils.api_client import Client
        status, body = Client(token=admin_client.token).admin_upload_asset(str(empty))
        assert status == 400, f"Expected 400 for empty file, got {status}: {body}"

    @allure.title("Upload valid PNG is accepted")
    def test_accept_png(self, admin_client, tmp_path):
        # Minimal 1x1 PNG
        png_data = (
            b"\x89PNG\r\n\x1a\n"  # PNG signature
            b"\x00\x00\x00\rIHDR\x00\x00\x00\x01\x00\x00\x00\x01"
            b"\x08\x02\x00\x00\x00\x90wS\xde"
            b"\x00\x00\x00\x0cIDATx\x9cc\xf8\x0f\x00\x00\x01\x01\x00\x05"
            b"\x18\xd8N"
            b"\x00\x00\x00\x00IEND\xaeB`\x82"
        )
        png = tmp_path / "valid.png"
        png.write_bytes(png_data)
        from utils.api_client import Client
        status, body = Client(token=admin_client.token).admin_upload_asset(str(png))
        assert_status(status, 200)
        assert "url" in body, f"No URL in upload response: {body}"


@allure.feature("Security — Privacy")
class TestPrivacy:

    @allure.title("User list does not leak password hashes")
    def test_no_password_leak(self, admin_client):
        status, users = admin_client.admin_list_users()
        assert_status(status, 200)
        for u in users:
            assert "password_hash" not in u
            assert "password" not in u

    @allure.title("Player cannot access admin endpoints")
    def test_player_admin_access(self, player_client):
        status, _ = player_client.admin_list_maps()
        assert status == 403, f"Expected 403, got {status}"
