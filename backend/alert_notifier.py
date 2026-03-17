import smtplib
from email.mime.text import MIMEText

import requests

from observability import ALERTS_SENT_TOTAL
from settings import settings


def _format_alerts(alerts: list[dict]) -> str:
    if not alerts:
        return "No active alerts."
    lines = ["AirQ Alerts:"]
    for alert in alerts:
        sev = alert.get("severity", "info").upper()
        code = alert.get("code", "UNKNOWN")
        msg = alert.get("message", "")
        lines.append(f"- [{sev}] {code}: {msg}")
    return "\n".join(lines)


def _notify_slack(message: str) -> bool:
    if not settings.SLACK_WEBHOOK_URL:
        return False
    res = requests.post(settings.SLACK_WEBHOOK_URL, json={"text": message}, timeout=10)
    return 200 <= res.status_code < 300


def _notify_telegram(message: str) -> bool:
    if not settings.TELEGRAM_BOT_TOKEN or not settings.TELEGRAM_CHAT_ID:
        return False
    url = f"https://api.telegram.org/bot{settings.TELEGRAM_BOT_TOKEN}/sendMessage"
    payload = {"chat_id": settings.TELEGRAM_CHAT_ID, "text": message}
    res = requests.post(url, json=payload, timeout=10)
    return 200 <= res.status_code < 300


def _notify_email(message: str) -> bool:
    if not settings.ALERT_EMAIL_TO:
        return False
    if not settings.SMTP_HOST or not settings.SMTP_FROM:
        return False
    msg = MIMEText(message)
    msg["Subject"] = "AirQ Alert Notification"
    msg["From"] = settings.SMTP_FROM
    msg["To"] = settings.ALERT_EMAIL_TO

    with smtplib.SMTP(settings.SMTP_HOST, settings.SMTP_PORT, timeout=10) as smtp:
        smtp.starttls()
        if settings.SMTP_USERNAME:
            smtp.login(settings.SMTP_USERNAME, settings.SMTP_PASSWORD)
        smtp.sendmail(settings.SMTP_FROM, [settings.ALERT_EMAIL_TO], msg.as_string())
    return True


def send_alerts(alerts: list[dict]) -> dict:
    message = _format_alerts(alerts)
    outcomes: dict[str, str] = {}
    for channel in settings.ALERT_CHANNELS:
        try:
            if channel == "slack":
                ok = _notify_slack(message)
            elif channel == "telegram":
                ok = _notify_telegram(message)
            elif channel == "email":
                ok = _notify_email(message)
            else:
                outcomes[channel] = "unsupported_channel"
                ALERTS_SENT_TOTAL.labels(channel=channel, status="unsupported").inc()
                continue

            status = "sent" if ok else "skipped_or_failed"
            outcomes[channel] = status
            ALERTS_SENT_TOTAL.labels(channel=channel, status=status).inc()
        except Exception:
            outcomes[channel] = "error"
            ALERTS_SENT_TOTAL.labels(channel=channel, status="error").inc()
    return outcomes
