import hashlib
import hmac

import pytest
from fastapi import HTTPException


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
