from __future__ import annotations

import smtplib
from email.message import EmailMessage
from typing import Any

from .config import Settings


class Mailer:
    def __init__(self, settings: Settings) -> None:
        self.settings = settings

    def send(self, message: dict[str, Any], business: dict[str, Any]) -> str:
        if self.settings.email_provider == "demo":
            return "demo"

        email = EmailMessage()
        email["Subject"] = message["subject"]
        email["From"] = f"{business['sender_name']} <{business['reply_to']}>"
        email["To"] = message["recipient"]
        email["Reply-To"] = business["reply_to"]
        email.set_content(message["body"])

        with smtplib.SMTP(self.settings.smtp_host, self.settings.smtp_port, timeout=15) as smtp:
            if self.settings.smtp_use_tls:
                smtp.starttls()
            if self.settings.smtp_username:
                smtp.login(self.settings.smtp_username, self.settings.smtp_password)
            smtp.send_message(email)
        return "smtp"
