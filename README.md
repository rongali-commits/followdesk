# FollowDesk

FollowDesk is a white-label lead follow-up and booking system for local service businesses. It captures enquiries, places them in a focused sales pipeline, sends a configurable four-step email sequence, offers a direct booking link, and records the full activity history.

The included fictional **Northstar Home Services** experience is a ready-to-use sales demo. Replace every sample name, email, link, service, and claim with buyer-approved information before a client launch.

## Why this product is sellable

- It solves a visible revenue problem: leads going cold after an enquiry.
- It is easier to understand than a broad CRM and cheaper to operate.
- The working demo needs no paid email or AI service.
- Each client receives their own branding, data, templates, and deployment.
- It can be sold alone or connected directly to LeadDesk AI.
- Agencies can reuse the same fulfilment process for different niches.

## Included features

- Branded public enquiry experience
- Six-stage lead pipeline: new, contacted, qualified, booked, won, lost
- Automatic email sequence at 0, 24, 72, and 168 hours by default
- Demo email provider for safe sales demonstrations
- Production SMTP support, including SMTP services offered by email providers
- Booking status and Calendly, Cal.com, or custom booking links
- Automatic sequence suppression for booked, won, and lost leads
- Search, filters, priorities, owner assignment, and internal notes
- Activity history and follow-up delivery log
- Editable brand settings and email templates
- Secure generic webhook and LeadDesk AI webhook support
- Formula-safe CSV export
- Private token-protected admin dashboard
- Docker, Railway, and standard Python deployment options
- Tests, buyer intake, fulfilment, QA, and handoff documentation

## Quick start

Python 3.11 or newer is required.

```powershell
py -m venv .venv
.venv\Scripts\Activate.ps1
pip install -e ".[dev]"
Copy-Item .env.example .env
$env:ADMIN_TOKEN="choose-a-private-admin-token"
$env:WEBHOOK_TOKEN="choose-a-separate-webhook-token"
uvicorn followdesk.app:app --reload
```

Open:

- Customer demo: `http://127.0.0.1:8000/`
- Admin dashboard: `http://127.0.0.1:8000/admin`
- Health check: `http://127.0.0.1:8000/health`

The default admin token in development is `development-admin-token`. Never use that value on a public deployment.

## Safe demonstration mode

`EMAIL_PROVIDER=demo` records due messages as sent but does not transmit email. This keeps the public demo free and prevents visitors from triggering real messages. The dashboard clearly labels this behavior.

To create a realistic local demo pipeline:

```powershell
$env:PYTHONPATH="src"
python scripts/seed_demo.py
```

The seed script refuses to add sample records when the database already contains leads.

## Production email

Set `EMAIL_PROVIDER=smtp` and configure the SMTP variables in `.env`. The sender uses the brand settings saved in the dashboard. Use a verified sending domain, configure SPF and DKIM with the provider, and test replies before launch.

The built-in worker checks for due messages every 60 seconds. On a platform where a persistent worker is unsuitable, set `FOLLOWUP_WORKER_ENABLED=false` and run this command from a trusted scheduled job:

```powershell
$env:PYTHONPATH="src"
python scripts/process_followups.py
```

## LeadDesk AI integration

FollowDesk accepts both a plain lead object and LeadDesk AI's `lead.created` envelope at:

```text
POST /api/webhooks/leads
X-Webhook-Token: your-private-webhook-token
```

See [INTEGRATIONS.md](INTEGRATIONS.md) for exact payloads and setup.

## Environment variables

| Variable | Required | Purpose |
|---|---:|---|
| `APP_ENV` | Yes in production | Enables strict secret validation when set to `production` |
| `ADMIN_TOKEN` | Production | Protects every admin API request |
| `WEBHOOK_TOKEN` | Production | Separately protects lead ingestion |
| `DATABASE_PATH` | No | SQLite path, defaults to `runtime/followdesk.db` |
| `BUSINESS_FILE` | No | First-run white-label brand seed |
| `SEQUENCE_FILE` | No | First-run email sequence seed |
| `EMAIL_PROVIDER` | No | `demo` or `smtp` |
| `SMTP_HOST` | SMTP | Mail server hostname |
| `SMTP_PORT` | SMTP | Defaults to `587` |
| `SMTP_USERNAME` | SMTP | Provider username |
| `SMTP_PASSWORD` | SMTP | Provider password or SMTP key |
| `SMTP_USE_TLS` | No | Defaults to `true` |
| `FOLLOWUP_WORKER_ENABLED` | No | Runs the internal due-message worker |
| `FOLLOWUP_POLL_SECONDS` | No | Worker interval, minimum 15 seconds |
| `LEAD_RATE_LIMIT_PER_MINUTE` | No | Per-address public form limit, defaults to 8 |
| `CORS_ORIGINS` | No | Exact comma-separated external form origins |
| `PORT` | Hosting | Injected automatically by Railway and similar hosts |

## Data and security boundaries

- Secrets belong only in server environment variables.
- The admin and webhook tokens must be different strong random values.
- Use HTTPS on every public deployment.
- Persist `/app/runtime` or the configured database directory.
- Use a client-approved privacy policy and consent statement.
- Do not collect payment-card, government ID, medical, or financial data.
- Keep demo mode enabled until the buyer approves the sender domain and templates.
- SQLite is suitable for a small single-business deployment. Move to PostgreSQL before building a high-write multi-tenant service.
- The token dashboard is designed for a small owner-managed system, not a large multi-user enterprise.

## Test and quality commands

```powershell
pytest -q
ruff check .
node --check src/followdesk/static/public.js
node --check src/followdesk/static/admin.js
```

## Delivery documents

- [CLIENT_QUESTIONNAIRE.md](CLIENT_QUESTIONNAIRE.md)
- [FULFILLMENT_PLAYBOOK.md](FULFILLMENT_PLAYBOOK.md)
- [QA_CHECKLIST.md](QA_CHECKLIST.md)
- [DELIVERY_GUIDE.md](DELIVERY_GUIDE.md)
- [DEPLOYMENT_RAILWAY.md](DEPLOYMENT_RAILWAY.md)
- [COMMERCIAL_LICENSE_TEMPLATE.md](COMMERCIAL_LICENSE_TEMPLATE.md)
- [Upwork Project Catalog copy](sales-assets/UPWORK_PROJECT_CATALOG.md)

## Commercial use

This repository is prepared as a productized-service base, not a public open-source template. Customize the included license template for each buyer. The template is not legal advice.


## Version 1.0.1: stop remaining follow-ups

The lead drawer includes a private admin action to cancel pending messages after a reply or opt-out, without closing the opportunity. Cancellation is recorded in the activity history. A message already in delivery may finish. Replies go to the configured reply-to mailbox; automatic inbox sync and reply detection are not included.
