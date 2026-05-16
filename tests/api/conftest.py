"""API test fixtures — no extra fixtures needed; use root conftest."""

import pytest


@pytest.fixture(autouse=True)
def allure_api_tag():
    import allure
    allure.dynamic.tag("api")
