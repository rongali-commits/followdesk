from __future__ import annotations

import json
import sqlite3
import uuid
from collections.abc import Iterator
from contextlib import contextmanager
from datetime import UTC, datetime, timedelta
from pathlib import Path
from typing import Any


def now_utc() -> datetime:
    return datetime.now(UTC)


def iso(value: datetime | None = None) -> str:
    return (value or now_utc()).isoformat(timespec="seconds")


class Storage:
    def __init__(self, database_path: Path) -> None:
        self.database_path = database_path
        self.database_path.parent.mkdir(parents=True, exist_ok=True)

    @contextmanager
    def connect(self) -> Iterator[sqlite3.Connection]:
        connection = sqlite3.connect(self.database_path, timeout=10)
        connection.row_factory = sqlite3.Row
        connection.execute("PRAGMA journal_mode=WAL")
        connection.execute("PRAGMA foreign_keys=ON")
        try:
            yield connection
            connection.commit()
        finally:
            connection.close()

    def initialize(
        self, business: dict[str, Any], sequence: list[dict[str, Any]]
    ) -> None:
        with self.connect() as connection:
            connection.executescript(
                """
                CREATE TABLE IF NOT EXISTS settings (
                    key TEXT PRIMARY KEY,
                    value TEXT NOT NULL,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS sequence_steps (
                    step INTEGER PRIMARY KEY,
                    delay_hours INTEGER NOT NULL,
                    name TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    enabled INTEGER NOT NULL DEFAULT 1,
                    updated_at TEXT NOT NULL
                );
                CREATE TABLE IF NOT EXISTS leads (
                    id TEXT PRIMARY KEY,
                    created_at TEXT NOT NULL,
                    updated_at TEXT NOT NULL,
                    name TEXT NOT NULL,
                    email TEXT NOT NULL DEFAULT '',
                    phone TEXT NOT NULL DEFAULT '',
                    company TEXT NOT NULL DEFAULT '',
                    service TEXT NOT NULL,
                    message TEXT NOT NULL DEFAULT '',
                    source TEXT NOT NULL DEFAULT 'website',
                    status TEXT NOT NULL DEFAULT 'new',
                    priority TEXT NOT NULL DEFAULT 'normal',
                    owner TEXT NOT NULL DEFAULT '',
                    booking_status TEXT NOT NULL DEFAULT 'not_booked',
                    last_contacted_at TEXT,
                    next_follow_up_at TEXT,
                    consent INTEGER NOT NULL DEFAULT 1
                );
                CREATE TABLE IF NOT EXISTS activities (
                    id TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    kind TEXT NOT NULL,
                    body TEXT NOT NULL,
                    created_at TEXT NOT NULL,
                    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE
                );
                CREATE TABLE IF NOT EXISTS outbox (
                    id TEXT PRIMARY KEY,
                    lead_id TEXT NOT NULL,
                    step INTEGER NOT NULL,
                    recipient TEXT NOT NULL,
                    subject TEXT NOT NULL,
                    body TEXT NOT NULL,
                    status TEXT NOT NULL DEFAULT 'pending',
                    scheduled_for TEXT NOT NULL,
                    sent_at TEXT,
                    provider TEXT,
                    error TEXT,
                    FOREIGN KEY (lead_id) REFERENCES leads(id) ON DELETE CASCADE,
                    UNIQUE (lead_id, step)
                );
                CREATE INDEX IF NOT EXISTS idx_leads_status ON leads(status);
                CREATE INDEX IF NOT EXISTS idx_leads_created ON leads(created_at DESC);
                CREATE INDEX IF NOT EXISTS idx_outbox_due ON outbox(status, scheduled_for);
                CREATE INDEX IF NOT EXISTS idx_activities_lead
                    ON activities(lead_id, created_at DESC);
                """
            )
            if connection.execute("SELECT COUNT(*) FROM settings").fetchone()[0] == 0:
                for key, value in business.items():
                    connection.execute(
                        "INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)",
                        (key, json.dumps(value), iso()),
                    )
            if connection.execute("SELECT COUNT(*) FROM sequence_steps").fetchone()[0] == 0:
                for item in sequence:
                    connection.execute(
                        """
                        INSERT INTO sequence_steps
                            (step, delay_hours, name, subject, body, enabled, updated_at)
                        VALUES (?, ?, ?, ?, ?, 1, ?)
                        """,
                        (
                            item["step"], item["delay_hours"], item["name"],
                            item["subject"], item["body"], iso(),
                        ),
                    )

    def ping(self) -> bool:
        try:
            with self.connect() as connection:
                return connection.execute("SELECT 1").fetchone()[0] == 1
        except sqlite3.Error:
            return False

    def get_settings(self) -> dict[str, Any]:
        with self.connect() as connection:
            rows = connection.execute("SELECT key, value FROM settings").fetchall()
        return {row["key"]: json.loads(row["value"]) for row in rows}

    def update_settings(self, values: dict[str, Any]) -> dict[str, Any]:
        allowed = {
            "name", "short_name", "tagline", "logo_text", "primary_color",
            "accent_color", "contact_email", "sender_name", "reply_to",
            "booking_url", "service_options", "privacy_url", "response_promise",
        }
        with self.connect() as connection:
            for key, value in values.items():
                if key not in allowed:
                    continue
                connection.execute(
                    """
                    INSERT INTO settings (key, value, updated_at) VALUES (?, ?, ?)
                    ON CONFLICT(key) DO UPDATE SET
                        value=excluded.value, updated_at=excluded.updated_at
                    """,
                    (key, json.dumps(value), iso()),
                )
        return self.get_settings()

    def list_sequence(self) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute("SELECT * FROM sequence_steps ORDER BY step").fetchall()
        return [{**dict(row), "enabled": bool(row["enabled"])} for row in rows]

    def update_sequence_step(self, step: int, values: dict[str, Any]) -> dict[str, Any] | None:
        with self.connect() as connection:
            exists = connection.execute(
                "SELECT 1 FROM sequence_steps WHERE step = ?", (step,)
            ).fetchone()
            if not exists:
                return None
            connection.execute(
                """
                UPDATE sequence_steps
                SET delay_hours=?, name=?, subject=?, body=?, enabled=?, updated_at=?
                WHERE step=?
                """,
                (
                    values["delay_hours"], values["name"], values["subject"],
                    values["body"], int(values["enabled"]), iso(), step,
                ),
            )
            row = connection.execute(
                "SELECT * FROM sequence_steps WHERE step = ?", (step,)
            ).fetchone()
        return {**dict(row), "enabled": bool(row["enabled"])} if row else None

    def create_lead(self, values: dict[str, Any]) -> dict[str, Any]:
        lead_id = uuid.uuid4().hex[:12]
        created_at = iso()
        with self.connect() as connection:
            connection.execute(
                """
                INSERT INTO leads
                    (id, created_at, updated_at, name, email, phone, company, service,
                     message, source, status, priority, owner, booking_status, consent)
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, 'new', 'normal', '', 'not_booked', ?)
                """,
                (
                    lead_id, created_at, created_at, values["name"], values.get("email", ""),
                    values.get("phone", ""), values.get("company", ""), values["service"],
                    values.get("message", ""), values.get("source", "website"),
                    int(values.get("consent", True)),
                ),
            )
            connection.execute(
                """
                INSERT INTO activities (id, lead_id, kind, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uuid.uuid4().hex[:12], lead_id, "created", "Lead captured", created_at),
            )
        self.schedule_sequence(lead_id)
        lead = self.get_lead(lead_id)
        if not lead:
            raise RuntimeError("Lead could not be created")
        return lead

    def _merge_lead(self, connection: sqlite3.Connection, row: sqlite3.Row) -> dict[str, Any]:
        lead = dict(row)
        lead["consent"] = bool(lead["consent"])
        lead["activities"] = [
            dict(item)
            for item in connection.execute(
                "SELECT * FROM activities WHERE lead_id=? ORDER BY created_at DESC", (lead["id"],)
            ).fetchall()
        ]
        lead["followups"] = [
            dict(item)
            for item in connection.execute(
                "SELECT * FROM outbox WHERE lead_id=? ORDER BY step", (lead["id"],)
            ).fetchall()
        ]
        return lead

    def get_lead(self, lead_id: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM leads WHERE id=?", (lead_id,)).fetchone()
            return self._merge_lead(connection, row) if row else None

    def list_leads(
        self, status: str = "", search: str = "", limit: int = 250
    ) -> list[dict[str, Any]]:
        where: list[str] = []
        params: list[Any] = []
        if status:
            where.append("status = ?")
            params.append(status)
        if search:
            where.append("(name LIKE ? OR email LIKE ? OR phone LIKE ? OR service LIKE ?)")
            query = f"%{search}%"
            params.extend([query, query, query, query])
        clause = " WHERE " + " AND ".join(where) if where else ""
        params.append(limit)
        with self.connect() as connection:
            rows = connection.execute(
                f"SELECT * FROM leads{clause} ORDER BY created_at DESC LIMIT ?", params
            ).fetchall()
        return [{**dict(row), "consent": bool(row["consent"])} for row in rows]

    def update_lead(self, lead_id: str, values: dict[str, Any]) -> dict[str, Any] | None:
        allowed = {"status", "priority", "owner", "booking_status", "next_follow_up_at"}
        changes = {key: value for key, value in values.items() if key in allowed}
        if not changes:
            return self.get_lead(lead_id)
        assignments = ", ".join(f"{key}=?" for key in changes)
        params = [*changes.values(), iso(), lead_id]
        with self.connect() as connection:
            cursor = connection.execute(
                f"UPDATE leads SET {assignments}, updated_at=? WHERE id=?", params
            )
            if cursor.rowcount == 0:
                return None
            summary = ", ".join(f"{key}: {value}" for key, value in changes.items())
            connection.execute(
                """
                INSERT INTO activities (id, lead_id, kind, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uuid.uuid4().hex[:12], lead_id, "updated", summary, iso()),
            )
        return self.get_lead(lead_id)

    def add_note(self, lead_id: str, body: str) -> dict[str, Any] | None:
        with self.connect() as connection:
            if not connection.execute("SELECT 1 FROM leads WHERE id=?", (lead_id,)).fetchone():
                return None
            note_id = uuid.uuid4().hex[:12]
            created_at = iso()
            connection.execute(
                """
                INSERT INTO activities (id, lead_id, kind, body, created_at)
                VALUES (?, ?, 'note', ?, ?)
                """,
                (note_id, lead_id, body, created_at),
            )
        return {"id": note_id, "lead_id": lead_id, "kind": "note", "body": body,
                "created_at": created_at}

    def schedule_sequence(self, lead_id: str) -> None:
        lead = self.get_lead(lead_id)
        if not lead or not lead["email"]:
            return
        business = self.get_settings()
        created_at = datetime.fromisoformat(lead["created_at"])
        first_name = lead["name"].split()[0]
        variables = {
            "first_name": first_name,
            "business_name": business["name"],
            "service": lead["service"],
            "booking_url": business.get("booking_url", ""),
            "response_promise": business.get("response_promise", ""),
            "sender_name": business.get("sender_name", business["name"]),
        }

        def render(template: str) -> str:
            for key, value in variables.items():
                template = template.replace("{{" + key + "}}", str(value))
            return template

        with self.connect() as connection:
            steps = connection.execute(
                "SELECT * FROM sequence_steps WHERE enabled=1 ORDER BY step"
            ).fetchall()
            for step in steps:
                scheduled_for = iso(created_at + timedelta(hours=step["delay_hours"]))
                connection.execute(
                    """
                    INSERT OR IGNORE INTO outbox
                        (id, lead_id, step, recipient, subject, body, scheduled_for)
                    VALUES (?, ?, ?, ?, ?, ?, ?)
                    """,
                    (
                        uuid.uuid4().hex[:12], lead_id, step["step"], lead["email"],
                        render(step["subject"]), render(step["body"]), scheduled_for,
                    ),
                )
            next_row = connection.execute(
                """
                SELECT scheduled_for FROM outbox
                WHERE lead_id=? AND status='pending' ORDER BY scheduled_for LIMIT 1
                """,
                (lead_id,),
            ).fetchone()
            connection.execute(
                "UPDATE leads SET next_follow_up_at=? WHERE id=?",
                (next_row["scheduled_for"] if next_row else None, lead_id),
            )

    def due_messages(self, limit: int = 50) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT outbox.*, leads.status AS lead_status
                FROM outbox JOIN leads ON leads.id=outbox.lead_id
                WHERE outbox.status='pending' AND outbox.scheduled_for<=?
                  AND leads.status NOT IN ('won', 'lost')
                  AND leads.booking_status!='booked'
                ORDER BY outbox.scheduled_for LIMIT ?
                """,
                (iso(), limit),
            ).fetchall()
        return [dict(row) for row in rows]

    def mark_message_sent(self, message_id: str, provider: str) -> None:
        sent_at = iso()
        with self.connect() as connection:
            row = connection.execute("SELECT * FROM outbox WHERE id=?", (message_id,)).fetchone()
            if not row:
                return
            connection.execute(
                "UPDATE outbox SET status='sent', sent_at=?, provider=?, error=NULL WHERE id=?",
                (sent_at, provider, message_id),
            )
            connection.execute(
                "UPDATE leads SET last_contacted_at=?, updated_at=? WHERE id=?",
                (sent_at, sent_at, row["lead_id"]),
            )
            connection.execute(
                """
                INSERT INTO activities (id, lead_id, kind, body, created_at)
                VALUES (?, ?, ?, ?, ?)
                """,
                (uuid.uuid4().hex[:12], row["lead_id"], "email_sent",
                 f"Follow-up {row['step']} sent: {row['subject']}", sent_at),
            )
            self._refresh_next_followup(connection, row["lead_id"])

    def mark_message_failed(self, message_id: str, error: str) -> None:
        with self.connect() as connection:
            connection.execute(
                "UPDATE outbox SET status='failed', error=? WHERE id=?", (error[:500], message_id)
            )

    def _refresh_next_followup(self, connection: sqlite3.Connection, lead_id: str) -> None:
        next_row = connection.execute(
            """
            SELECT scheduled_for FROM outbox
            WHERE lead_id=? AND status='pending'
            ORDER BY scheduled_for LIMIT 1
            """,
            (lead_id,),
        ).fetchone()
        connection.execute(
            "UPDATE leads SET next_follow_up_at=? WHERE id=?",
            (next_row["scheduled_for"] if next_row else None, lead_id),
        )

    def list_outbox(self, limit: int = 250) -> list[dict[str, Any]]:
        with self.connect() as connection:
            rows = connection.execute(
                """
                SELECT outbox.*, leads.name AS lead_name
                FROM outbox JOIN leads ON leads.id=outbox.lead_id
                ORDER BY outbox.scheduled_for DESC LIMIT ?
                """,
                (limit,),
            ).fetchall()
        return [dict(row) for row in rows]

    def stats(self) -> dict[str, Any]:
        with self.connect() as connection:
            total = connection.execute("SELECT COUNT(*) FROM leads").fetchone()[0]
            counts = {
                row["status"]: row["count"]
                for row in connection.execute(
                    "SELECT status, COUNT(*) AS count FROM leads GROUP BY status"
                ).fetchall()
            }
            booked = connection.execute(
                "SELECT COUNT(*) FROM leads WHERE booking_status='booked'"
            ).fetchone()[0]
            sent = connection.execute(
                "SELECT COUNT(*) FROM outbox WHERE status='sent'"
            ).fetchone()[0]
            due = connection.execute(
                "SELECT COUNT(*) FROM outbox WHERE status='pending' AND scheduled_for<=?", (iso(),)
            ).fetchone()[0]
        return {
            "total_leads": total,
            "new_leads": counts.get("new", 0),
            "qualified_leads": counts.get("qualified", 0),
            "booked_leads": booked,
            "won_leads": counts.get("won", 0),
            "emails_sent": sent,
            "followups_due": due,
            "booking_rate": round((booked / total * 100) if total else 0, 1),
        }
