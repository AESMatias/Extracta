import logging
import threading
from email.message import EmailMessage
from typing import Any

import pytest
from pydantic import SecretStr

from app import emails, mail
from app.config import Settings

SENDER = "Extracta <no-reply@extracta.example.com>"


def settings(**values: Any) -> Settings:
    return Settings(  # type: ignore[call-arg]
        _env_file=None,
        gemini_api_key=SecretStr("k"),
        database_url=SecretStr("postgresql://u:p@h/d"),
        secret_key=SecretStr("k" * 32),
        **values,
    )


def text_of(message: EmailMessage) -> str:
    body = message.get_body(("plain",))
    assert body is not None
    return str(body.get_content())


def html_of(message: EmailMessage) -> str:
    body = message.get_body(("html",))
    assert body is not None
    return str(body.get_content())


# --------------------------------------------------------------------------- templates


def test_verification_email() -> None:
    link = "https://extracta.example.com/verify-email#token=abc"
    message = emails.verify_email(sender=SENDER, to="ana@example.com", name="Ana", link=link)

    assert message["To"] == "ana@example.com"
    assert message["From"] == SENDER
    assert "Confirm your email" in message["Subject"]
    assert message["Message-ID"].endswith("@extracta.example.com>")
    assert link in text_of(message) and "Hi Ana," in text_of(message)
    assert f'href="{link}"' in html_of(message)


def test_user_text_is_escaped_in_html() -> None:
    message = emails.reset_password(sender=SENDER, to="a@b.co", name="<script>x</script>", link="https://e/x#token=1")

    assert "<script>" not in html_of(message)
    assert "&lt;script&gt;" in html_of(message)


def test_reset_and_password_changed_emails() -> None:
    reset = emails.reset_password(sender=SENDER, to="a@b.co", name=None, link="https://e/reset-password#token=t")
    changed = emails.password_changed(sender=SENDER, to="a@b.co", name=None, reset_link="https://e/forgot-password")

    assert "1 hour" in text_of(reset) and text_of(reset).startswith("Hi,")
    assert "was changed" in changed["Subject"]
    assert "https://e/forgot-password" in text_of(changed)


# --------------------------------------------------------------------------- mailers


def message() -> EmailMessage:
    return emails.verify_email(sender=SENDER, to="ana@example.com", name=None, link="https://e/v#token=secret-link")


def test_log_mailer_writes_the_email_to_the_logs(caplog: pytest.LogCaptureFixture) -> None:
    with caplog.at_level(logging.WARNING, logger="app.mail"):
        mail.LogMailer().send(message())

    assert "NOT sent" in caplog.text
    assert "ana@example.com" in caplog.text and "https://e/v#token=secret-link" in caplog.text


class RecordingSMTP:
    instances: list["RecordingSMTP"] = []

    def __init__(self, host: str, port: int, timeout: int, context: object = None) -> None:
        self.host, self.port, self.context = host, port, context
        self.calls: list[str] = []
        RecordingSMTP.instances.append(self)

    def __enter__(self) -> "RecordingSMTP":
        return self

    def __exit__(self, *_: object) -> None:
        self.calls.append("quit")

    def starttls(self, context: object) -> None:
        self.calls.append("starttls")

    def login(self, username: str, password: str) -> None:
        self.calls.append(f"login:{username}")

    def send_message(self, msg: EmailMessage) -> None:
        self.calls.append(f"send:{msg['To']}")


@pytest.fixture
def smtp(monkeypatch: pytest.MonkeyPatch) -> type[RecordingSMTP]:
    RecordingSMTP.instances = []
    monkeypatch.setattr(mail.smtplib, "SMTP", RecordingSMTP)
    monkeypatch.setattr(mail.smtplib, "SMTP_SSL", RecordingSMTP)
    return RecordingSMTP


@pytest.mark.parametrize(
    ("security", "expected"),
    [
        ("starttls", ["starttls", "login:user", "send:ana@example.com", "quit"]),
        ("ssl", ["login:user", "send:ana@example.com", "quit"]),
        ("none", ["login:user", "send:ana@example.com", "quit"]),
    ],
)
def test_smtp_mailer(smtp: type[RecordingSMTP], security: Any, expected: list[str]) -> None:
    mailer = mail.SmtpMailer(host="smtp.example.com", port=587, username="user", password="pw", security=security)

    mailer.send(message())

    [connection] = smtp.instances
    assert (connection.host, connection.port) == ("smtp.example.com", 587)
    assert connection.calls == expected
    assert (connection.context is not None) == (security == "ssl")  # SMTP_SSL verifies the certificate


def test_smtp_without_credentials_skips_login(smtp: type[RecordingSMTP]) -> None:
    mail.SmtpMailer(host="relay", port=25, username=None, password=None, security="none").send(message())

    assert smtp.instances[0].calls == ["send:ana@example.com", "quit"]


def test_background_mailer_sends_on_another_thread() -> None:
    sent: list[str] = []
    done = threading.Event()

    class Inner:
        def send(self, msg: EmailMessage) -> None:
            sent.append(threading.current_thread().name)
            done.set()

    mail.BackgroundMailer(Inner()).send(message())

    assert done.wait(5)
    assert sent == ["mailer"]


def test_background_mailer_survives_smtp_failures(caplog: pytest.LogCaptureFixture) -> None:
    class Broken:
        def send(self, msg: EmailMessage) -> None:
            raise OSError("connection refused")

    with caplog.at_level(logging.ERROR, logger="app.mail"):
        mail.BackgroundMailer(Broken())._deliver(message())  # runs inline: same code as the thread

    assert "Could not send the email" in caplog.text


def test_build_mailer() -> None:
    assert isinstance(mail.build_mailer(settings()), mail.LogMailer)
    assert isinstance(mail.build_mailer(settings(smtp_host="smtp.example.com")), mail.BackgroundMailer)
    assert settings(smtp_host="smtp.example.com").mail_enabled is True
