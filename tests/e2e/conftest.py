"""Playwright E2E fixtures with Allure integration."""

from __future__ import annotations

import pytest
import allure

import config


@pytest.fixture(scope="session")
def browser_context_args(browser_context_args: dict) -> dict:
    return {
        **browser_context_args,
        "viewport": {"width": 1440, "height": 900},
        "locale": "zh-CN",
        "ignore_https_errors": True,
    }


@pytest.fixture(autouse=True)
def allure_e2e_tag():
    allure.dynamic.tag("e2e")


@pytest.fixture(autouse=True)
def screenshot_on_failure(page, request):
    """Auto-attach screenshot to Allure on test failure."""
    yield
    if request.node.rep_call.failed if hasattr(request.node, "rep_call") else False:
        import uuid
        png_bytes = page.screenshot(full_page=False)
        allure.attach(
            png_bytes,
            name=f"failure-{request.node.name[:60]}.png",
            attachment_type=allure.attachment_type.PNG,
        )
