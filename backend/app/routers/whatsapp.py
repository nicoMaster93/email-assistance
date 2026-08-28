import json
import re
from datetime import datetime, timezone
from urllib.parse import quote
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Request, status

from app.config import WHATSAPP_NUMBER_ASSISTANT
from app.db import db_session, sql
from app.dependencies import CurrentUser, require_owner
from app.openai_client import answer_whatsapp_assistant
from app.schemas import WhatsAppNotificationPreferencesUpdate, WhatsAppSetupRequest, WhatsAppSetupResponse, WhatsAppWebhookRequest
from app.whatsapp_client import send_whatsapp_text, send_whatsapp_text_result, whatsapp_chat_id_from_number

router = APIRouter(prefix="/whatsapp", tags=["whatsapp"])


def _normalize_phone(value: str | None) -> str:
    return re.sub(r"\D+", "", value or "")


def _looks_like_phone(value: str | None) -> bool:
    """WAHA a veces manda @lid (Linked ID) en vez del numero real."""
    digits = _normalize_phone(value)
    if not digits or not (8 <= len(digits) <= 15):
        return False
    raw = str(value or "").lower()
    if "@lid" in raw:
        return False
    return True


def _prefer_phone_candidates(raw_values: list) -> tuple[list[str], list[str]]:
    """Separa numeros reales (@s.whatsapp.net) de Linked IDs (@lid)."""
    phones: list[str] = []
    others: list[str] = []
    for raw in raw_values:
        if not raw:
            continue
        normalized = _normalize_phone(str(raw))
        if not normalized:
            continue
        if _looks_like_phone(str(raw)):
            if normalized not in phones:
                phones.append(normalized)
        elif normalized not in others and normalized not in phones:
            others.append(normalized)
    return phones, others


def _best_phone_candidate(phone_candidates: list[str], fallback: list[str] | None = None) -> str | None:
    if phone_candidates:
        return phone_candidates[0]
    return None


def _timestamp_to_iso(value) -> str | None:
    if value is None:
        return None
    try:
        number = int(value)
        if number > 9_999_999_999:
            number = number // 1000
        return datetime.fromtimestamp(number, tz=timezone.utc).isoformat()
    except Exception:
        return None


def _compact_metadata(payload: dict, from_candidates: list[str], message: str) -> dict:
    event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    data = event_payload.get("_data") if isinstance(event_payload.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}
    me = payload.get("me") if isinstance(payload.get("me"), dict) else {}
    environment = payload.get("environment") if isinstance(payload.get("environment"), dict) else {}

    return {
        "source": "whatsapp_webhook",
        "event_id": payload.get("id"),
        "event": payload.get("event"),
        "session": payload.get("session"),
        "event_timestamp": _timestamp_to_iso(payload.get("timestamp")),
        "assistant_id": me.get("id"),
        "assistant_name": me.get("pushName"),
        "message_id": event_payload.get("id"),
        "message_timestamp": _timestamp_to_iso(event_payload.get("timestamp") or data.get("messageTimestamp")),
        "from": event_payload.get("from"),
        "from_alt": key.get("remoteJidAlt"),
        "from_candidates": from_candidates,
        "push_name": data.get("pushName"),
        "body": message,
        "from_me": event_payload.get("fromMe"),
        "source_app": event_payload.get("source"),
        "has_media": event_payload.get("hasMedia"),
        "ack": event_payload.get("ack"),
        "ack_name": event_payload.get("ackName"),
        "engine": payload.get("engine"),
        "environment_version": environment.get("version"),
        "environment_tier": environment.get("tier"),
        "reply_chat_id": event_payload.get("from"),
        "reply_session": payload.get("session"),
    }


def _extract_webhook_fields(payload: dict) -> tuple[list[str], list[str], str, dict]:
    event_payload = payload.get("payload") if isinstance(payload.get("payload"), dict) else {}
    data = event_payload.get("_data") if isinstance(event_payload.get("_data"), dict) else {}
    key = data.get("key") if isinstance(data.get("key"), dict) else {}

    # Prioridad: remoteJidAlt / participantAlt suelen traer el numero real cuando from es @lid
    raw_from_values = [
        key.get("remoteJidAlt"),
        key.get("participantAlt"),
        event_payload.get("participantAlt"),
        event_payload.get("replyTo"),
        payload.get("from_number"),
        payload.get("phone"),
        payload.get("wa_id"),
        payload.get("sender"),
        event_payload.get("from"),
        key.get("participant"),
        key.get("remoteJid"),
        payload.get("from"),
    ]
    candidates_message = [
        payload.get("message"),
        payload.get("text"),
        payload.get("body"),
        event_payload.get("body"),
    ]
    whatsapp_message = data.get("message") if isinstance(data.get("message"), dict) else {}
    candidates_message.append(whatsapp_message.get("conversation"))

    entry = payload.get("entry")
    if isinstance(entry, list):
        for entry_item in entry:
            for change in entry_item.get("changes", []) if isinstance(entry_item, dict) else []:
                value = change.get("value", {})
                messages = value.get("messages") or []
                if messages:
                    message = messages[0]
                    raw_from_values.append(message.get("from"))
                    text = message.get("text") or {}
                    candidates_message.append(text.get("body"))

    phone_candidates, lid_candidates = _prefer_phone_candidates(raw_from_values)
    from_candidates = phone_candidates + [item for item in lid_candidates if item not in phone_candidates]
    message = next((str(item) for item in candidates_message if item), "")
    metadata = _compact_metadata(payload, from_candidates, message)
    metadata["phone_candidates"] = phone_candidates
    metadata["lid_candidates"] = lid_candidates
    reply_from_phone = next((str(v) for v in raw_from_values if v and _looks_like_phone(str(v))), None)
    if reply_from_phone:
        metadata["reply_chat_id"] = reply_from_phone if "@" in str(reply_from_phone) else f"{_normalize_phone(reply_from_phone)}@c.us"
    return from_candidates, phone_candidates, message, metadata


