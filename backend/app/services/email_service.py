"""
Email service — Gmail SMTP via stdlib smtplib.

Sends are dispatched on a background thread so HTTP handlers never block on SMTP,
and SMTP errors are logged (not raised) so a flaky mail server can't break a
password reset, registration, or transaction flow.
"""
from __future__ import annotations

import logging
import smtplib
import ssl
import threading
from email.message import EmailMessage
from email.utils import formataddr
from typing import Iterable, Optional

from flask import current_app, has_app_context

logger = logging.getLogger(__name__)


def _send_sync(
    app,
    to_addrs: list[str],
    subject: str,
    text_body: str,
    html_body: Optional[str],
) -> None:
    cfg = app.config
    if not cfg.get('MAIL_ENABLED'):
        logger.info('MAIL_ENABLED is false — skipping send to %s', to_addrs)
        return

    username = cfg.get('MAIL_USERNAME')
    password = cfg.get('MAIL_PASSWORD')
    if not username or not password:
        logger.warning('MAIL credentials missing — skipping send to %s', to_addrs)
        return

    sender_email = cfg.get('MAIL_DEFAULT_SENDER') or username
    sender_name = cfg.get('MAIL_DEFAULT_SENDER_NAME') or 'QR Transaction Protection'

    msg = EmailMessage()
    msg['Subject'] = subject
    msg['From'] = formataddr((sender_name, sender_email))
    msg['To'] = ', '.join(to_addrs)
    msg.set_content(text_body)
    if html_body:
        msg.add_alternative(html_body, subtype='html')

    server = cfg.get('MAIL_SERVER', 'smtp.gmail.com')
    port = int(cfg.get('MAIL_PORT', 587))
    use_ssl = bool(cfg.get('MAIL_USE_SSL'))
    use_tls = bool(cfg.get('MAIL_USE_TLS'))
    timeout = int(cfg.get('MAIL_TIMEOUT', 15))

    try:
        if use_ssl:
            ctx = ssl.create_default_context()
            with smtplib.SMTP_SSL(server, port, timeout=timeout, context=ctx) as s:
                s.login(username, password)
                s.send_message(msg)
        else:
            with smtplib.SMTP(server, port, timeout=timeout) as s:
                s.ehlo()
                if use_tls:
                    s.starttls(context=ssl.create_default_context())
                    s.ehlo()
                s.login(username, password)
                s.send_message(msg)
        logger.info('Email sent to %s — subject=%r', to_addrs, subject)
    except Exception as exc:  # noqa: BLE001 — never let mail break a request
        logger.exception('Email send failed to=%s subject=%r err=%s', to_addrs, subject, exc)


def send_email(
    to: str | Iterable[str],
    subject: str,
    text_body: str,
    html_body: Optional[str] = None,
    *,
    sync: bool = False,
) -> None:
    """Send an email. Non-blocking by default."""
    if not has_app_context():
        logger.warning('send_email called without app context — dropping')
        return
    to_addrs = [to] if isinstance(to, str) else list(to)
    to_addrs = [a for a in to_addrs if a]
    if not to_addrs:
        return

    app = current_app._get_current_object()  # capture real app for the thread

    if sync:
        _send_sync(app, to_addrs, subject, text_body, html_body)
        return

    threading.Thread(
        target=_send_sync,
        args=(app, to_addrs, subject, text_body, html_body),
        daemon=True,
    ).start()


# ---------------------------------------------------------------------------
# Templates
# ---------------------------------------------------------------------------

def _wrap_html(title: str, inner: str) -> str:
    return f"""<!doctype html>
<html><body style="font-family: -apple-system,Segoe UI,Roboto,Helvetica,Arial,sans-serif; background:#f5f7fb; padding:24px; margin:0;">
  <div style="max-width:560px; margin:0 auto; background:#fff; border-radius:12px; padding:32px; box-shadow:0 1px 3px rgba(0,0,0,.06);">
    <h1 style="margin:0 0 16px; font-size:20px; color:#0f172a;">{title}</h1>
    {inner}
    <hr style="border:none; border-top:1px solid #e5e7eb; margin:24px 0;">
    <p style="font-size:12px; color:#6b7280; margin:0;">QR Transaction Protection — automated message, please do not reply.</p>
  </div>
</body></html>"""


def send_password_reset_email(to_email: str, full_name: str, token: str) -> None:
    frontend = current_app.config.get('APP_FRONTEND_URL', 'http://localhost:3000')
    reset_link = f"{frontend.rstrip('/')}/login?reset_token={token}"
    subject = 'Reset your QR Transaction password'
    text = (
        f"Hi {full_name},\n\n"
        f"We received a request to reset your password.\n\n"
        f"Reset link: {reset_link}\n"
        f"Or use this token directly: {token}\n\n"
        f"This token expires in 1 hour. If you didn't request this, you can ignore this email.\n"
    )
    html = _wrap_html(
        'Reset your password',
        f"""<p>Hi {full_name},</p>
<p>We received a request to reset your password. Click the button below to set a new one.</p>
<p style="margin:24px 0;"><a href="{reset_link}" style="background:#2563eb; color:#fff; padding:10px 18px; border-radius:8px; text-decoration:none; display:inline-block;">Reset password</a></p>
<p style="font-size:13px; color:#475569;">Or paste this token in the reset form: <code style="background:#f1f5f9; padding:2px 6px; border-radius:4px;">{token}</code></p>
<p style="font-size:13px; color:#475569;">This link expires in 1 hour. If you didn't request this, you can safely ignore this email.</p>""",
    )
    send_email(to_email, subject, text, html)


