from __future__ import annotations

from followdesk.app import create_app

SAMPLE_LEADS = [
    {
        "name": "Olivia Bennett",
        "email": "olivia@example.com",
        "phone": "+1 555 0101",
        "company": "Bennett Residence",
        "service": "Deep cleaning",
        "message": "Looking for a deep clean before family visits next month.",
        "source": "Website enquiry",
        "consent": True,
        "status": "qualified",
        "priority": "high",
    },
    {
        "name": "Marcus Lee",
        "email": "marcus@example.com",
        "phone": "+1 555 0102",
        "company": "Lee Property Group",
        "service": "Commercial cleaning",
        "message": "We need a recurring service for a small office.",
        "source": "Referral",
        "consent": True,
        "status": "contacted",
        "priority": "normal",
    },
    {
        "name": "Sofia Ramirez",
        "email": "sofia@example.com",
        "phone": "+1 555 0103",
        "company": "",
        "service": "Move-in or move-out cleaning",
        "message": "The apartment will be empty on Friday afternoon.",
        "source": "LeadDesk AI",
        "consent": True,
        "status": "booked",
        "priority": "high",
    },
    {
        "name": "Daniel Foster",
        "email": "daniel@example.com",
        "phone": "",
        "company": "",
        "service": "Home cleaning",
        "message": "Interested in a biweekly plan.",
        "source": "Landing page",
        "consent": True,
        "status": "new",
        "priority": "normal",
    },
]


def main() -> None:
    app = create_app()
    storage = app.state.storage
    if storage.list_leads(limit=1):
        print("Demo seed skipped because the database already contains leads.")
        return
    for sample in SAMPLE_LEADS:
        values = {key: value for key, value in sample.items() if key not in {"status", "priority"}}
        lead = storage.create_lead(values)
        update = {"status": sample["status"], "priority": sample["priority"]}
        if sample["status"] == "booked":
            update["booking_status"] = "booked"
        storage.update_lead(lead["id"], update)
    result = app.state.process_followups()
    print(f"Created {len(SAMPLE_LEADS)} demo leads. Sent {result['processed']} demo messages.")


if __name__ == "__main__":
    main()
