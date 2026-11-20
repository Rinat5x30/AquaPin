"""Telegram bot: thin conversation over the same services as the web UI."""

from __future__ import annotations

import datetime as dt
import logging
import re
from typing import Any, Protocol

import requests
from django.conf import settings
from django.utils import timezone

from aquapin_core.errors import AquaPinError

from .i18n import error_text, tr
from .models import BotSession, Field, Job, Result
from .ratelimit import allow
from .render import advice_text
from .services import create_field_job, default_planting_date, delete_owner_data

log = logging.getLogger(__name__)
DEFAULT_RADIUS_M = 150.0
DEFAULT_CROP = "winter_wheat"
_DATE = re.compile(r"^\d{4}-\d{2}-\d{2}$")

BOT_TEXT: dict[str, dict[str, str]] = {
    "en": {
        "start": "AquaPin: send me your field location (the paperclip, then Location) and I will "
        "tell you whether to irrigate today. I store the location only to calculate the advice. "
        "/delete removes all your data.",
        "consent": "To calculate I must store this location. Reply /agree to continue, /delete to cancel.",
        "ask_date": "Send the planting date as YYYY-MM-DD, or /skip to assume 1 November (winter wheat).",
        "queued": "Calculating. This can take a minute or two; I will write when it is ready.",
        "bad_date": "I did not understand the date. Use YYYY-MM-DD, for example 2025-11-01, or /skip.",
        "deleted": "Done. Your locations and results are deleted.",
        "bad_geo": "That location is not valid for AquaPin.",
        "limit": "Too many messages. Please wait a minute.",
        "example": "Open the web example to see a full season replay.",
        "need_location": "Send a location first.",
    },
    "ru": {
        "start": "AquaPin: пришлите место вашего поля (скрепка, затем «Геопозиция»), и я скажу, "
        "нужен ли сегодня полив. Место хранится только для расчёта совета. "
        "/delete удаляет все ваши данные.",
        "consent": "Для расчёта нужно сохранить это место. Ответьте /agree, чтобы продолжить, или /delete для отмены.",
        "ask_date": "Пришлите дату посева в формате ГГГГ-ММ-ДД или /skip, чтобы принять 1 ноября (озимая пшеница).",
        "queued": "Считаю. Это может занять минуту-две, напишу, когда будет готово.",
        "bad_date": "Не понял дату. Формат ГГГГ-ММ-ДД, например 2025-11-01, или /skip.",
        "deleted": "Готово. Ваши места и результаты удалены.",
        "bad_geo": "Это место не подходит для AquaPin.",
        "limit": "Слишком много сообщений. Подождите минуту.",
        "example": "Откройте веб-пример, чтобы увидеть повтор целого сезона.",
        "need_location": "Сначала пришлите геопозицию.",
    },
}


class Messenger(Protocol):
    def send_message(self, chat_id: int, text: str) -> bool: ...


class TelegramClient:
    def __init__(self, token: str | None = None, session: requests.Session | None = None) -> None:
        self._token = settings.TELEGRAM_BOT_TOKEN if token is None else token
        self._session = session or requests.Session()

    def send_message(self, chat_id: int, text: str) -> bool:
        if not self._token:
            log.warning("TELEGRAM_BOT_TOKEN is not set; message to %s not sent", chat_id)
            return False
        try:
            resp = self._session.post(
                f"https://api.telegram.org/bot{self._token}/sendMessage",
                json={"chat_id": chat_id, "text": text},
                timeout=15,
            )
            resp.raise_for_status()
        except requests.exceptions.RequestException as exc:
            log.warning("telegram send failed for chat %s: %s", chat_id, type(exc).__name__)
            return False
        return True


def _msg(lang: str, key: str) -> str:
    return BOT_TEXT.get(lang, BOT_TEXT["en"])[key]


def _queue(session: BotSession, planting: dt.date, client: Messenger, today: dt.date) -> None:
    owner = f"tg:{session.chat_id}"
    try:
        create_field_job(
            owner_key=owner,
            lat=float(session.pending_lat or 0.0),
            lon=float(session.pending_lon or 0.0),
            radius_m=DEFAULT_RADIUS_M,
            crop_id=DEFAULT_CROP,
            planting=planting,
            today=today,
        )
    except AquaPinError:
        client.send_message(session.chat_id, _msg(session.lang, "bad_geo"))
        return
    finally:
        session.state = BotSession.State.IDLE
        session.pending_lat = session.pending_lon = None
        session.save()
    client.send_message(session.chat_id, _msg(session.lang, "queued"))


