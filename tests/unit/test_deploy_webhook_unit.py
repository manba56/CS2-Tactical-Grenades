import hashlib
import hmac

import pytest
from fastapi import HTTPException
from fastapi.testclient import TestClient


def test_deploy_webhook_rejects_when_secret_missing(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "DEPLOY_WEBHOOK_SECRET", "")

    with pytest.raises(HTTPException) as exc:
        main.verify_deploy_webhook(b"{}", None, None)

    assert exc.value.status_code == 503


def test_deploy_webhook_accepts_github_signature(monkeypatch):
    from app import main

    raw_body = b'{"ref":"refs/heads/main"}'
    secret = "test-secret"
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    monkeypatch.setattr(main, "DEPLOY_WEBHOOK_SECRET", secret)

    main.verify_deploy_webhook(raw_body, f"sha256={digest}", None)


def test_deploy_webhook_accepts_plain_deploy_secret(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "DEPLOY_WEBHOOK_SECRET", "test-secret")

    main.verify_deploy_webhook(b"{}", None, "test-secret")


def test_deploy_webhook_rejects_bad_secret(monkeypatch):
    from app import main

    monkeypatch.setattr(main, "DEPLOY_WEBHOOK_SECRET", "test-secret")

    with pytest.raises(HTTPException) as exc:
        main.verify_deploy_webhook(b"{}", None, "wrong-secret")

    assert exc.value.status_code == 401


def test_deploy_webhook_accepts_quickly_and_schedules_background_task(monkeypatch):
    from app import main

    started_refs: list[str] = []
    raw_body = b'{"ref":"refs/heads/main"}'
    secret = "test-secret"
    digest = hmac.new(secret.encode("utf-8"), raw_body, hashlib.sha256).hexdigest()

    monkeypatch.setattr(main, "DEPLOY_WEBHOOK_SECRET", secret)
    monkeypatch.setattr(main, "start_deploy_process", lambda ref: started_refs.append(ref))

    client = TestClient(main.app)
    response = client.post(
        "/api/webhook/deploy",
        content=raw_body,
        headers={"x-hub-signature-256": f"sha256={digest}"},
    )

    assert response.status_code == 200
    assert response.json()["status"] == "accepted"
    assert started_refs == ["refs/heads/main"]
