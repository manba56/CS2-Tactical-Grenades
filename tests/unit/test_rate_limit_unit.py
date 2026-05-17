"""Unit tests for cs2-api/app/rate_limit.py — RateLimiter, IP extraction."""

import time
import pytest
import allure
from unittest.mock import MagicMock


class TestRateLimiter:
    """Direct tests for the RateLimiter class in isolation."""

    def test_first_request_allowed(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)
        assert limiter.is_allowed("192.168.1.1") is True

    def test_under_limit_all_allowed(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)
        for _ in range(4):
            assert limiter.is_allowed("192.168.1.1") is True

    def test_at_limit(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=3, window_seconds=60)
        assert limiter.is_allowed("ip") is True
        assert limiter.is_allowed("ip") is True
        assert limiter.is_allowed("ip") is True  # 3rd — still allowed

    def test_exceeded_limit(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=3, window_seconds=60)
        for _ in range(3):
            limiter.is_allowed("ip")
        assert limiter.is_allowed("ip") is False  # 4th — denied

    def test_window_expiry(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=0.05)  # 50ms window
        limiter.is_allowed("ip")
        limiter.is_allowed("ip")
        assert limiter.is_allowed("ip") is False  # exceeded
        time.sleep(0.1)  # wait for window to expire
        assert limiter.is_allowed("ip") is True  # allowed again

    def test_different_keys_independent(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=2, window_seconds=60)
        limiter.is_allowed("ip1")
        limiter.is_allowed("ip1")
        assert limiter.is_allowed("ip1") is False  # ip1 exceeded
        assert limiter.is_allowed("ip2") is True    # ip2 still fresh

    def test_periodic_cleanup_triggers(self):
        """When _hits exceeds 10000 keys, empty buckets are swept."""
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=5, window_seconds=60)
        # Exceed the cleanup threshold
        for i in range(11000):
            limiter.is_allowed(f"ip_{i}")
        # Should still function after cleanup
        assert limiter.is_allowed("new_ip") is True

    def test_custom_params(self):
        from app.rate_limit import RateLimiter

        limiter = RateLimiter(max_requests=1, window_seconds=3600)
        assert limiter.is_allowed("x") is True
        assert limiter.is_allowed("x") is False


class TestCheckRateLimit:
    """Tests for the module-level check_rate_limit dispatcher."""

    def test_global_limiter_used_when_strict_false(self):
        from app.rate_limit import check_rate_limit, _limiter

        # Clear any existing state by checking a unique IP
        ip = f"test_global_{time.time()}"
        for _ in range(_limiter.max_requests):
            assert check_rate_limit(ip, strict=False) is True
        assert check_rate_limit(ip, strict=False) is False

    def test_strict_limiter_used_when_strict_true(self):
        from app.rate_limit import check_rate_limit, _auth_limiter

        ip = f"test_strict_{time.time()}"
        for _ in range(_auth_limiter.max_requests):
            assert check_rate_limit(ip, strict=True) is True
        assert check_rate_limit(ip, strict=True) is False

    def test_global_and_strict_independent(self):
        from app.rate_limit import check_rate_limit, _limiter, _auth_limiter

        ip = f"test_both_{time.time()}"
        # Exhaust the strict limiter
        for _ in range(_auth_limiter.max_requests):
            check_rate_limit(ip, strict=True)
        # Global should still be available
        assert check_rate_limit(ip, strict=False) is True


class TestGetClientIp:
    """Tests for client IP extraction from request headers."""

    def test_x_forwarded_for_single_ip(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {"X-Forwarded-For": "1.2.3.4"}
        assert get_client_ip(req) == "1.2.3.4"

    def test_x_forwarded_for_multiple_ips(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {"X-Forwarded-For": " 1.2.3.4 , 5.6.7.8 "}
        assert get_client_ip(req) == "1.2.3.4"

    def test_x_real_ip_fallback(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {"X-Real-IP": "9.9.9.9"}
        assert get_client_ip(req) == "9.9.9.9"

    def test_forwarded_takes_priority_over_real_ip(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {"X-Forwarded-For": "1.1.1.1", "X-Real-IP": "2.2.2.2"}
        assert get_client_ip(req) == "1.1.1.1"

    def test_direct_client_host(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {}
        req.client = MagicMock()
        req.client.host = "10.0.0.1"
        assert get_client_ip(req) == "10.0.0.1"

    def test_client_none_fallback(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {}
        req.client = None
        assert get_client_ip(req) == "127.0.0.1"

    def test_client_host_none_fallback(self):
        from app.rate_limit import get_client_ip

        req = MagicMock()
        req.headers = {}
        req.client = MagicMock()
        req.client.host = None
        assert get_client_ip(req) == "127.0.0.1"
