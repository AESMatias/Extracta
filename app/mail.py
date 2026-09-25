"""Outgoing email.

- SmtpMailer: any SMTP provider (Brevo, Resend, Mailgun, Amazon SES, Gmail with an app password).
- LogMailer: no SMTP configured; writes each email, links included, to the logs. Local testing
  only: in production anyone who can read the logs could use those links.
- BackgroundMailer: sends on a separate thread, so a slow SMTP server never delays a response
  and the response time does not reveal whether an email was sent (account enumeration).
"""

import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from typing import Literal, Protocol

from app.config import Settings

log = logging.getLogger(__name__)
SMTP_TIMEOUT_SECONDS = 15


class Mailer(Protocol):
    def send(self, message: EmailMessage) -> None: ...


class SmtpMailer:
    def __init__(
        self,
        *,
        host: str,
        port: int,
        username: str | None,
        password: str | None,
        security: Literal["starttls", "ssl", "none"],
    ) -> None:
        self._host, self._port = host, port
        self._username, self._password = username, password
        self._security = security

    def send(self, message: EmailMessage) -> None:
        context = ssl.create_default_context()  # verifies the server's certificate
        smtp: smtplib.SMTP
        if self._security == "ssl":
            smtp = smtplib.SMTP_SSL(self._host, self._port, timeout=SMTP_TIMEOUT_SECONDS, context=context)
        else:
            smtp = smtplib.SMTP(self._host, self._port, timeout=SMTP_TIMEOUT_SECONDS)
        with smtp:
            if self._security == "starttls":
                smtp.starttls(context=context)
            if self._username and self._password:
                smtp.login(self._username, self._password)
            smtp.send_message(message)


class LogMailer:
    def send(self, message: EmailMessage) -> None:
        body = message.get_body(("plain",))
        text = body.get_content() if body is not None else ""
        log.warning(
            "SMTP is not configured; this email was NOT sent.\nTo: %s\nSubject: %s\n\n%s",
            message["To"],
            message["Subject"],
            text,
        )


class BackgroundMailer:
    def __init__(self, inner: Mailer) -> None:
        self._inner = inner

    def send(self, message: EmailMessage) -> None:
        threading.Thread(target=self._deliver, args=(message,), name="mailer", daemon=True).start()

    def _deliver(self, message: EmailMessage) -> None:
        try:
            self._inner.send(message)
        except Exception:  # never crash the thread: the user can ask for the email again
            log.exception("Could not send the email %r to %s", message["Subject"], message["To"])


def build_mailer(settings: Settings) -> Mailer:
    if not settings.smtp_host:
        return LogMailer()
    return BackgroundMailer(
        SmtpMailer(
            host=settings.smtp_host,
            port=settings.smtp_port,
            username=settings.smtp_username,
            password=settings.smtp_password.get_secret_value() if settings.smtp_password else None,
            security=settings.smtp_security,
        )
    )
