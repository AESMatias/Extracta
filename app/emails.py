"""The emails Extracta sends: verify your address, reset your password, your password changed.

Every email has a plain-text part and a simple HTML part; the HTML only uses inline styles,
which is what email clients support. User-provided text (the name) is HTML-escaped.
"""

from email.message import EmailMessage
from email.utils import formatdate, make_msgid
from html import escape

BRAND = "Extracta"
_COLOR = "#4f46e5"


def _message(*, sender: str, to: str, subject: str, text: str, html: str) -> EmailMessage:
    message = EmailMessage()
    message["From"] = sender
    message["To"] = to
    message["Subject"] = subject
    message["Date"] = formatdate(localtime=False)
    message["Message-ID"] = make_msgid(domain=sender.rpartition("@")[2].strip("> ") or None)
    message.set_content(text)
    message.add_alternative(html, subtype="html")
    return message


def _layout(title: str, paragraphs: list[str], button: tuple[str, str] | None, footer: str) -> str:
    body = "".join(f'<p style="margin:0 0 16px;line-height:1.55">{p}</p>' for p in paragraphs)
    if button:
        label, url = button
        body += (
            f'<p style="margin:24px 0"><a href="{escape(url)}" style="background:{_COLOR};color:#ffffff;'
            'text-decoration:none;padding:12px 22px;border-radius:10px;font-weight:600;display:inline-block">'
            f"{escape(label)}</a></p>"
            f'<p style="margin:0 0 16px;font-size:13px;color:#6b7280;word-break:break-all">'
            f"If the button does not work, copy this link into your browser:<br>{escape(url)}</p>"
        )
    return (
        '<!doctype html><html><body style="margin:0;background:#f4f4f8;padding:24px 12px;'
        'font-family:-apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif;color:#111827">'
        '<table role="presentation" width="100%" cellpadding="0" cellspacing="0"><tr><td align="center">'
        '<table role="presentation" width="100%" style="max-width:520px;background:#ffffff;border-radius:16px;'
        'padding:32px" cellpadding="0" cellspacing="0"><tr><td>'
        f'<p style="margin:0 0 24px;font-size:20px;font-weight:700;color:{_COLOR}">{BRAND}</p>'
        f'<h1 style="margin:0 0 16px;font-size:22px">{escape(title)}</h1>{body}'
        f'<p style="margin:24px 0 0;font-size:12px;color:#9ca3af">{footer}</p>'
        "</td></tr></table></td></tr></table></body></html>"
    )


def _greeting(name: str | None) -> str:
    return f"Hi {name}," if name else "Hi,"


def verify_email(*, sender: str, to: str, name: str | None, link: str) -> EmailMessage:
    subject = f"Confirm your email for {BRAND}"
    text = (
        f"{_greeting(name)}\n\n"
        f"Confirm that this is your email address to start processing documents with {BRAND}:\n\n"
        f"{link}\n\n"
        "The link is valid for 3 days. If you did not create an account, ignore this email.\n"
    )
    html = _layout(
        "Confirm your email",
        [
            escape(_greeting(name)),
            f"Confirm that this is your email address to start processing documents with {BRAND}.",
        ],
        ("Confirm my email", link),
        "The link is valid for 3 days. If you did not create an account, ignore this email.",
    )
    return _message(sender=sender, to=to, subject=subject, text=text, html=html)


def reset_password(*, sender: str, to: str, name: str | None, link: str) -> EmailMessage:
    subject = f"Reset your {BRAND} password"
    text = (
        f"{_greeting(name)}\n\n"
        "Someone (hopefully you) asked to reset the password of this account. Choose a new one here:\n\n"
        f"{link}\n\n"
        "The link is valid for 1 hour and works once. If it was not you, ignore this email: "
        "your password stays the same.\n"
    )
    html = _layout(
        "Reset your password",
        [escape(_greeting(name)), "Someone (hopefully you) asked to reset the password of this account."],
        ("Choose a new password", link),
        "The link is valid for 1 hour and works once. If it was not you, ignore this email: "
        "your password stays the same.",
    )
    return _message(sender=sender, to=to, subject=subject, text=text, html=html)


def password_changed(*, sender: str, to: str, name: str | None, reset_link: str) -> EmailMessage:
    subject = f"Your {BRAND} password was changed"
    text = (
        f"{_greeting(name)}\n\n"
        "The password of your account was just changed, and every other session was signed out.\n\n"
        "If it was not you, reset it right away:\n\n"
        f"{reset_link}\n"
    )
    html = _layout(
        "Your password was changed",
        [
            escape(_greeting(name)),
            "The password of your account was just changed, and every other session was signed out.",
            "If it was not you, reset it right away.",
        ],
        ("Reset my password", reset_link),
        "You receive this email for your security; there is nothing to do if it was you.",
    )
    return _message(sender=sender, to=to, subject=subject, text=text, html=html)
