"""
Minimal transactional email sender for Jet Finder (password resets, notifications).

Provider resolution order:
  1. Resend (https://resend.com) if RESEND_API_KEY is set — simplest setup.
  2. SMTP if SMTP_HOST is set (works with Gmail app passwords, SendGrid SMTP, etc.).
  3. Dev fallback: logs the email body to the console so the flow is testable
     without any provider. In production this returns False so callers can
     surface "email not configured" instead of silently dropping mail.

Env vars:
  RESEND_API_KEY      — Resend API key (easiest option)
  MAIL_FROM           — From address, e.g. "JetSchool <noreply@jetschoolusa.com>"
  SMTP_HOST / SMTP_PORT / SMTP_USER / SMTP_PASS — classic SMTP alternative
"""
from __future__ import annotations

import logging
import os
import smtplib
from email.mime.multipart import MIMEMultipart
from email.mime.text import MIMEText

_log = logging.getLogger(__name__)


def _mail_from() -> str:
    return os.environ.get('MAIL_FROM', 'JetSchool <noreply@jetschoolusa.com>')


def is_configured() -> bool:
    return bool(os.environ.get('RESEND_API_KEY') or os.environ.get('SMTP_HOST'))


def send_email(to: str, subject: str, html: str, text: str | None = None) -> bool:
    """Send an email. Returns True if handed off to a provider successfully."""
    if os.environ.get('RESEND_API_KEY'):
        return _send_resend(to, subject, html)
    if os.environ.get('SMTP_HOST'):
        return _send_smtp(to, subject, html, text)
    # Dev fallback: print to logs so local testing works without a provider.
    _log.warning(
        "email_service: no provider configured. Would send to=%s subject=%r\n----\n%s\n----",
        to, subject, text or html,
    )
    return False


def _send_resend(to: str, subject: str, html: str) -> bool:
    import requests
    try:
        resp = requests.post(
            'https://api.resend.com/emails',
            headers={'Authorization': f"Bearer {os.environ['RESEND_API_KEY']}"},
            json={'from': _mail_from(), 'to': [to], 'subject': subject, 'html': html},
            timeout=15,
        )
        if resp.status_code in (200, 201):
            return True
        _log.error('email_service: Resend error %s: %s', resp.status_code, resp.text[:300])
        return False
    except Exception:
        _log.exception('email_service: Resend request failed')
        return False


def _send_smtp(to: str, subject: str, html: str, text: str | None) -> bool:
    host = os.environ['SMTP_HOST']
    port = int(os.environ.get('SMTP_PORT', '587'))
    user = os.environ.get('SMTP_USER')
    password = os.environ.get('SMTP_PASS')
    msg = MIMEMultipart('alternative')
    msg['Subject'] = subject
    msg['From'] = _mail_from()
    msg['To'] = to
    if text:
        msg.attach(MIMEText(text, 'plain'))
    msg.attach(MIMEText(html, 'html'))
    try:
        with smtplib.SMTP(host, port, timeout=20) as server:
            server.starttls()
            if user and password:
                server.login(user, password)
            server.sendmail(_mail_from(), [to], msg.as_string())
        return True
    except Exception:
        _log.exception('email_service: SMTP send failed')
        return False