def _connected_context(conn, from_candidates: list[str]) -> tuple[dict | None, list[dict]]:
    placeholders = ",".join("?" for _ in from_candidates)
    rows = conn.execute(
        sql(
            f"""
            SELECT gc.id, gc.organization_id, gc.display_name, gc.email, gc.whatsapp_number
            FROM google_connections gc
            WHERE gc.whatsapp_status = 'connected'
              AND gc.whatsapp_number IN ({placeholders})
            ORDER BY gc.updated_at DESC
            """
        ),
        tuple(from_candidates),
    ).fetchall()
    if not rows:
        return None, []

    connection = dict(rows[0])
    rules = conn.execute(
        sql(
            """
            SELECT ar.id, ar.name, ar.action_type, ar.configuration
            FROM automation_rules ar
            JOIN rule_connections rc ON rc.rule_id = ar.id
            WHERE rc.google_connection_id = ?
              AND rc.whatsapp_notifications_enabled
              AND ar.is_active
            ORDER BY ar.created_at DESC
            """
        ),
        (connection["id"],),
    ).fetchall()
    return connection, [dict(rule) for rule in rules]


@router.post("/connections/{connection_id}/setup", response_model=WhatsAppSetupResponse)
def start_whatsapp_setup(
    connection_id: int,
    payload: WhatsAppSetupRequest,
    user: dict = CurrentUser,
) -> WhatsAppSetupResponse:
    require_owner(user)
    assistant_number = _normalize_phone(WHATSAPP_NUMBER_ASSISTANT)
    if not assistant_number:
        raise HTTPException(status.HTTP_500_INTERNAL_SERVER_ERROR, "Falta WHATSAPP_NUMBER_ASSISTANT en backend/.env")

    phone_number = _normalize_phone(payload.phone_number)
    if len(phone_number) < 8:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Numero de WhatsApp invalido")

    token = uuid4().hex[:10].upper()
    message = f"Hola, quiero que me notifiques. Codigo: {token}"
    whatsapp_url = f"https://wa.me/{assistant_number}?text={quote(message)}"

    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
            (connection_id, user["organization_id"]),
        ).fetchone()
        if not connection:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET whatsapp_number = ?,
                    whatsapp_status = 'pending',
                    whatsapp_verification_token = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (phone_number, token, connection_id, user["organization_id"]),
        )

    return WhatsAppSetupResponse(
        google_connection_id=connection_id,
        assistant_number=assistant_number,
        phone_number=phone_number,
        verification_token=token,
        message=message,
        whatsapp_url=whatsapp_url,
        status="pending",
    )


@router.patch("/connections/{connection_id}/preferences")
def update_whatsapp_preferences(
    connection_id: int,
    payload: WhatsAppNotificationPreferencesUpdate,
    user: dict = CurrentUser,
) -> dict:
    require_owner(user)
    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
            (connection_id, user["organization_id"]),
        ).fetchone()
        if not connection:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET whatsapp_notifications_enabled = ?,
                    whatsapp_notify_new_email = ?,
                    whatsapp_notify_followup_overdue = ?,
                    whatsapp_notify_followup_warning = ?,
                    whatsapp_notify_followup_late = ?,
                    whatsapp_notify_followup_responded = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (
                payload.notifications_enabled,
                payload.notify_new_email,
                payload.notify_followup_overdue,
                payload.notify_followup_warning,
                payload.notify_followup_late,
                payload.notify_followup_responded,
                connection_id,
                user["organization_id"],
            ),
        )

    return {"status": "ok", "google_connection_id": connection_id}


