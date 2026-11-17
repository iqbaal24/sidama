"""Notification fan-out and Telegram transport."""
from __future__ import annotations

import json
import logging
import urllib.error
import urllib.request

from django.conf import settings

from apps.accounts.models import User
from apps.core.models import Setting
from apps.notifications.models import Notification

logger = logging.getLogger("sidama.notifications")


def notify_user(user, *, title: str, message: str = "", url: str = "",
                level: str = Notification.Level.INFO) -> Notification | None:
    if user is None:
        return None
    return Notification.objects.create(
        user=user, title=title[:160], message=message[:500], url=url[:300],
        level=level,
    )


def notify_roles(roles, *, title: str, message: str = "", url: str = "",
                 level: str = Notification.Level.INFO) -> int:
    recipients = User.objects.filter(role__in=list(roles), is_active=True)
    created = 0
    for user in recipients:
        notify_user(user, title=title, message=message, url=url, level=level)
        created += 1
    return created


def telegram_credentials() -> tuple[str, str]:
    token = getattr(settings, "TELEGRAM_BOT_TOKEN", "") or ""
    chat_id = Setting.get("telegram_chat_id", "") or ""
    return token, chat_id


def send_telegram(text: str) -> bool:
    """Send a Telegram message when credentials are configured.

    Returns ``True`` when the API accepted the message. Without credentials the
    message is only logged, so local demos keep working offline.
    """
    token, chat_id = telegram_credentials()
    if not token or not chat_id:
        logger.info("Telegram dilewati (token/chat id belum diatur): %s", text[:120])
        return False
    payload = json.dumps({
        "chat_id": chat_id,
        "text": text,
        "parse_mode": "HTML",
        "disable_web_page_preview": True,
    }).encode()
    request = urllib.request.Request(
        f"https://api.telegram.org/bot{token}/sendMessage",
        data=payload,
        headers={"Content-Type": "application/json"},
    )
    try:
        with urllib.request.urlopen(request, timeout=10) as response:
            return response.status == 200
    except (urllib.error.URLError, urllib.error.HTTPError, TimeoutError) as exc:
        logger.warning("Telegram gagal dikirim: %s", exc)
        return False


def send_telegram_async(text: str) -> None:
    from apps.notifications.tasks import send_telegram_task

    try:
        send_telegram_task.delay(text)
    except Exception:  # noqa: BLE001 - broker may be unavailable in local dev
        logger.info("Broker tidak tersedia, kirim Telegram langsung.")
        send_telegram(text)
