from __future__ import annotations

from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from followdesk.app import create_app
from followdesk.config import Settings

PROJECT_ROOT = Path(__file__).parents[1]


@pytest.fixture
def settings(tmp_path: Path) -> Settings:
    return Settings(
        app_env="test",
        admin_token="test-admin-token",
        webhook_token="test-webhook-token",
        database_path=tmp_path / "followdesk.db",
        business_file=PROJECT_ROOT / "data" / "business.json",
        sequence_file=PROJECT_ROOT / "data" / "sequence.json",
        email_provider="demo",
        smtp_host="",
        smtp_port=587,
        smtp_username="",
        smtp_password="",
        smtp_use_tls=True,
        followup_worker_enabled=False,
        followup_poll_seconds=60,
        lead_rate_limit_per_minute=50,
        cors_origins=(),
    )


@pytest.fixture
def client(settings: Settings) -> TestClient:
    with TestClient(create_app(settings)) as test_client:
        yield test_client


@pytest.fixture
def admin_headers() -> dict[str, str]:
    return {"X-Admin-Token": "test-admin-token"}


@pytest.fixture
def lead_payload() -> dict[str, object]:
    return {
        "name": "Alex Morgan",
        "email": "alex@example.com",
        "phone": "",
        "company": "Morgan House",
        "service": "Deep cleaning",
        "message": "We need help before moving weekend.",
        "source": "test-form",
        "consent": True,
    }