@router.post("/webhook")
async def whatsapp_webhook(request: Request) -> dict:
    raw_payload = await request.json()
    payloads = raw_payload if isinstance(raw_payload, list) else [raw_payload]
    results = []

    for raw_item in payloads:
        if not isinstance(raw_item, dict):
            results.append({"status": "ignored", "reason": "invalid payload item"})
            continue

        parsed_payload = WhatsAppWebhookRequest(**raw_item)
        payload = {**parsed_payload.payload, **raw_item}
        from_candidates, phone_candidates, message, metadata = _extract_webhook_fields(
            {
                **payload,
                "from_number": parsed_payload.from_number or payload.get("from_number"),
                "message": parsed_payload.message or payload.get("message"),
            }
        )

        if not from_candidates or not message:
            results.append({"status": "ignored", "reason": "missing from_number or message"})
            continue

        with db_session() as conn:
            pending_rows = conn.execute(
                sql(
                    """
                    SELECT id, organization_id, whatsapp_number, whatsapp_verification_token
                    FROM google_connections
                    WHERE whatsapp_status = 'pending'
                    ORDER BY updated_at DESC
                    """
                )
            ).fetchall()

            matched = None
            matched_phone: str | None = None
            for row in pending_rows:
                token = row["whatsapp_verification_token"]
                if not token or token not in message:
                    continue
                pending_number = _normalize_phone(row["whatsapp_number"])
                # 1) Numero registrado coincide con telefono real o lid
                if pending_number in from_candidates:
                    matched = row
                    matched_phone = pending_number
                    break
                # 2) Codigo correcto + WAHA trajo telefono real (@s.whatsapp.net / remoteJidAlt)
                best_phone = _best_phone_candidate(phone_candidates)
                if best_phone:
                    matched = row
                    matched_phone = best_phone
                    break
                # 3) Solo llego @lid: conectar igual por codigo y conservar el numero digitado
                matched = row
                matched_phone = pending_number
                break

            if not matched:
                connected_connection, notification_rules = _connected_context(conn, from_candidates)
                reply_chat_id = metadata.get("reply_chat_id") or payload.get("from")
                reply_session = metadata.get("reply_session")

                if connected_connection:
                    answer = answer_whatsapp_assistant(
                        message,
                        {
                            "connection": connected_connection,
                            "rules": notification_rules,
                            "restriction": "Solo responder sobre correos marcados por reglas con notificaciones WhatsApp habilitadas.",
                        },
                        organization_id=connected_connection.get("organization_id"),
                        google_connection_id=connected_connection.get("id"),
                    )
                    send_result = send_whatsapp_text_result(
                        reply_session,
                        whatsapp_chat_id_from_number(connected_connection["whatsapp_number"]) or reply_chat_id,
                        answer,
                    )
                    conn.execute(
                        sql(
                            """
                            INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
                            VALUES (?, ?, 'info', 'whatsapp_assistant_replied', 'Asistente WhatsApp respondio mensaje entrante', ?)
                            """
                        ),
                        (
                            connected_connection["organization_id"],
                            connected_connection["id"],
                            json.dumps({**metadata, "sent": send_result.sent, "send_result": send_result.to_dict(), "answer": answer}, ensure_ascii=False),
                        ),
                    )
                    results.append(
                        {
                            "status": "ok",
                            "reason": "assistant replied",
                            "google_connection_id": connected_connection["id"],
                            "sent": send_result.sent,
                            "send_result": send_result.to_dict(),
                        }
                    )
                    continue

                conn.execute(
                    sql(
                        """
                        INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
                        VALUES (NULL, NULL, 'info', 'whatsapp_unknown_number_ignored', 'Mensaje WhatsApp ignorado porque el numero no esta en whitelist', ?)
                        """
                    ),
                    (json.dumps(metadata, ensure_ascii=False),),
                )
                results.append(
                    {
                        "status": "ignored",
                        "reason": "unknown whatsapp number",
                        "from_candidates": from_candidates,
                        "sent": False,
                        "ai_consumed": False,
                    }
                )
                continue

            message_id = metadata.get("message_id")
            message_at = metadata.get("message_timestamp")
            contact_name = metadata.get("push_name")
            phone_to_store = matched_phone or _normalize_phone(matched["whatsapp_number"])
            conn.execute(
                sql(
                    """
                    UPDATE google_connections
                    SET whatsapp_status = 'connected',
                        whatsapp_number = ?,
                        whatsapp_verification_token = NULL,
                        whatsapp_contact_name = ?,
                        whatsapp_last_message_id = ?,
                        whatsapp_last_message_at = ?,
                        updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """
                ),
                (phone_to_store, contact_name, message_id, message_at, matched["id"]),
            )
            conn.execute(
                sql(
                    """
                    INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
                    VALUES (?, ?, 'info', 'whatsapp_connected', 'Numero WhatsApp asociado correctamente', ?)
                    """
                ),
                (matched["organization_id"], matched["id"], json.dumps(metadata, ensure_ascii=False)),
            )

        results.append(
            {
                "status": "ok",
                "google_connection_id": matched["id"],
                "phone_number": phone_to_store,
                "message_id": metadata.get("message_id"),
            }
        )
        send_whatsapp_text(
            metadata.get("reply_session"),
            metadata.get("reply_chat_id"),
            "Listo, tu numero quedo asociado. Te notificare solo sobre correos que coincidan con reglas habilitadas para WhatsApp.",
        )

    if len(results) == 1:
        return results[0]
    return {"status": "ok", "results": results}
