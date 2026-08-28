from __future__ import annotations

from dataclasses import replace

from fastapi.testclient import TestClient

from followdesk.app import create_app
from followdesk.config import Settings


def test_health_and_public_pages(client: TestClient) -> None:
    health = client.get("/health")
    assert health.status_code == 200
    assert health.json()["product"] == "FollowDesk"
    assert health.json()["email_provider"] == "demo"
    assert client.get("/").status_code == 200
    assert client.get("/admin").status_code == 200
    assert client.get("/assets/styles.css").status_code == 200


def test_admin_requires_private_token(client: TestClient) -> None:
    assert client.get("/api/admin/stats").status_code == 401
    assert client.get(
        "/api/admin/stats", headers={"X-Admin-Token": "wrong-token"}
    ).status_code == 401


def test_capture_schedules_and_processes_sequence(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    response = client.post("/api/leads", json=lead_payload)
    assert response.status_code == 201
    lead_id = response.json()["id"]
    assert response.json()["booking_url"].startswith("https://")

    lead = client.get(f"/api/admin/leads/{lead_id}", headers=admin_headers).json()
    assert lead["status"] == "new"
    assert len(lead["followups"]) == 4
    assert lead["followups"][0]["status"] == "sent"
    assert lead["followups"][0]["provider"] == "demo"
    assert lead["followups"][1]["status"] == "pending"
    assert "Alex" in lead["followups"][0]["body"]
    assert "Deep cleaning" in lead["followups"][0]["body"]

    stats = client.get("/api/admin/stats", headers=admin_headers).json()
    assert stats["total_leads"] == 1
    assert stats["emails_sent"] == 1


def test_phone_only_lead_has_no_email_sequence(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    lead_payload["email"] = ""
    lead_payload["phone"] = "+1 555 0100"
    response = client.post("/api/leads", json=lead_payload)
    lead = client.get(
        f"/api/admin/leads/{response.json()['id']}", headers=admin_headers
    ).json()
    assert lead["followups"] == []


def test_booking_stops_pending_followups(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    lead_id = client.post("/api/leads", json=lead_payload).json()["id"]
    updated = client.put(
        f"/api/admin/leads/{lead_id}",
        headers=admin_headers,
        json={"status": "booked"},
    )
    assert updated.status_code == 200
    assert updated.json()["booking_status"] == "booked"
    result = client.post("/api/admin/process-followups", headers=admin_headers).json()
    assert result == {"processed": 0, "failed": 0}


def test_notes_and_filters(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    lead_id = client.post("/api/leads", json=lead_payload).json()["id"]
    note = client.post(
        f"/api/admin/leads/{lead_id}/notes",
        headers=admin_headers,
        json={"body": "Customer prefers an afternoon call."},
    )
    assert note.status_code == 200
    assert note.json()["kind"] == "note"
    results = client.get(
        "/api/admin/leads?status_filter=new&search=Alex", headers=admin_headers
    ).json()
    assert len(results) == 1
    assert results[0]["id"] == lead_id


def test_webhook_uses_separate_secret(
    client: TestClient, lead_payload: dict[str, object]
) -> None:
    assert client.post("/api/webhooks/leads", json=lead_payload).status_code == 401
    response = client.post(
        "/api/webhooks/leads",
        headers={"X-Webhook-Token": "test-webhook-token"},
        json=lead_payload,
    )
    assert response.status_code == 201
    assert response.json()["status"] == "accepted"


def test_accepts_leaddesk_webhook_envelope(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    response = client.post(
        "/api/webhooks/leads",
        headers={"X-Webhook-Token": "test-webhook-token"},
        json={"event": "lead.created", "lead": lead_payload},
    )
    assert response.status_code == 201
    leads = client.get("/api/admin/leads", headers=admin_headers).json()
    assert leads[0]["source"] == "LeadDesk AI"


def test_settings_and_sequence_are_editable(
    client: TestClient, admin_headers: dict[str, str]
) -> None:
    settings = client.get("/api/admin/settings", headers=admin_headers).json()
    settings["name"] = "Acme Services"
    settings["primary_color"] = "#112233"
    response = client.put("/api/admin/settings", headers=admin_headers, json=settings)
    assert response.status_code == 200
    assert client.get("/api/config").json()["name"] == "Acme Services"

    step = client.get("/api/admin/sequence", headers=admin_headers).json()[1]
    step["delay_hours"] = 12
    updated = client.put(
        f"/api/admin/sequence/{step['step']}", headers=admin_headers, json=step
    )
    assert updated.status_code == 200
    assert updated.json()["delay_hours"] == 12


def test_csv_export_blocks_formula_injection(
    client: TestClient, admin_headers: dict[str, str], lead_payload: dict[str, object]
) -> None:
    lead_payload["name"] = "=SUM(A1:A2)"
    client.post("/api/leads", json=lead_payload)
    response = client.get("/api/admin/leads.csv", headers=admin_headers)
    assert response.status_code == 200
    assert "'=SUM(A1:A2)" in response.text


def test_validation_rejects_bad_contact_and_consent(
    client: TestClient, lead_payload: dict[str, object]
) -> None:
    lead_payload["email"] = "not-an-email"
    assert client.post("/api/leads", json=lead_payload).status_code == 422
    lead_payload["email"] = "valid@example.com"
    lead_payload["consent"] = False
    assert client.post("/api/leads", json=lead_payload).status_code == 422


def test_honeypot_rejects_bot_submission(
    client: TestClient, lead_payload: dict[str, object]
) -> None:
    lead_payload["website"] = "https://spam.example"
    assert client.post("/api/leads", json=lead_payload).status_code == 422


def test_public_capture_is_rate_limited(
    settings: Settings, lead_payload: dict[str, object]
) -> None:
    limited = replace(settings, lead_rate_limit_per_minute=1)
    with TestClient(create_app(limited)) as client:
        assert client.post("/api/leads", json=lead_payload).status_code == 201
        assert client.post("/api/leads", json=lead_payload).status_code == 429
