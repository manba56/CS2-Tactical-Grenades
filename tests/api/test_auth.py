"""Authentication — login, register, token handling, legacy fallback."""

import time
import pytest
import allure

from utils.allure_helper import assert_status, assert_has_key, assert_error, attach_body
import config


@allure.feature("Auth — Register")
class TestRegister:

    @allure.title("Register new player")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_register_success(self, anon_client):
        import uuid
        uname = f"reg_{uuid.uuid4().hex[:6]}"
        status, body = anon_client.register(uname, f"{uname}@test.com", "pass123456")
        attach_body(body)
        assert_status(status, 200)
        assert_has_key(body, "token")
        assert_has_key(body, "user")

    @allure.title("Register duplicate username")
    def test_register_duplicate(self, anon_client):
        import uuid
        uname = f"dup_{uuid.uuid4().hex[:6]}"
        anon_client.register(uname, f"{uname}@test.com", "pass123456")
        status, body = anon_client.register(uname, f"diff_{uname}@test.com", "pass123456")
        assert_error(status, body, 400, "用户名已存在")

    @allure.title("Register duplicate email")
    def test_register_duplicate_email(self, anon_client):
        import uuid
        uname = f"eml_{uuid.uuid4().hex[:6]}"
        email = f"{uname}@test.com"
        anon_client.register(uname, email, "pass123456")
        status, body = anon_client.register(f"diff_{uname}", email, "pass123456")
        assert_error(status, body, 400, "邮箱已存在")


@allure.feature("Auth — Login")
class TestLogin:

    @allure.title("Login with correct credentials")
    @allure.severity(allure.severity_level.CRITICAL)
    def test_login_success(self, player_client):
        # player_client already authenticated — test passes by fixture
        assert player_client.token is not None

    @allure.title("Login with wrong password")
    def test_login_wrong_password(self, anon_client):
        import uuid
        uname = f"wrong_{uuid.uuid4().hex[:6]}"
        anon_client.register(uname, f"{uname}@test.com", "correct123")
        status, body = anon_client.login(uname, "wrongpass")
        assert_error(status, body, 400, "账号或密码错误")

    @allure.title("Login with non-existent user")
    def test_login_nonexistent(self, anon_client):
        status, body = anon_client.login("nouser_99999", "anything")
        assert_error(status, body, 400)


@allure.feature("Auth — Admin Login")
class TestAdminLogin:

    @allure.title("Admin login success")
    @allure.severity(allure.severity_level.BLOCKER)
    def test_admin_login(self, admin_client):
        assert admin_client.token is not None

    @allure.title("Admin login wrong password")
    def test_admin_login_wrong(self, anon_client):
        status, body = anon_client.admin_login(config.ADMIN_USERNAME, "wrongpassword")
        assert_error(status, body, 400)

    @allure.title("Admin login non-existent")
    def test_admin_login_nonexistent(self, anon_client):
        status, body = anon_client.admin_login("no_such_admin_999", "anything")
        assert_error(status, body, 400)


@allure.feature("Auth — Token")
class TestToken:

    @allure.title("Token works for authenticated endpoints")
    def test_token_access_control(self, player_client):
        status, body = player_client.get_favorites()
        assert_status(status, 200)
        assert_has_key(body, "favorites")

    @allure.title("Invalid token gets 401")
    def test_invalid_token(self, anon_client):
        from utils.api_client import Client
        bad = Client(token="invalid-token-12345")
        status, body = bad.get_favorites()
        assert status == 401, f"Expected 401, got {status}: {body}"

    @allure.title("Missing token gets 401")
    def test_no_token(self, anon_client):
        status, body = anon_client.get_favorites()
        assert status == 401, f"Expected 401, got {status}: {body}"


@allure.feature("Auth — Favorites")
class TestFavorites:

    @allure.title("Full favorites lifecycle: add → list → remove")
    def test_favorites_flow(self, player_client, anon_client):
        # Find a tactic to favorite
        _, data = anon_client.list_tactics({"page_size": 1})
        if not data["items"]:
            pytest.skip("No tactics available")
        tactic_id = data["items"][0]["id"]

        # Add
        status, body = player_client.add_favorite(tactic_id)
        assert_status(status, 200)

        # List — should contain it
        status, body = player_client.get_favorites()
        assert_status(status, 200)
        fav_ids = [f["id"] for f in body["favorites"]]
        assert tactic_id in fav_ids, f"Tactic {tactic_id} not in favorites"

        # Remove
        status, body = player_client.remove_favorite(tactic_id)
        assert_status(status, 200)

        # List — should be gone
        status, body = player_client.get_favorites()
        fav_ids = [f["id"] for f in body["favorites"]]
        assert tactic_id not in fav_ids

    @allure.title("Track recent tactic")
    def test_recent(self, player_client, anon_client):
        _, data = anon_client.list_tactics({"page_size": 1})
        if not data["items"]:
            pytest.skip("No tactics available")
        tactic_id = data["items"][0]["id"]
        status, body = player_client.track_recent(tactic_id)
        assert_status(status, 200)
        status, body = player_client.get_favorites()
        assert_status(status, 200)
        assert tactic_id in body.get("recent", [])
