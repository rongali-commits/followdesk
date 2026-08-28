from __future__ import annotations

from dataclasses import replace

import pytest

from followdesk.config import Settings


def test_production_rejects_weak_secrets(settings: Settings) -> None:
    production = replace(settings, app_env="production")
    with pytest.raises(RuntimeError, match="ADMIN_TOKEN"):
        production.validate()


def test_smtp_requires_host(settings: Settings) -> None:
    smtp = replace(settings, email_provider="smtp", smtp_host="")
    with pytest.raises(RuntimeError, match="SMTP_HOST"):
        smtp.validate()


def test_production_accepts_strong_separate_secrets(settings: Settings) -> None:
    production = replace(
        settings,
        app_env="production",
        admin_token="a-strong-admin-secret-value-123",
        webhook_token="a-separate-webhook-secret-456",
    )
    production.validate()
