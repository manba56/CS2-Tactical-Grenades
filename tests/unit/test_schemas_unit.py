"""Unit tests for cs2-api/app/schemas.py — Pydantic model validation."""

import pytest
import allure
from pydantic import ValidationError


class TestRegisterRequest:
    def test_valid(self):
        from app.schemas import RegisterRequest

        r = RegisterRequest(username="testuser", email="a@b.com", password="123456")
        assert r.username == "testuser"

    def test_username_too_short(self):
        from app.schemas import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(username="ab", email="a@b.com", password="123456")

    def test_username_too_long(self):
        from app.schemas import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(username="a" * 25, email="a@b.com", password="123456")

    def test_password_too_short(self):
        from app.schemas import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", email="a@b.com", password="12345")

    def test_email_too_short(self):
        from app.schemas import RegisterRequest

        with pytest.raises(ValidationError):
            RegisterRequest(username="testuser", email="a@b", password="123456")


class TestLoginRequest:
    def test_valid_username(self):
        from app.schemas import LoginRequest

        r = LoginRequest(username_or_email="testuser", password="123456")
        assert r.username_or_email == "testuser"

    def test_valid_email(self):
        from app.schemas import LoginRequest

        r = LoginRequest(username_or_email="test@example.com", password="123456")
        assert r.username_or_email == "test@example.com"

    def test_username_too_short(self):
        from app.schemas import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(username_or_email="ab", password="123456")

    def test_password_too_short(self):
        from app.schemas import LoginRequest

        with pytest.raises(ValidationError):
            LoginRequest(username_or_email="testuser", password="12345")


class TestAdminLoginRequest:
    def test_valid(self):
        from app.schemas import AdminLoginRequest

        r = AdminLoginRequest(username="admin", password="123456")
        assert r.username == "admin"


class TestMapPayload:
    def test_defaults(self):
        from app.schemas import MapPayload

        m = MapPayload(name="Test", slug="test", overview="Overview", cover_url="", layout_url="")
        assert m.callout_color == "#ff7a18"
        assert m.order == 0
        assert m.status == "draft"
        assert m.active_pool is True

    def test_invalid_status(self):
        from app.schemas import MapPayload

        with pytest.raises(ValidationError):
            MapPayload(name="M", slug="m", overview="O", cover_url="", layout_url="", status="deleted")


class TestPointPayload:
    def test_valid(self):
        from app.schemas import PointPayload

        p = PointPayload(map_id=1, name="A Site", key="a_site", x=50.0, y=50.0)
        assert p.side == "BOTH"
        assert p.point_type == "site"
        assert p.tags == []

    def test_x_out_of_range_negative(self):
        from app.schemas import PointPayload

        with pytest.raises(ValidationError):
            PointPayload(map_id=1, name="P", key="p", x=-0.1, y=50)

    def test_x_out_of_range_above_100(self):
        from app.schemas import PointPayload

        with pytest.raises(ValidationError):
            PointPayload(map_id=1, name="P", key="p", x=100.1, y=50)

    def test_y_out_of_range(self):
        from app.schemas import PointPayload

        with pytest.raises(ValidationError):
            PointPayload(map_id=1, name="P", key="p", x=50, y=150)

    def test_invalid_side(self):
        from app.schemas import PointPayload

        with pytest.raises(ValidationError):
            PointPayload(map_id=1, name="P", key="p", x=50, y=50, side="NORTH")

    def test_invalid_point_type(self):
        from app.schemas import PointPayload

        with pytest.raises(ValidationError):
            PointPayload(map_id=1, name="P", key="p", x=50, y=50, point_type="castle")


class TestLineupPayload:
    def test_valid(self):
        from app.schemas import LineupPayload

        l = LineupPayload(
            map_id=1, title="Test Lineup", slug="test-lineup",
            side="T", utility_type="smoke",
            start_point_id=1, aim_point_id=2, land_point_id=3,
            purpose="Block vision", summary="A lineup",
        )
        assert l.difficulty == "medium"
        assert l.steps == []
        assert l.media == []
        assert l.status == "draft"

    def test_invalid_side(self):
        from app.schemas import LineupPayload

        with pytest.raises(ValidationError):
            LineupPayload(
                map_id=1, title="TL", slug="tl", side="NORTH",
                utility_type="smoke", start_point_id=1, aim_point_id=2,
                land_point_id=3, purpose="Test", summary="S",
            )

    def test_invalid_utility_type(self):
        from app.schemas import LineupPayload

        with pytest.raises(ValidationError):
            LineupPayload(
                map_id=1, title="TL", slug="tl", side="T",
                utility_type="rocket", start_point_id=1, aim_point_id=2,
                land_point_id=3, purpose="Test", summary="S",
            )

    def test_invalid_difficulty(self):
        from app.schemas import LineupPayload

        with pytest.raises(ValidationError):
            LineupPayload(
                map_id=1, title="TL", slug="tl", side="T",
                utility_type="smoke", start_point_id=1, aim_point_id=2,
                land_point_id=3, purpose="Test", summary="S",
                difficulty="impossible",
            )


class TestTacticPayload:
    def test_valid_minimal(self):
        from app.schemas import TacticPayload

        t = TacticPayload(
            map_id=1, title="Test Tactic", slug="test-tactic",
            side="T", goal="A 点爆弹", phase="exec",
            players=3, summary="Summary", note="", cover_url="",
        )
        assert t.difficulty == "medium"
        assert t.status == "draft"
        assert t.featured is False

    def test_players_too_few(self):
        from app.schemas import TacticPayload

        with pytest.raises(ValidationError):
            TacticPayload(
                map_id=1, title="T", slug="t", side="T", goal="G",
                phase="exec", players=0, summary="S", note="", cover_url="",
            )

    def test_players_too_many(self):
        from app.schemas import TacticPayload

        with pytest.raises(ValidationError):
            TacticPayload(
                map_id=1, title="T", slug="t", side="T", goal="G",
                phase="exec", players=6, summary="S", note="", cover_url="",
            )

    def test_invalid_side(self):
        from app.schemas import TacticPayload

        with pytest.raises(ValidationError):
            TacticPayload(
                map_id=1, title="T", slug="t", side="WEST", goal="G",
                phase="exec", players=3, summary="S", note="", cover_url="",
            )

    def test_invalid_phase(self):
        from app.schemas import TacticPayload

        with pytest.raises(ValidationError):
            TacticPayload(
                map_id=1, title="T", slug="t", side="T", goal="G",
                phase="warmup", players=3, summary="S", note="", cover_url="",
            )


class TestDumpModel:
    def test_dump_model_dict(self):
        from app.schemas import RegisterRequest, dump_model

        r = RegisterRequest(username="testuser", email="a@b.com", password="123456")
        d = dump_model(r)
        assert d["username"] == "testuser"
        assert d["email"] == "a@b.com"
        assert "password" in d
