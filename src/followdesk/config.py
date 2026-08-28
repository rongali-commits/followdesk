from __future__ import annotations

import json
import os
from dataclasses import dataclass
from pathlib import Path
from typing import Any

from dotenv import load_dotenv


def _bool(value: str | None, default: bool) -> bool:
    if value is None:
        return default
    return value.strip().lower() in {"1", "true", "yes", "on"}


@dataclass(frozen=True)
class Settings:
    app_env: str
    admin_token: str
    webhook_token: str
    database_path: Path
    business_file: Path
    sequence_file: Path
    email_provider: str
    smtp_host: str
    smtp_port: int
    smtp_username: str
    smtp_password: str
    smtp_use_tls: bool
    followup_worker_enabled: bool
    followup_poll_seconds: int
    lead_rate_limit_per_minute: int
    cors_origins: tuple[str, ...]

    @classmethod
    def from_env(cls) -> Settings:
        load_dotenv()
        return cls(
            app_env=os.getenv("APP_ENV", "development").strip().lower(),
            admin_token=os.getenv("ADMIN_TOKEN", "development-admin-token"),
            webhook_token=os.getenv("WEBHOOK_TOKEN", "development-webhook-token"),
            database_path=Path(os.getenv("DATABASE_PATH", "runtime/followdesk.db")),
            business_file=Path(os.getenv("BUSINESS_FILE", "data/business.json")),
            sequence_file=Path(os.getenv("SEQUENCE_FILE", "data/sequence.json")),
            email_provider=os.getenv("EMAIL_PROVIDER", "demo").strip().lower(),
            smtp_host=os.getenv("SMTP_HOST", "").strip(),
            smtp_port=int(os.getenv("SMTP_PORT", "587")),
            smtp_username=os.getenv("SMTP_USERNAME", "").strip(),
            smtp_password=os.getenv("SMTP_PASSWORD", ""),
            smtp_use_tls=_bool(os.getenv("SMTP_USE_TLS"), True),
            followup_worker_enabled=_bool(os.getenv("FOLLOWUP_WORKER_ENABLED"), True),
            followup_poll_seconds=max(15, int(os.getenv("FOLLOWUP_POLL_SECONDS", "60"))),
            lead_rate_limit_per_minute=max(
                1, int(os.getenv("LEAD_RATE_LIMIT_PER_MINUTE", "8"))
            ),
            cors_origins=tuple(
                origin.strip()
                for origin in os.getenv("CORS_ORIGINS", "").split(",")
                if origin.strip()
            ),
        )

    def validate(self) -> None:
        if self.app_env == "production":
            for label, value in (
                ("ADMIN_TOKEN", self.admin_token),
                ("WEBHOOK_TOKEN", self.webhook_token),
            ):
                weak_value = value.startswith(("replace-", "development-"))
                if len(value) < 24 or weak_value:
                    raise RuntimeError(f"{label} must be a strong secret in production")
        if self.email_provider not in {"demo", "smtp"}:
            raise RuntimeError("EMAIL_PROVIDER must be demo or smtp")
        if self.email_provider == "smtp" and not self.smtp_host:
            raise RuntimeError("SMTP_HOST is required when EMAIL_PROVIDER is smtp")

    def load_business(self) -> dict[str, Any]:
        return json.loads(self.business_file.read_text(encoding="utf-8"))

    def load_sequence(self) -> list[dict[str, Any]]:
        return json.loads(self.sequence_file.read_text(encoding="utf-8"))
