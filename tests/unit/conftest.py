"""Unit test fixtures — no API server required."""

import sys
from pathlib import Path

import allure

# Allow importing from cs2-api/app/ directly
API_DIR = Path(__file__).resolve().parent.parent.parent / "cs2-api"
if str(API_DIR) not in sys.path:
    sys.path.insert(0, str(API_DIR))


import pytest


@pytest.fixture(autouse=True)
def _tag_unit():
    """Tag every unit test with Allure label."""
    allure.dynamic.tag("unit")