def send_welcome_email(to_email: str, full_name: str, role: str) -> None:
    frontend = current_app.config.get('APP_FRONTEND_URL', 'http://localhost:3000')
    login_link = f"{frontend.rstrip('/')}/login"
    subject = 'Welcome to QR Transaction Protection'
    text = (
        f"Hi {full_name},\n\n"
        f"Your {role} account has been created.\n"
        f"Sign in: {login_link}\n\n"
        f"For your security, we strongly recommend enabling 2FA from your profile settings."
    )
    html = _wrap_html(
        f'Welcome, {full_name}',
        f"""<p>Your <strong>{role}</strong> account is ready.</p>
<p style="margin:24px 0;"><a href="{login_link}" style="background:#0f172a; color:#fff; padding:10px 18px; border-radius:8px; text-decoration:none; display:inline-block;">Sign in</a></p>
<p style="font-size:13px; color:#475569;">Tip: enable 2FA from your profile to add an extra layer of security to your transactions.</p>""",
    )
    send_email(to_email, subject, text, html)


def send_transaction_receipt(
    to_email: str,
    full_name: str,
    transaction_ref: str,
    amount: float,
    currency: str = 'MYR',
    status: str = 'completed',
    flagged: bool = False,
) -> None:
    subject = f'Transaction receipt — {transaction_ref}'
    flag_note = ''
    if flagged:
        flag_note = (
            "\nNote: This transaction was flagged by our AI tamper-detection system "
            "and is under review. You will be contacted if further action is needed.\n"
        )
    text = (
        f"Hi {full_name},\n\n"
        f"Your transaction has been {status}.\n\n"
        f"Reference: {transaction_ref}\n"
        f"Amount:    {currency} {amount:.2f}\n"
        f"Status:    {status}\n"
        f"{flag_note}\n"
        f"Keep this email for your records."
    )
    flag_html = ''
    if flagged:
        flag_html = (
            '<p style="background:#fef3c7; color:#92400e; padding:12px; border-radius:8px; '
            'font-size:13px;">Heads up: this transaction was flagged by our AI tamper-detection '
            'system and is under review.</p>'
        )
    html = _wrap_html(
        'Transaction receipt',
        f"""<p>Hi {full_name},</p>
<p>Your transaction has been <strong>{status}</strong>.</p>
<table style="width:100%; border-collapse:collapse; margin:16px 0;">
  <tr><td style="padding:8px 0; color:#475569;">Reference</td><td style="padding:8px 0; text-align:right;"><code>{transaction_ref}</code></td></tr>
  <tr><td style="padding:8px 0; color:#475569; border-top:1px solid #e5e7eb;">Amount</td><td style="padding:8px 0; text-align:right; border-top:1px solid #e5e7eb;"><strong>{currency} {amount:.2f}</strong></td></tr>
  <tr><td style="padding:8px 0; color:#475569; border-top:1px solid #e5e7eb;">Status</td><td style="padding:8px 0; text-align:right; border-top:1px solid #e5e7eb;">{status}</td></tr>
</table>
{flag_html}
<p style="font-size:13px; color:#475569;">Keep this email for your records.</p>""",
    )
    send_email(to_email, subject, text, html)


def send_tamper_alert_email(
    admin_emails: Iterable[str],
    transaction_ref: str,
    user_email: str,
    amount: float,
    anomaly_score: float,
    details: str,
) -> None:
    admin_list = [e for e in admin_emails if e]
    if not admin_list:
        return
    subject = f'[ALERT] Tamper detected on {transaction_ref}'
    text = (
        f"AI tamper detection has flagged a transaction.\n\n"
        f"Transaction: {transaction_ref}\n"
        f"User:        {user_email}\n"
        f"Amount:      {amount}\n"
        f"Score:       {anomaly_score}\n"
        f"Details:     {details}\n\n"
        f"Review it in the admin dashboard."
    )
    html = _wrap_html(
        'Tamper detection alert',
        f"""<p style="background:#fee2e2; color:#991b1b; padding:12px; border-radius:8px;">
<strong>An anomalous transaction was detected.</strong></p>
<table style="width:100%; border-collapse:collapse; margin:16px 0;">
  <tr><td style="padding:8px 0; color:#475569;">Transaction</td><td style="padding:8px 0; text-align:right;"><code>{transaction_ref}</code></td></tr>
  <tr><td style="padding:8px 0; color:#475569; border-top:1px solid #e5e7eb;">User</td><td style="padding:8px 0; text-align:right; border-top:1px solid #e5e7eb;">{user_email}</td></tr>
  <tr><td style="padding:8px 0; color:#475569; border-top:1px solid #e5e7eb;">Amount</td><td style="padding:8px 0; text-align:right; border-top:1px solid #e5e7eb;">{amount}</td></tr>
  <tr><td style="padding:8px 0; color:#475569; border-top:1px solid #e5e7eb;">Anomaly score</td><td style="padding:8px 0; text-align:right; border-top:1px solid #e5e7eb;">{anomaly_score}</td></tr>
</table>
<p style="font-size:13px; color:#475569;">{details}</p>
<p style="font-size:13px; color:#475569;">Review it in the admin dashboard.</p>""",
    )
    send_email(admin_list, subject, text, html)
