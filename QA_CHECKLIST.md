# FollowDesk release checklist

## Brand and copy

- [ ] No Northstar sample text remains in the buyer deployment.
- [ ] Business name, logo, colors, services, and sender are approved.
- [ ] Booking and privacy links open correctly.
- [ ] Response-time promise is accurate.
- [ ] Every email template has buyer approval.

## Customer experience

- [ ] Form works on desktop and mobile.
- [ ] Invalid email and missing consent are rejected clearly.
- [ ] Success state shows the correct business and booking link.
- [ ] No sensitive information is requested.
- [ ] Form keyboard navigation and labels work.

## Pipeline

- [ ] New lead appears immediately.
- [ ] Search and stage filters work.
- [ ] Stage, priority, owner, and booking status save correctly.
- [ ] Internal notes appear in activity history.
- [ ] CSV export opens safely and contains expected fields.

## Follow-up

- [ ] Four messages are scheduled for an email lead.
- [ ] Phone-only leads do not schedule email.
- [ ] Tokens render with the correct lead and brand data.
- [ ] Booked, won, and lost leads are excluded from processing.
- [ ] Delivery log shows provider and errors.
- [ ] A controlled SMTP test reaches the buyer and replies to the correct address.

## Security and deployment

- [ ] `APP_ENV=production` is enabled.
- [ ] Strong separate admin and webhook tokens are configured.
- [ ] HTTPS is active.
- [ ] SQLite directory is mounted to persistent storage.
- [ ] Secrets do not appear in Git, HTML, URLs, screenshots, or documents.
- [ ] `/health` returns `ok`.
- [ ] Data remains after a service restart.
- [ ] Tests and lint checks pass.
