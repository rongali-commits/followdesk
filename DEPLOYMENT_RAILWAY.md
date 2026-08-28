# Railway deployment

Railway is the recommended host for the first FollowDesk deployment because the product uses persistent SQLite storage and a long-running follow-up worker. Vercel is still suitable for noerong.com, but it is not the best default for this stateful service.

## 1. Create the service

1. Push this repository to a private GitHub repository.
2. In Railway, choose **New Project**, then **Deploy from GitHub repo**.
3. Select the FollowDesk repository.
4. Railway detects the included Dockerfile and health check.

## 2. Create persistent storage

1. Open the service in Railway.
2. Add a volume.
3. Mount it at `/app/runtime`.
4. Keep `DATABASE_PATH=/app/runtime/followdesk.db`.

Without the volume, redeployment can remove the buyer's leads and settings.

## 3. Add production variables

Create strong, separate random secrets. Do not use the example values.

```text
APP_ENV=production
ADMIN_TOKEN=<at least 24 random characters>
WEBHOOK_TOKEN=<a different value with at least 24 random characters>
DATABASE_PATH=/app/runtime/followdesk.db
EMAIL_PROVIDER=demo
FOLLOWUP_WORKER_ENABLED=true
FOLLOWUP_POLL_SECONDS=60
LEAD_RATE_LIMIT_PER_MINUTE=8
```

Leave email in demo mode until the buyer has approved the sender identity and every template.

## 4. Generate a domain

Use Railway's generated HTTPS domain first. Add a custom subdomain such as `followup.clientdomain.com` only after the application passes QA.

## 5. Verify the release

1. Open `/health` and confirm `status` is `ok`.
2. Open `/` and submit one non-sensitive test lead.
3. Open `/admin` and sign in with the private admin token.
4. Confirm the lead appears and step 1 shows as sent by `demo`.
5. Change the lead to booked and confirm future messages remain pending but are not processed.
6. Restart the Railway service and confirm the lead still exists.

## 6. Enable real email

After approval, add the SMTP values described in `.env.example`, set `EMAIL_PROVIDER=smtp`, and redeploy. Test with an email address controlled by the buyer before sending to real leads.

## 7. Handoff

Provide the buyer with:

- Public product URL
- Admin URL
- Admin token through a secure channel
- Booking-link and reply-to confirmation
- A test delivery record
- [DELIVERY_GUIDE.md](DELIVERY_GUIDE.md)

Never place the admin or webhook token in a public chat, screenshot, repository, or delivery document.
