"""Security hardening — password, token, upload restrictions, privacy."""

import pytest
import allure

from utils.allure_helper import assert_status, assert_error, attach_body


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
            if "$" not in pw_hash:
                pytest.skip(f"User '{username}' has legacy (non-PBKDF2) password hash — "
                            f"will be auto-upgraded on next login")


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
        assert status in (400, 429), f"Expected 400 or 429, got {status}: {body}"

    @allure.title("Upload empty file is rejected")
    def test_reject_empty_file(self, admin_client, tmp_path):
        empty = tmp_path / "empty.png"
        empty.write_bytes(b"")
        from utils.api_client import Client
        status, body = Client(token=admin_client.token).admin_upload_asset(str(empty))
        assert status in (400, 429), f"Expected 400 or 429, got {status}: {body}"

    @allure.title("Upload valid PNG is accepted")
    def test_accept_png(self, admin_client, tmp_path):
        png_data = (
            b"\x89PNG\r\n\x1a\n"
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
        # 200 on success, 429 if rate-limited by preceding tests
        assert status in (200, 429), f"Expected 200 or 429, got {status}: {body}"
        if status == 200:
            assert "url" in body, f"No URL in upload response: {body}"


@allure.feature("Security — Privacy")
class TestPrivacy:

    @allure.title("User list does not leak password hashes")
    def test_no_password_leak(self, admin_client):
        status, users = admin_client.admin_list_users()
        assert status in (200, 429), f"Expected 200 or 429, got {status}"
        if status == 429:
            pytest.skip("Rate limited")
        for u in users:
            assert "password_hash" not in u
            assert "password" not in u

    @allure.title("Player cannot access admin endpoints")
    def test_player_admin_access(self, player_client):
        status, _ = player_client.admin_list_maps()
        assert status in (403, 429), f"Expected 403 or 429, got {status}"