def handle_update(update: dict[str, Any], client: Messenger, today: dt.date | None = None) -> None:
    today = today or dt.date.today()
    message = update.get("message")
    if not isinstance(message, dict):
        return
    chat = message.get("chat")
    chat_id = chat.get("id") if isinstance(chat, dict) else None
    if not isinstance(chat_id, int):
        return
    raw_sender = message.get("from")
    sender: dict[str, Any] = raw_sender if isinstance(raw_sender, dict) else {}
    lang = "ru" if str(sender.get("language_code", "")).lower().startswith("ru") else "en"
    session, _ = BotSession.objects.get_or_create(chat_id=chat_id, defaults={"lang": lang})
    if not allow(f"tg:{chat_id}", 20, 60):
        if allow(f"tg-warn:{chat_id}", 1, 60):  # warn once per window, then stay silent
            client.send_message(chat_id, _msg(session.lang, "limit"))
        return

    raw_text = message.get("text")
    text = raw_text.strip() if isinstance(raw_text, str) else ""
    command = text.split()[0].split("@")[0].lower() if text.startswith("/") else ""
    raw_location = message.get("location")
    location = raw_location if isinstance(raw_location, dict) else None

    if command in {"/start", "/help"}:
        client.send_message(chat_id, _msg(session.lang, "start"))
    elif command == "/example":
        client.send_message(chat_id, _msg(session.lang, "example"))
    elif command == "/delete":
        delete_owner_data(f"tg:{chat_id}")
        session.state, session.consent_at = BotSession.State.IDLE, None
        session.pending_lat = session.pending_lon = None
        session.save()
        client.send_message(chat_id, _msg(session.lang, "deleted"))
    elif command == "/agree":
        if session.pending_lat is None:
            client.send_message(chat_id, _msg(session.lang, "need_location"))
            return
        session.consent_at, session.state = timezone.now(), BotSession.State.AWAIT_DATE
        session.save()
        client.send_message(chat_id, _msg(session.lang, "ask_date"))
    elif command == "/skip" and session.state == BotSession.State.AWAIT_DATE:
        _queue(session, default_planting_date(today), client, today)
    elif location is not None:
        try:
            lat, lon = float(location["latitude"]), float(location["longitude"])
        except (KeyError, TypeError, ValueError):
            return
        session.pending_lat, session.pending_lon = lat, lon
        if session.consent_at is None:
            session.state = BotSession.State.AWAIT_CONSENT
            session.save()
            client.send_message(chat_id, _msg(session.lang, "consent"))
        else:
            session.state = BotSession.State.AWAIT_DATE
            session.save()
            client.send_message(chat_id, _msg(session.lang, "ask_date"))
    elif session.state == BotSession.State.AWAIT_DATE and text:
        if not _DATE.match(text):
            client.send_message(chat_id, _msg(session.lang, "bad_date"))
            return
        try:
            planting = dt.date.fromisoformat(text)
        except ValueError:
            client.send_message(chat_id, _msg(session.lang, "bad_date"))
            return
        _queue(session, planting, client, today)
    else:
        client.send_message(chat_id, _msg(session.lang, "start"))


def notify_job(job: Job, client: Messenger) -> None:
    """Send the result (or a plain error) to the chat that owns the field."""
    owner = job.field.owner_key
    if not owner.startswith("tg:"):
        return
    chat_id = int(owner[3:])
    session = BotSession.objects.filter(chat_id=chat_id).first()
    lang = session.lang if session else "en"
    if job.status == Job.Status.DONE:
        result = Result.objects.filter(field=job.field).order_by("-computed_on", "-id").first()
        if result is not None:
            client.send_message(chat_id, advice_text(result.payload["advice_final"], lang))
    elif job.status == Job.Status.FAILED:
        client.send_message(chat_id, error_text(lang, job.error_code) or tr(lang, "failed"))


def field_for_chat(chat_id: int) -> Field | None:
    return Field.objects.filter(owner_key=f"tg:{chat_id}").order_by("-created_at").first()
