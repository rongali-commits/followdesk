# FollowDesk Source Kit Guide

FollowDesk is a white-label lead follow-up and booking CRM for service businesses. This package includes the application source, tests, sample configuration, deployment files, and buyer documentation needed to launch a branded installation.

## Included

- FastAPI application and responsive lead form
- Protected lead dashboard and pipeline
- Follow-up sequence configuration
- Lead notes, activity history, ownership, and next actions
- Demo email provider plus SMTP configuration
- Booking workflow and secure webhook endpoint
- Docker and Railway deployment configuration
- Automated tests
- Single-business commercial licence

## Requirements

- Python 3.11 or newer
- Separate long secrets for administration and webhooks
- Optional SMTP credentials for real email delivery
- Optional external form or automation client

## Quick start

1. Extract the package and open a terminal in the project folder.
2. Create and activate a virtual environment.
3. Install the project with `pip install -e .`.
4. Copy `.env.example` to `.env`.
5. Replace both secret placeholders with different random values of at least 24 characters.
6. Update `data/business.json` and `data/sequence.json` with the buyer's brand and follow-up workflow.
7. Start the application with `uvicorn followdesk.main:app --host 0.0.0.0 --port 8000`.
8. Test the lead form, protected dashboard, pipeline, sequence, and booking actions.

The demo email provider records messages without sending them. Configure SMTP only when the buyer is ready to send real email.

## Production checklist

- Set `APP_ENV=production`.
- Generate unique `ADMIN_TOKEN` and `WEBHOOK_TOKEN` values.
- Keep secrets and SMTP credentials in the hosting provider's secret manager.
- Replace all sample brand, booking, and sequence content.
- Decide whether the built-in worker or an external scheduled call will process follow-ups.
- Set exact allowed origins for external forms.
- Run `pytest` before deployment.
- Test lead creation, duplicate handling, stage changes, follow-up processing, booking, and dashboard protection.

## Deployment

Use `DEPLOYMENT_RAILWAY.md` for the complete Railway procedure. See `INTEGRATIONS.md` for SMTP, external forms, and automation connections.

## Licence and support

The purchase includes the licence in `BUYER_LICENSE.md`. Hosting, domains, email providers, integrations, data migration, major feature work, and ongoing maintenance are not included in the source-kit price.

For a setup question, contact hello@noerong.com.


## Version 1.0.1: stop remaining follow-ups

The lead drawer includes a private admin action to cancel pending messages after a reply or opt-out, without closing the opportunity. Cancellation is recorded in the activity history. A message already in delivery may finish. Replies go to the configured reply-to mailbox; automatic inbox sync and reply detection are not included.
