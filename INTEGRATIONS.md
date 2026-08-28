# Integrations

## Generic website or automation tool

Send an HTTPS POST request to `/api/webhooks/leads` with the private `X-Webhook-Token` header.

```json
{
  "name": "Alex Morgan",
  "email": "alex@example.com",
  "phone": "",
  "company": "Morgan House",
  "service": "Deep cleaning",
  "message": "Please contact me about availability.",
  "source": "website-contact-form",
  "consent": true
}
```

Either email or phone is required. Email is required for the automated email sequence.

## LeadDesk AI

FollowDesk also accepts LeadDesk AI's native envelope:

```json
{
  "event": "lead.created",
  "lead": {
    "name": "Alex Morgan",
    "email": "alex@example.com",
    "phone": "",
    "company": "",
    "service": "Deep cleaning",
    "message": "Please contact me about availability.",
    "source": "website-widget",
    "consent": true
  }
}
```

For a direct connection, configure LeadDesk AI's lead webhook to call the FollowDesk endpoint and include the FollowDesk webhook token. If the sending system cannot add a custom header, route the event through Make, Zapier, or n8n and add the header there.

## Booking providers

FollowDesk does not copy calendar data. It sends the buyer's approved booking URL in each message and displays the same link after form submission. Supported options include:

- Calendly
- Cal.com
- TidyCal
- Google Calendar appointment schedules
- A custom booking page

When a booking is confirmed, set the lead's booking status to `booked`. FollowDesk immediately excludes that lead from future follow-up processing.

## SMTP providers

Any standard STARTTLS SMTP service can be used. Common transactional email services expose SMTP credentials, but the provider account, sender domain, SPF, DKIM, and applicable messaging rules remain the buyer's responsibility.
