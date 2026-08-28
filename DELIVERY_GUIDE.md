# FollowDesk operating guide

## Open the system

Use the public URL for the customer enquiry form. Add `/admin` to open the private dashboard. Enter the admin token supplied through the agreed secure channel.

## Work a new lead

1. Open the lead from the overview table or pipeline.
2. Review the service, message, and source.
3. Assign a priority and owner.
4. Move the lead to contacted after a team member responds.
5. Add internal notes so the next team member has context.
6. Mark the booking status as booked when an appointment is confirmed.
7. Move the lead to won or lost when the opportunity closes.

Booked, won, and lost leads do not receive future automatic messages.

## Review email activity

Open **Follow-ups** to see scheduled, sent, and failed messages. In demo mode, sent means the product recorded the message without transmitting real email. In SMTP mode, sent means the mail server accepted the message.

## Edit the sequence

Open **Email sequence**, choose a step, edit the timing or copy, and save. Changes apply to leads captured after the edit. Existing scheduled messages retain the content created when that lead entered the system.

## Change branding

Open **Brand settings** to update the business name, colors, sender, reply-to address, services, booking link, privacy link, and response promise.

## Export data

Choose **Export CSV** from the dashboard. Store exported lead files securely and delete old exports according to the business's retention policy.

## Troubleshooting

- If a lead has no scheduled email, check whether it supplied an email address.
- If messages fail, verify the SMTP host, port, username, password, TLS choice, sender domain, and provider logs.
- If future messages still appear as pending after a booking, that is expected. They remain in the audit log but are excluded from sending.
- If data disappears after deployment, confirm the host has persistent storage mounted at the configured database path.
