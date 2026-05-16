"""Test configuration — override via environment variables."""

import os

# ── Target endpoints ───────────────────────────────────
API_BASE = os.getenv("TEST_API_BASE", "http://127.0.0.1:8008")
WEB_BASE = os.getenv("TEST_WEB_BASE", "http://127.0.0.1:5174")
ADMIN_BASE = os.getenv("TEST_ADMIN_BASE", "http://127.0.0.1:5175")

# ── Test accounts ───────────────────────────────────────
ADMIN_USERNAME = os.getenv("TEST_ADMIN_USERNAME", "admin")
ADMIN_PASSWORD = os.getenv("TEST_ADMIN_PASSWORD", "Gyh159951.")

PLAYER_USERNAME = os.getenv("TEST_PLAYER_USERNAME", "testrunner")
PLAYER_EMAIL = os.getenv("TEST_PLAYER_EMAIL", "testrunner@test.com")
PLAYER_PASSWORD = os.getenv("TEST_PLAYER_PASSWORD", "test123456")

# ── ZenTao integration ──────────────────────────────────
ZENTAO_URL = os.getenv("ZENTAO_URL", "")
ZENTAO_USERNAME = os.getenv("ZENTAO_USERNAME", "")
ZENTAO_PASSWORD = os.getenv("ZENTAO_PASSWORD", "")
ZENTAO_PRODUCT_ID = int(os.getenv("ZENTAO_PRODUCT_ID", "1"))

# ── Timing ──────────────────────────────────────────────
REQUEST_TIMEOUT = int(os.getenv("TEST_TIMEOUT", "15"))
RATE_LIMIT_REQUESTS = 130  # must exceed global limit (120/min)

# ── Allure ──────────────────────────────────────────────
ALLURE_RESULTS_DIR = os.getenv("ALLURE_RESULTS_DIR", "allure-results")
