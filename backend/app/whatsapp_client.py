from dataclasses import asdict, dataclass

import httpx

from app.config import WHATSAPP_SEND_SESSION, WHATSAPP_SEND_TEXT_TOKEN, WHATSAPP_SEND_TEXT_URL


@dataclass
class WhatsAppSendResult:
    sent: bool
    reason: str
    status_code: int | None = None
    response_text: str | None = None
    chat_id: str | None = None

    def to_dict(self) -> dict:
        return asdict(self)


def send_whatsapp_text_result(session: str | None, chat_id: str, text: str) -> WhatsAppSendResult:
    if not WHATSAPP_SEND_TEXT_URL or not chat_id or not text:
        missing = []
        if not WHATSAPP_SEND_TEXT_URL:
            missing.append("WHATSAPP_SEND_TEXT_URL")
        if not chat_id:
            missing.append("chat_id")
        if not text:
            missing.append("text")
        return WhatsAppSendResult(False, f"missing {', '.join(missing)}", chat_id=chat_id)

    headers = {"Content-Type": "application/json"}
    if WHATSAPP_SEND_TEXT_TOKEN:
        headers["Authorization"] = f"Bearer {WHATSAPP_SEND_TEXT_TOKEN}"

    payload = {
        "session": session,
        "chatId": chat_id,
        "text": text,
    }
    try:
        with httpx.Client(timeout=20, trust_env=False) as client:
            response = client.post(WHATSAPP_SEND_TEXT_URL, headers=headers, json=payload)
    except httpx.HTTPError as exc:
        return WhatsAppSendResult(False, exc.__class__.__name__, response_text=str(exc), chat_id=chat_id)

    response_text = response.text[:500] if response.text else None
    return WhatsAppSendResult(
        response.status_code < 400,
        "ok" if response.status_code < 400 else "http_error",
        status_code=response.status_code,
        response_text=response_text,
        chat_id=chat_id,
    )


def send_whatsapp_text(session: str | None, chat_id: str, text: str) -> bool:
    return send_whatsapp_text_result(session, chat_id, text).sent


def whatsapp_chat_id_from_number(phone_number: str | None) -> str | None:
    if not phone_number:
        return None
    normalized = "".join(ch for ch in phone_number if ch.isdigit())
    if not normalized:
        return None
    return f"{normalized}@c.us"


def send_whatsapp_text_to_number(phone_number: str | None, text: str) -> bool:
    chat_id = whatsapp_chat_id_from_number(phone_number)
    if not chat_id:
        return False
    return send_whatsapp_text(WHATSAPP_SEND_SESSION, chat_id, text)
