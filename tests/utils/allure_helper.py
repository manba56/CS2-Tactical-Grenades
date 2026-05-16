"""Allure reporting helpers — wraps common assertions with @allure.step."""

from __future__ import annotations

import allure


@allure.step("Assert status code {expected}")
def assert_status(status: int, expected: int) -> None:
    assert status == expected, f"Expected {expected}, got {status}"


@allure.step("Assert JSON response contains key '{key}'")
def assert_has_key(data: dict, key: str) -> None:
    assert key in data, f"Key '{key}' not in response: {list(data.keys())[:10]}"


@allure.step("Assert list is not empty")
def assert_not_empty(items: list) -> None:
    assert len(items) > 0, "Expected non-empty list"


@allure.step("Assert field '{key}' == {expected}")
def assert_field(data: dict, key: str, expected) -> None:
    actual = data.get(key)
    assert actual == expected, f"data['{key}'] = {actual!r}, expected {expected!r}"


@allure.step("Assert response is error ({status}, '{detail_contains}')")
def assert_error(status: int, body: dict, expected_status: int, detail_contains: str = "") -> None:
    assert status == expected_status, f"Expected {expected_status}, got {status}"
    detail = body.get("detail", "")
    if detail_contains:
        assert detail_contains.lower() in detail.lower(), f"detail='{detail}', expected contains '{detail_contains}'"


@allure.step("Attach response body")
def attach_body(body: dict | list) -> None:
    import json
    allure.attach(
        json.dumps(body, indent=2, ensure_ascii=False),
        name="response",
        attachment_type=allure.attachment_type.JSON,
    )
