from __future__ import annotations

import asyncio
import csv
import hmac
import io
import re
import time
from collections import defaultdict, deque
from collections.abc import AsyncIterator
from contextlib import asynccontextmanager, suppress
from pathlib import Path
from threading import Lock
from typing import Annotated, Any, Literal

import uvicorn
from fastapi import BackgroundTasks, Depends, FastAPI, Header, HTTPException, Request, status
from fastapi.middleware.cors import CORSMiddleware
from fastapi.responses import FileResponse, StreamingResponse
from fastapi.staticfiles import StaticFiles
from pydantic import BaseModel, ConfigDict, Field, field_validator, model_validator

from .config import Settings
from .mailer import Mailer
from .storage import Storage

STATIC_DIR = Path(__file__).parent / "static"
EMAIL_RE = re.compile(r"^[^\s@]+@[^\s@]+\.[^\s@]+$")
HEX_RE = re.compile(r"^#[0-9a-fA-F]{6}$")
VALID_STATUSES = {"new", "contacted", "qualified", "booked", "won", "lost"}
VALID_PRIORITIES = {"low", "normal", "high"}
VALID_BOOKING_STATUSES = {"not_booked", "booked", "completed", "cancelled"}


class SlidingWindowLimiter:
    def __init__(self, requests_per_minute: int) -> None:
        self.limit = requests_per_minute
        self.events: dict[str, deque[float]] = defaultdict(deque)

    def allow(self, key: str) -> bool:
        current = time.monotonic()
        bucket = self.events[key]
        while bucket and bucket[0] < current - 60:
            bucket.popleft()
        if len(bucket) >= self.limit:
            return False
        bucket.append(current)
        return True


class LeadRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=100)
    email: str = Field(default="", max_length=200)
    phone: str = Field(default="", max_length=40)
    company: str = Field(default="", max_length=120)
    service: str = Field(min_length=2, max_length=120)
    message: str = Field(default="", max_length=1500)
    source: str = Field(default="website", max_length=120)
    consent: bool = True
    website: str = Field(default="", max_length=200, exclude=True)

    @field_validator("email")
    @classmethod
    def validate_email(cls, value: str) -> str:
        if value and not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value

    @model_validator(mode="after")
    def validate_contact(self) -> LeadRequest:
        if not self.email and not self.phone:
            raise ValueError("Provide an email address or phone number")
        if not self.consent:
            raise ValueError("Consent is required so the business can follow up")
        if self.website:
            raise ValueError("Request could not be accepted")
        return self


class LeadWebhookEnvelope(BaseModel):
    event: Literal["lead.created"]
    lead: LeadRequest


class LeadUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    status: str | None = None
    priority: str | None = None
    owner: str | None = Field(default=None, max_length=100)
    booking_status: str | None = None
    next_follow_up_at: str | None = None

    @field_validator("status")
    @classmethod
    def validate_status(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_STATUSES:
            raise ValueError("Invalid lead status")
        return value

    @field_validator("priority")
    @classmethod
    def validate_priority(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_PRIORITIES:
            raise ValueError("Invalid priority")
        return value

    @field_validator("booking_status")
    @classmethod
    def validate_booking(cls, value: str | None) -> str | None:
        if value is not None and value not in VALID_BOOKING_STATUSES:
            raise ValueError("Invalid booking status")
        return value


class NoteRequest(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    body: str = Field(min_length=2, max_length=2000)


class BusinessUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    name: str = Field(min_length=2, max_length=120)
    short_name: str = Field(min_length=1, max_length=40)
    tagline: str = Field(min_length=2, max_length=160)
    logo_text: str = Field(min_length=1, max_length=3)
    primary_color: str
    accent_color: str
    contact_email: str = Field(max_length=200)
    sender_name: str = Field(min_length=2, max_length=100)
    reply_to: str = Field(max_length=200)
    booking_url: str = Field(default="", max_length=500)
    service_options: list[str] = Field(min_length=1, max_length=20)
    privacy_url: str = Field(default="", max_length=500)
    response_promise: str = Field(min_length=2, max_length=300)

    @field_validator("primary_color", "accent_color")
    @classmethod
    def validate_color(cls, value: str) -> str:
        if not HEX_RE.match(value):
            raise ValueError("Use a six-digit hex color such as #5b4df7")
        return value

    @field_validator("contact_email", "reply_to")
    @classmethod
    def validate_business_email(cls, value: str) -> str:
        if value and not EMAIL_RE.match(value):
            raise ValueError("Enter a valid email address")
        return value

    @field_validator("booking_url", "privacy_url")
    @classmethod
    def validate_url(cls, value: str) -> str:
        if value and not value.startswith(("https://", "http://")):
            raise ValueError("URL must begin with https:// or http://")
        return value


class SequenceUpdate(BaseModel):
    model_config = ConfigDict(str_strip_whitespace=True)
    delay_hours: int = Field(ge=0, le=8760)
    name: str = Field(min_length=2, max_length=100)
    subject: str = Field(min_length=2, max_length=200)
    body: str = Field(min_length=10, max_length=5000)
    enabled: bool = True


def csv_safe(value: Any) -> Any:
    if isinstance(value, str) and value[:1] in "=+-@":
        return "'" + value
    return value


def create_app(settings: Settings | None = None) -> FastAPI:
    active_settings = settings or Settings.from_env()
    active_settings.validate()
    storage = Storage(active_settings.database_path)
    storage.initialize(active_settings.load_business(), active_settings.load_sequence())
    mailer = Mailer(active_settings)
    lead_limiter = SlidingWindowLimiter(active_settings.lead_rate_limit_per_minute)
    processing_lock = Lock()

    def process_followups() -> dict[str, int]:
        if not processing_lock.acquire(blocking=False):
            return {"processed": 0, "failed": 0}
        processed = 0
        failed = 0
        try:
            for message in storage.due_messages():
                try:
                    if not storage.message_is_pending(message["id"]):
                        continue
                    provider = mailer.send(message, storage.get_settings())
                    storage.mark_message_sent(message["id"], provider)
                    processed += 1
                except Exception as exc:  # Provider errors do not stop later messages.
                    storage.mark_message_failed(message["id"], str(exc))
                    failed += 1
            return {"processed": processed, "failed": failed}
        finally:
            processing_lock.release()

    async def worker() -> None:
        while True:
            await asyncio.to_thread(process_followups)
            await asyncio.sleep(active_settings.followup_poll_seconds)

    @asynccontextmanager
    async def lifespan(_: FastAPI) -> AsyncIterator[None]:
        task = None
        if active_settings.followup_worker_enabled:
            task = asyncio.create_task(worker())
        yield
        if task:
            task.cancel()
            with suppress(asyncio.CancelledError):
                await task

    app = FastAPI(
        title="FollowDesk",
        version="1.0.0",
        docs_url=None,
        redoc_url=None,
        openapi_url=None,
        lifespan=lifespan,
    )
    app.state.settings = active_settings
    app.state.storage = storage
    app.state.process_followups = process_followups
    app.mount("/assets", StaticFiles(directory=STATIC_DIR), name="assets")

    if active_settings.cors_origins:
        app.add_middleware(
            CORSMiddleware,
            allow_origins=list(active_settings.cors_origins),
            allow_credentials=False,
            allow_methods=["GET", "POST", "PUT"],
            allow_headers=["Content-Type", "X-Admin-Token", "X-Webhook-Token"],
        )

    @app.middleware("http")
    async def security_headers(request: Request, call_next: Any) -> Any:
        response = await call_next(request)
        response.headers["X-Content-Type-Options"] = "nosniff"
        response.headers["Referrer-Policy"] = "strict-origin-when-cross-origin"
        response.headers["Permissions-Policy"] = "camera=(), microphone=(), geolocation=()"
        if request.url.path.startswith(("/admin", "/api/admin")):
            response.headers["Cache-Control"] = "no-store"
        return response

    def require_admin(
        x_admin_token: Annotated[str | None, Header(alias="X-Admin-Token")] = None,
    ) -> None:
        if not x_admin_token or not hmac.compare_digest(x_admin_token, active_settings.admin_token):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    def require_webhook(
        x_webhook_token: Annotated[str | None, Header(alias="X-Webhook-Token")] = None,
    ) -> None:
        if not x_webhook_token or not hmac.compare_digest(
            x_webhook_token, active_settings.webhook_token
        ):
            raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, detail="Unauthorized")

    @app.get("/", include_in_schema=False)
    async def home() -> FileResponse:
        return FileResponse(STATIC_DIR / "index.html")

    @app.get("/admin", include_in_schema=False)
    async def admin() -> FileResponse:
        return FileResponse(STATIC_DIR / "admin.html")

    @app.get("/health")
    async def health() -> dict[str, Any]:
        if not storage.ping():
            raise HTTPException(status_code=503, detail="Storage is unavailable")
        return {
            "status": "ok",
            "product": "FollowDesk",
            "version": "1.0.0",
            "storage": "ok",
            "email_provider": active_settings.email_provider,
            "environment": active_settings.app_env,
        }

    @app.get("/api/config")
    async def public_config() -> dict[str, Any]:
        business = storage.get_settings()
        return {
            "name": business["name"],
            "short_name": business["short_name"],
            "tagline": business["tagline"],
            "logo_text": business["logo_text"],
            "primary_color": business["primary_color"],
            "accent_color": business["accent_color"],
            "booking_url": business.get("booking_url", ""),
            "service_options": business["service_options"],
            "privacy_url": business.get("privacy_url", ""),
            "response_promise": business["response_promise"],
        }

    @app.post("/api/leads", status_code=201)
    async def create_lead(
        payload: LeadRequest, background_tasks: BackgroundTasks, request: Request
    ) -> dict[str, Any]:
        client_host = request.client.host if request.client else "unknown"
        if not lead_limiter.allow(client_host):
            raise HTTPException(
                status_code=429, detail="Too many requests. Please wait before trying again."
            )
        lead = storage.create_lead(payload.model_dump())
        background_tasks.add_task(process_followups)
        business = storage.get_settings()
        return {
            "id": lead["id"],
            "status": lead["status"],
            "booking_url": business.get("booking_url", ""),
            "message": f"Thanks, {payload.name}. {business['name']} received your request.",
        }

    @app.post("/api/webhooks/leads", status_code=201, dependencies=[Depends(require_webhook)])
    async def webhook_lead(
        payload: LeadRequest | LeadWebhookEnvelope, background_tasks: BackgroundTasks
    ) -> dict[str, str]:
        if isinstance(payload, LeadWebhookEnvelope):
            values = payload.lead.model_dump()
            values["source"] = "LeadDesk AI"
        else:
            values = payload.model_dump()
            if values["source"] == "website":
                values["source"] = "webhook"
        lead = storage.create_lead(values)
        background_tasks.add_task(process_followups)
        return {"id": lead["id"], "status": "accepted"}

    @app.get("/api/admin/stats", dependencies=[Depends(require_admin)])
    async def admin_stats() -> dict[str, Any]:
        return storage.stats()

    @app.get("/api/admin/leads", dependencies=[Depends(require_admin)])
    async def admin_leads(status_filter: str = "", search: str = "") -> list[dict[str, Any]]:
        if status_filter and status_filter not in VALID_STATUSES:
            raise HTTPException(status_code=400, detail="Invalid status filter")
        return storage.list_leads(status_filter, search)

    @app.get("/api/admin/leads/{lead_id}", dependencies=[Depends(require_admin)])
    async def admin_lead(lead_id: str) -> dict[str, Any]:
        lead = storage.get_lead(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead

    @app.put("/api/admin/leads/{lead_id}", dependencies=[Depends(require_admin)])
    async def update_lead(lead_id: str, payload: LeadUpdate) -> dict[str, Any]:
        values = payload.model_dump(exclude_none=True)
        if values.get("status") == "booked" and "booking_status" not in values:
            values["booking_status"] = "booked"
        lead = storage.update_lead(lead_id, values)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead

    @app.post("/api/admin/leads/{lead_id}/stop-followups", dependencies=[Depends(require_admin)])
    async def stop_followups(lead_id: str) -> dict[str, Any]:
        lead = storage.stop_followups(lead_id)
        if not lead:
            raise HTTPException(status_code=404, detail="Lead not found")
        return lead

    @app.post("/api/admin/leads/{lead_id}/notes", dependencies=[Depends(require_admin)])
    async def add_note(lead_id: str, payload: NoteRequest) -> dict[str, Any]:
        note = storage.add_note(lead_id, payload.body)
        if not note:
            raise HTTPException(status_code=404, detail="Lead not found")
        return note

    @app.get("/api/admin/outbox", dependencies=[Depends(require_admin)])
    async def admin_outbox() -> list[dict[str, Any]]:
        return storage.list_outbox()

    @app.post("/api/admin/process-followups", dependencies=[Depends(require_admin)])
    async def process_now() -> dict[str, int]:
        return await asyncio.to_thread(process_followups)

    @app.get("/api/admin/settings", dependencies=[Depends(require_admin)])
    async def admin_settings() -> dict[str, Any]:
        return storage.get_settings()

    @app.put("/api/admin/settings", dependencies=[Depends(require_admin)])
    async def update_settings(payload: BusinessUpdate) -> dict[str, Any]:
        return storage.update_settings(payload.model_dump())

    @app.get("/api/admin/sequence", dependencies=[Depends(require_admin)])
    async def admin_sequence() -> list[dict[str, Any]]:
        return storage.list_sequence()

    @app.put("/api/admin/sequence/{step}", dependencies=[Depends(require_admin)])
    async def update_sequence(step: int, payload: SequenceUpdate) -> dict[str, Any]:
        result = storage.update_sequence_step(step, payload.model_dump())
        if not result:
            raise HTTPException(status_code=404, detail="Sequence step not found")
        return result

    @app.get("/api/admin/leads.csv", dependencies=[Depends(require_admin)])
    async def export_leads() -> StreamingResponse:
        leads = storage.list_leads(limit=5000)
        fieldnames = [
            "id", "created_at", "name", "email", "phone", "company", "service",
            "message", "source", "status", "priority", "owner", "booking_status",
            "last_contacted_at", "next_follow_up_at",
        ]
        output = io.StringIO()
        writer = csv.DictWriter(output, fieldnames=fieldnames, extrasaction="ignore")
        writer.writeheader()
        for lead in leads:
            writer.writerow({key: csv_safe(value) for key, value in lead.items()})
        return StreamingResponse(
            iter([output.getvalue()]),
            media_type="text/csv",
            headers={"Content-Disposition": 'attachment; filename="followdesk-leads.csv"'},
        )

    return app


app = create_app()


def run() -> None:
    uvicorn.run("followdesk.app:app", host="0.0.0.0", port=8000, reload=False)
