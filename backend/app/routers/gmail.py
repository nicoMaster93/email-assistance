import json
import base64
import re
import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from uuid import uuid4

from fastapi import APIRouter, HTTPException, Query, status

from app.config import ATTACHMENTS_DIR, GOOGLE_PUBSUB_TOPIC
from app.db import db_session, sql, using_postgres
from app.dependencies import CurrentUser, require_connection_access, require_owner
from app.followups import create_followup_for_message, evaluate_pending_followups
from app.google_client import gmail_get, gmail_get_attachment, gmail_post, refresh_access_token
from app.openai_client import email_matches_ai_rule
from app.schemas import EmailMessageResponse, GmailSyncResponse, GmailWatchRequest, GmailWatchResponse, PubSubPushRequest
from app.whatsapp_client import send_whatsapp_text_to_number

router = APIRouter(prefix="/gmail", tags=["gmail"])


def _serialize_message(row) -> EmailMessageResponse:
    return EmailMessageResponse(
        id=row["id"],
        google_connection_id=row["google_connection_id"],
        connection_email=row["connection_email"] if "connection_email" in row.keys() else None,
        gmail_message_id=row["gmail_message_id"],
        gmail_thread_id=row["gmail_thread_id"],
        subject=row["subject"],
        sender=row["sender"],
        recipients=row["recipients"],
        received_at=str(row["received_at"]) if row["received_at"] else None,
        snippet=row["snippet"],
        has_attachments=bool(row["has_attachments"]),
        matched_rule_id=row["matched_rule_id"] if "matched_rule_id" in row.keys() else None,
        matched_rule_name=row["matched_rule_name"] if "matched_rule_name" in row.keys() else None,
        status=row["status"],
        created_at=str(row["created_at"]),
    )


def _header(headers: list[dict], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _has_attachments(payload: dict | None) -> bool:
    if not payload:
        return False

    parts = payload.get("parts") or []
    for part in parts:
        if part.get("filename") and part.get("body", {}).get("attachmentId"):
            return True
        if _has_attachments(part):
            return True
    return False


def _attachment_parts(payload: dict | None) -> list[dict]:
    if not payload:
        return []

    found = []
    for part in payload.get("parts") or []:
        body = part.get("body") or {}
        if part.get("filename") and body.get("attachmentId"):
            found.append(part)
        found.extend(_attachment_parts(part))
    return found


def _received_at(message: dict) -> str | None:
    internal_date = message.get("internalDate")
    if not internal_date:
        return None
    return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc).isoformat()


def _parse_datetime(value: str | datetime | None) -> datetime | None:
    if not value:
        return None
    if isinstance(value, datetime):
        parsed = value
    else:
        parsed = datetime.fromisoformat(str(value).replace("Z", "+00:00"))
    if parsed.tzinfo is None:
        return parsed.replace(tzinfo=timezone.utc)
    return parsed.astimezone(timezone.utc)


def _watch_is_active(connection) -> bool:
    expiration = _parse_datetime(connection["watch_expiration_at"])
    return bool(expiration and expiration > datetime.now(timezone.utc))


def _desired_watch_is_active(connection) -> bool:
    desired_until = _parse_datetime(connection["watch_desired_until"])
    return bool(desired_until and desired_until > datetime.now(timezone.utc))


def _normalize_future_datetime(value: str, field_name: str) -> datetime:
    parsed = _parse_datetime(value)
    if not parsed or parsed <= datetime.now(timezone.utc):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, f"{field_name} debe ser una fecha futura")
    return parsed


def _get_connection(conn, connection_id: int, organization_id: int):
    connection = conn.execute(
        sql("SELECT * FROM google_connections WHERE id = ? AND organization_id = ?"),
        (connection_id, organization_id),
    ).fetchone()
    if not connection:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")
    return connection


def _connection_rule_count(conn, organization_id: int, connection_id: int) -> int:
    row = conn.execute(
        sql(
            """
            SELECT COUNT(*) AS total
            FROM automation_rules ar
            JOIN rule_connections rc ON rc.rule_id = ar.id
            WHERE ar.organization_id = ?
              AND ar.is_active
              AND rc.google_connection_id = ?
            """
        ),
        (organization_id, connection_id),
    ).fetchone()
    return int(row["total"] or 0)


def _ensure_connection_has_rules(conn, organization_id: int, connection_id: int) -> None:
    if _connection_rule_count(conn, organization_id, connection_id) == 0:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "La cuenta debe tener al menos una regla activa asociada antes de sincronizar.",
        )


def _log_event(conn, organization_id: int | None, connection_id: int | None, level: str, event_type: str, message: str, metadata: dict | None = None) -> None:
    conn.execute(
        sql(
            """
            INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        ),
        (organization_id, connection_id, level, event_type, message, json.dumps(metadata or {})),
    )


def _register_gmail_watch(
    conn,
    connection,
    desired_until: datetime,
    manual: bool,
) -> GmailWatchResponse:
    access_token, expires_at = refresh_access_token(connection["encrypted_refresh_token"])
    response = gmail_post(
        access_token,
        "/users/me/watch",
        {
            "topicName": GOOGLE_PUBSUB_TOPIC,
            "labelIds": ["INBOX"],
        },
    )
    expiration = response.get("expiration")
    expiration_iso = None
    if expiration:
        expiration_iso = datetime.fromtimestamp(int(expiration) / 1000, tz=timezone.utc).isoformat()

    conn.execute(
        sql(
            """
            UPDATE google_connections
            SET gmail_history_id = ?,
                watch_expiration_at = ?,
                watch_desired_until = ?,
                access_token_expires_at = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
        ),
        (
            response.get("historyId"),
            expiration_iso,
            desired_until if using_postgres() else desired_until.isoformat(),
            expires_at if using_postgres() else expires_at.isoformat(),
            connection["id"],
        ),
    )
    if manual:
        _log_event(
            conn,
            connection["organization_id"],
            connection["id"],
            "info",
            "gmail_watch_registered",
            "Monitor Gmail registrado correctamente",
            {
                **response,
                "desired_until": desired_until.isoformat(),
            },
        )

    return GmailWatchResponse(
        google_connection_id=connection["id"],
        history_id=response.get("historyId"),
        expiration=expiration_iso,
        desired_until=desired_until.isoformat(),
        active=True,
    )


def _decode_gmail_data(data: str) -> bytes:
    padded = data + "=" * (-len(data) % 4)
    return base64.urlsafe_b64decode(padded.encode("utf-8"))


def _store_attachment_file(
    conn,
    access_token: str,
    organization_id: int,
    connection_id: int,
    message_row_id: int,
    message_id: str,
    part: dict,
) -> int:
    filename = Path(part.get("filename") or "attachment.bin").name
    attachment_id = part["body"]["attachmentId"]
    existing = conn.execute(
        sql("SELECT id FROM email_attachments WHERE email_message_id = ? AND gmail_attachment_id = ?"),
        (message_row_id, attachment_id),
    ).fetchone()
    if existing:
        return 0

    payload = gmail_get_attachment(access_token, message_id, attachment_id)
    content = _decode_gmail_data(payload["data"])
    folder = ATTACHMENTS_DIR / str(organization_id) / str(connection_id)
    folder.mkdir(parents=True, exist_ok=True)
    storage_name = f"{uuid4().hex}-{filename}"
    storage_path = folder / storage_name
    storage_path.write_bytes(content)

    conn.execute(
        sql(
            """
            INSERT INTO email_attachments (
                email_message_id,
                google_connection_id,
                gmail_attachment_id,
                filename,
                mime_type,
                size_bytes,
                storage_provider,
                storage_path,
                processing_status
            )
            VALUES (?, ?, ?, ?, ?, ?, 'local', ?, 'stored')
            """
        ),
        (
            message_row_id,
            connection_id,
            attachment_id,
            filename,
            part.get("mimeType") or "application/octet-stream",
            len(content),
            str(storage_path.relative_to(ATTACHMENTS_DIR)),
        ),
    )
    return 1


def _send_whatsapp_rule_notification(conn, connection_id: int, rule_id: int, subject: str | None, sender: str | None, snippet: str | None) -> None:
    row = conn.execute(
        sql(
            """
            SELECT gc.organization_id,
                   gc.whatsapp_number,
                   gc.display_name,
                   gc.email,
                   rc.whatsapp_notifications_enabled,
                   ar.name AS rule_name
            FROM google_connections gc
            JOIN rule_connections rc ON rc.google_connection_id = gc.id
            JOIN automation_rules ar ON ar.id = rc.rule_id
            WHERE gc.id = ?
              AND ar.id = ?
              AND gc.whatsapp_status = 'connected'
              AND gc.whatsapp_notify_new_email
              AND rc.whatsapp_notifications_enabled
            """
        ),
        (connection_id, rule_id),
    ).fetchone()
    if not row:
        return

    text = (
        f"Nuevo correo detectado.\n"
        f"Cuenta: {row['display_name'] or row['email']}\n"
        f"Correo cuenta: {row['email']}\n"
        f"Regla: {row['rule_name']}\n"
        f"Estado: correo nuevo sincronizado\n"
        f"De: {sender or 'No disponible'}\n"
        f"Asunto: {subject or 'Sin asunto'}"
    )
    if snippet:
        text += f"\nResumen: {snippet[:240]}"
    sent = send_whatsapp_text_to_number(row["whatsapp_number"], text)
    _log_event(
        conn,
        row["organization_id"],
        connection_id,
        "info",
        "whatsapp_email_notification_sent",
        "Notificacion WhatsApp enviada por regla",
        {"rule_id": rule_id, "sent": sent, "subject": subject},
    )


def _normalize_match_text(value: str | None) -> str:
    normalized = unicodedata.normalize("NFKD", value or "")
    ascii_text = "".join(char for char in normalized if not unicodedata.combining(char))
    return re.sub(r"[^a-z0-9]+", " ", ascii_text.lower()).strip()


def _significant_tokens(value: str | None) -> list[str]:
    stopwords = {"de", "del", "la", "las", "el", "los", "un", "una", "y", "o", "en", "con", "para", "por"}
    return [token for token in _normalize_match_text(value).split() if len(token) >= 3 and token not in stopwords]


def _token_matches(expected: str, actual: str) -> bool:
    if expected == actual:
        return True
    if expected in actual:
        return True
    if len(actual) >= 4 and expected.startswith(actual):
        return True
    if len(expected) >= 4 and actual.startswith(expected):
        return True
    return False


def _flexible_text_match(expected: str | None, actual: str | None) -> tuple[bool, str]:
    normalized_expected = _normalize_match_text(expected)
    normalized_actual = _normalize_match_text(actual)
    if not normalized_expected:
        return True, "empty_expected"
    if normalized_expected in normalized_actual:
        return True, "literal_normalized"

    expected_tokens = _significant_tokens(expected)
    actual_tokens = _significant_tokens(actual)
    if expected_tokens and all(any(_token_matches(expected_token, actual_token) for actual_token in actual_tokens) for expected_token in expected_tokens):
        return True, "token_fuzzy"
    return False, "no_match"


def _matched_rule_for_message(
    conn,
    organization_id: int,
    connection_id: int,
    sender: str | None,
    subject: str | None,
    recipients: str | None,
    snippet: str | None,
    has_attachments: bool,
):
    rules = conn.execute(
        sql(
            """
            SELECT ar.*
            FROM automation_rules ar
            JOIN rule_connections rc ON rc.rule_id = ar.id
            WHERE ar.organization_id = ?
              AND ar.is_active
              AND rc.google_connection_id = ?
            ORDER BY ar.created_at ASC
            """
        ),
        (organization_id, connection_id),
    ).fetchall()
    diagnostics = []

    for rule in rules:
        rule_diagnostic = {
            "rule_id": rule["id"],
            "rule_name": rule["name"],
            "action_type": rule["action_type"],
            "matched": False,
            "checks": [],
        }
        if rule["action_type"] == "ai_match":
            configuration = json.loads(rule["configuration"] or "{}")
            description = configuration.get("ai_description") or rule["name"]
            ai_matched = email_matches_ai_rule(
                description,
                {
                    "sender": sender,
                    "subject": subject,
                    "recipients": recipients,
                    "snippet": snippet,
                    "has_attachments": has_attachments,
                },
            )
            rule_diagnostic["checks"].append(
                {
                    "field": "ai_description",
                    "expected": description,
                    "actual": {
                        "sender": sender,
                        "subject": subject,
                        "snippet": snippet,
                        "has_attachments": has_attachments,
                    },
                    "passed": ai_matched,
                }
            )
            rule_diagnostic["matched"] = ai_matched
            diagnostics.append(rule_diagnostic)
            if ai_matched:
                return rule, diagnostics
            continue

        if rule["sender_contains"]:
            expected_sender = rule["sender_contains"]
            if "@" in expected_sender:
                passed = expected_sender.lower() in (sender or "").lower()
                match_type = "literal_email"
            else:
                passed, match_type = _flexible_text_match(expected_sender, sender)
            rule_diagnostic["checks"].append(
                {
                    "field": "sender_contains",
                    "expected": expected_sender,
                    "actual": sender,
                    "passed": passed,
                    "match_type": match_type,
                }
            )
            if not passed:
                diagnostics.append(rule_diagnostic)
                continue
        if rule["subject_contains"]:
            passed, match_type = _flexible_text_match(rule["subject_contains"], subject)
            rule_diagnostic["checks"].append(
                {
                    "field": "subject_contains",
                    "expected": rule["subject_contains"],
                    "actual": subject,
                    "passed": passed,
                    "match_type": match_type,
                }
            )
            if not passed:
                diagnostics.append(rule_diagnostic)
                continue
        if rule["has_attachment"] is not None:
            passed = bool(rule["has_attachment"]) == has_attachments
            rule_diagnostic["checks"].append(
                {
                    "field": "has_attachment",
                    "expected": bool(rule["has_attachment"]),
                    "actual": has_attachments,
                    "passed": passed,
                    "match_type": "boolean",
                }
            )
            if not passed:
                diagnostics.append(rule_diagnostic)
                continue
        rule_diagnostic["matched"] = True
        diagnostics.append(rule_diagnostic)
        return rule, diagnostics

    return None, diagnostics


def _ignored_message_metadata(
    message: dict,
    sender: str | None,
    subject: str | None,
    recipients: str | None,
    received_at: str | None,
    snippet: str | None,
    has_attachments: bool,
    rule_diagnostics: list[dict],
) -> dict:
    if not rule_diagnostics:
        reason = "no_active_rules_for_connection"
    elif any(rule.get("action_type") == "ai_match" for rule in rule_diagnostics):
        reason = "no_ai_rule_matched"
    else:
        reason = "no_rule_matched"

    return {
        "ignore_reason": reason,
        "gmail_message_id": message.get("id"),
        "gmail_thread_id": message.get("threadId"),
        "gmail_history_id": message.get("historyId"),
        "subject": subject,
        "sender": sender,
        "recipients": recipients,
        "received_at": received_at,
        "snippet": snippet,
        "has_attachments": has_attachments,
        "evaluated_rules": rule_diagnostics,
    }


def _store_full_message(conn, access_token: str, organization_id: int, connection_id: int, message: dict) -> tuple[int, int, str | None]:
    payload = message.get("payload") or {}
    headers = payload.get("headers") or []
    received_at = _received_at(message)
    has_attachments = _has_attachments(payload)
    sender = _header(headers, "From")
    subject = _header(headers, "Subject")
    recipients = _header(headers, "To")
    snippet = message.get("snippet")
    matched_rule, rule_diagnostics = _matched_rule_for_message(
        conn,
        organization_id,
        connection_id,
        sender,
        subject,
        recipients,
        snippet,
        has_attachments,
    )
    if not matched_rule:
        _log_event(
            conn,
            organization_id,
            connection_id,
            "info",
            "gmail_message_ignored",
            f"Correo ignorado: \"{subject or 'Sin asunto'}\" no coincide con reglas asociadas",
            _ignored_message_metadata(
                message,
                sender,
                subject,
                recipients,
                received_at,
                snippet,
                has_attachments,
                rule_diagnostics,
            ),
        )
        return 0, 0, message.get("historyId")

    message_status = "matched_rule"
    values = (
        connection_id,
        message["id"],
        message.get("threadId"),
        subject,
        sender,
        recipients,
        received_at,
        snippet,
        has_attachments,
        matched_rule["id"],
        matched_rule["name"],
        message_status,
        json.dumps(message),
    )

    if using_postgres():
        row = conn.execute(
            """
            INSERT INTO email_messages (
                google_connection_id,
                gmail_message_id,
                gmail_thread_id,
                subject,
                sender,
                recipients,
                received_at,
                snippet,
                has_attachments,
                matched_rule_id,
                matched_rule_name,
                status,
                raw_metadata
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (google_connection_id, gmail_message_id) DO UPDATE SET
                has_attachments = EXCLUDED.has_attachments,
                matched_rule_id = EXCLUDED.matched_rule_id,
                matched_rule_name = EXCLUDED.matched_rule_name,
                status = EXCLUDED.status,
                raw_metadata = EXCLUDED.raw_metadata
            RETURNING id, (xmax = 0) AS inserted
            """,
            values,
        ).fetchone()
        message_row_id = row["id"]
        stored = 1 if row["inserted"] else 0
    else:
        cursor = conn.execute(
            """
            INSERT OR IGNORE INTO email_messages (
                google_connection_id,
                gmail_message_id,
                gmail_thread_id,
                subject,
                sender,
                recipients,
                received_at,
                snippet,
                has_attachments,
                matched_rule_id,
                matched_rule_name,
                status,
                raw_metadata
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        stored = cursor.rowcount
        conn.execute(
            """
            UPDATE email_messages
            SET has_attachments = ?, matched_rule_id = ?, matched_rule_name = ?, status = ?, raw_metadata = ?
            WHERE google_connection_id = ? AND gmail_message_id = ?
            """,
            (has_attachments, matched_rule["id"], matched_rule["name"], message_status, json.dumps(message), connection_id, message["id"]),
        )
        existing_message = conn.execute(
            sql("SELECT id FROM email_messages WHERE google_connection_id = ? AND gmail_message_id = ?"),
            (connection_id, message["id"]),
        ).fetchone()
        message_row_id = existing_message["id"]

    attachments_stored = 0
    for part in _attachment_parts(payload):
        attachments_stored += _store_attachment_file(
            conn,
            access_token,
            organization_id,
            connection_id,
            message_row_id,
            message["id"],
            part,
        )

    if stored:
        _log_event(
            conn,
            organization_id,
            connection_id,
            "info",
            "gmail_message_matched",
            f"Correo sincronizado: \"{subject or 'Sin asunto'}\" coincide con la regla \"{matched_rule['name']}\"",
            {
                "gmail_message_id": message.get("id"),
                "gmail_thread_id": message.get("threadId"),
                "gmail_history_id": message.get("historyId"),
                "subject": subject,
                "sender": sender,
                "recipients": recipients,
                "received_at": received_at,
                "snippet": snippet,
                "has_attachments": has_attachments,
                "matched_rule_id": matched_rule["id"],
                "matched_rule_name": matched_rule["name"],
                "evaluated_rules": rule_diagnostics,
            },
        )
        create_followup_for_message(
            conn,
            organization_id,
            connection_id,
            matched_rule,
            message_row_id,
            message.get("threadId"),
            message["id"],
            subject,
            sender,
            received_at,
        )
        _send_whatsapp_rule_notification(conn, connection_id, matched_rule["id"], subject, sender, snippet)

    return stored, attachments_stored, message.get("historyId")


def _mark_deleted_messages(conn, organization_id: int, connection_id: int, gmail_message_ids: list[str]) -> int:
    deleted = 0
    deleted_at = datetime.now(timezone.utc).isoformat()
    for gmail_message_id in dict.fromkeys(gmail_message_ids):
        row = conn.execute(
            sql(
                """
                SELECT id, subject, sender, recipients, received_at, matched_rule_id, matched_rule_name, status
                FROM email_messages
                WHERE google_connection_id = ? AND gmail_message_id = ?
                LIMIT 1
                """
            ),
            (connection_id, gmail_message_id),
        ).fetchone()
        if not row or row["status"] == "deleted_in_gmail":
            continue

        conn.execute(
            sql(
                """
                UPDATE email_messages
                SET status = 'deleted_in_gmail'
                WHERE id = ?
                """
            ),
            (row["id"],),
        )
        _log_event(
            conn,
            organization_id,
            connection_id,
            "warning",
            "gmail_message_deleted",
            f"Correo eliminado en Gmail: \"{row['subject'] or 'Sin asunto'}\"",
            {
                "email_message_id": row["id"],
                "gmail_message_id": gmail_message_id,
                "subject": row["subject"],
                "sender": row["sender"],
                "recipients": row["recipients"],
                "received_at": str(row["received_at"]) if row["received_at"] else None,
                "deleted_at": deleted_at,
                "previous_status": row["status"],
                "matched_rule_id": row["matched_rule_id"],
                "matched_rule_name": row["matched_rule_name"],
            },
        )
        deleted += 1
    return deleted


def _sync_history_range(organization_id: int, connection_id: int, start_history_id: str) -> GmailSyncResponse:
    with db_session() as conn:
        connection = _get_connection(conn, connection_id, organization_id)
        _ensure_connection_has_rules(conn, organization_id, connection_id)

    access_token, expires_at = refresh_access_token(connection["encrypted_refresh_token"])
    history_response = gmail_get(
        access_token,
        "/users/me/history",
        {
            "startHistoryId": start_history_id,
        },
    )
    history_items = history_response.get("history") or []
    message_ids: list[str] = []
    deleted_message_ids: list[str] = []
    for history in history_items:
        for added in history.get("messagesAdded") or []:
            message = added.get("message") or {}
            if message.get("id"):
                message_ids.append(message["id"])
        for deleted in history.get("messagesDeleted") or []:
            message = deleted.get("message") or {}
            if message.get("id"):
                deleted_message_ids.append(message["id"])

    stored = 0
    attachments_stored = 0
    deleted_tracked = 0
    latest_history_id = history_response.get("historyId") or start_history_id

    with db_session() as conn:
        _get_connection(conn, connection_id, organization_id)
        conn.execute(
            sql("UPDATE google_connections SET access_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
            (expires_at if using_postgres() else expires_at.isoformat(), connection_id),
        )

        for message_id in dict.fromkeys(message_ids):
            message = gmail_get(access_token, f"/users/me/messages/{message_id}", {"format": "full"})
            added, added_attachments, history_id = _store_full_message(
                conn, access_token, organization_id, connection_id, message
            )
            stored += added
            attachments_stored += added_attachments
            latest_history_id = history_id or latest_history_id

        deleted_tracked = _mark_deleted_messages(conn, organization_id, connection_id, deleted_message_ids)

        conn.execute(
            sql("UPDATE google_connections SET gmail_history_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
            (latest_history_id, connection_id),
        )
        if message_ids or deleted_message_ids:
            _log_event(
                conn,
                organization_id,
                connection_id,
                "info",
                "gmail_history_synced",
                "Gmail reviso cambios recientes",
                {
                    "message_ids_found": len(message_ids),
                    "deleted_ids_found": len(deleted_message_ids),
                    "stored": stored,
                    "ignored": max(len(message_ids) - stored, 0),
                    "deleted_tracked": deleted_tracked,
                    "attachments_stored": attachments_stored,
                },
            )
        evaluate_pending_followups(conn, connection_id)

    return GmailSyncResponse(
        google_connection_id=connection_id,
        fetched=len(message_ids),
        stored=stored,
        attachments_stored=attachments_stored,
        latest_history_id=latest_history_id,
    )


@router.post("/connections/{connection_id}/sync", response_model=GmailSyncResponse)
def sync_connection(
    connection_id: int,
    max_results: int = Query(10, ge=1, le=25),
    user: dict = CurrentUser,
) -> GmailSyncResponse:
    require_connection_access(user, connection_id)
    with db_session() as conn:
        connection = _get_connection(conn, connection_id, user["organization_id"])
        _ensure_connection_has_rules(conn, user["organization_id"], connection_id)

    access_token, expires_at = refresh_access_token(connection["encrypted_refresh_token"])
    listed = gmail_get(access_token, "/users/me/messages", {"maxResults": max_results})
    messages = listed.get("messages", [])

    stored = 0
    attachments_stored = 0
    latest_history_id = None

    with db_session() as conn:
        _get_connection(conn, connection_id, user["organization_id"])
        conn.execute(
            sql("UPDATE google_connections SET access_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
            (expires_at if using_postgres() else expires_at.isoformat(), connection_id),
        )

        for item in messages:
            message = gmail_get(
                access_token,
                f"/users/me/messages/{item['id']}",
                {"format": "full"},
            )
            added, added_attachments, history_id = _store_full_message(
                conn, access_token, user["organization_id"], connection_id, message
            )
            stored += added
            attachments_stored += added_attachments
            latest_history_id = history_id or latest_history_id

        if latest_history_id:
            conn.execute(
                sql("UPDATE google_connections SET gmail_history_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
                (latest_history_id, connection_id),
            )
        evaluate_pending_followups(conn, connection_id)

    return GmailSyncResponse(
        google_connection_id=connection_id,
        fetched=len(messages),
        stored=stored,
        attachments_stored=attachments_stored,
        latest_history_id=latest_history_id,
    )


@router.post("/connections/{connection_id}/watch", response_model=GmailWatchResponse)
def watch_connection(
    connection_id: int,
    payload: GmailWatchRequest,
    user: dict = CurrentUser,
) -> GmailWatchResponse:
    require_owner(user)
    if not GOOGLE_PUBSUB_TOPIC:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falta GOOGLE_PUBSUB_TOPIC en backend/.env")

    desired_until = _normalize_future_datetime(payload.active_until, "active_until")

    with db_session() as conn:
        connection = _get_connection(conn, connection_id, user["organization_id"])
        if _watch_is_active(connection):
            conn.execute(
                sql(
                    """
                    UPDATE google_connections
                    SET watch_desired_until = ?, updated_at = CURRENT_TIMESTAMP
                    WHERE id = ?
                    """
                ),
                (desired_until if using_postgres() else desired_until.isoformat(), connection_id),
            )
            return GmailWatchResponse(
                google_connection_id=connection_id,
                history_id=connection["gmail_history_id"],
                expiration=str(connection["watch_expiration_at"]) if connection["watch_expiration_at"] else None,
                desired_until=desired_until.isoformat(),
                active=True,
            )

        return _register_gmail_watch(conn, connection, desired_until, manual=True)


@router.delete("/connections/{connection_id}/watch", response_model=GmailWatchResponse)
def stop_watch_connection(connection_id: int, user: dict = CurrentUser) -> GmailWatchResponse:
    require_owner(user)
    with db_session() as conn:
        connection = _get_connection(conn, connection_id, user["organization_id"])

    access_token, expires_at = refresh_access_token(connection["encrypted_refresh_token"])
    gmail_post(access_token, "/users/me/stop", {})

    with db_session() as conn:
        _get_connection(conn, connection_id, user["organization_id"])
        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET watch_expiration_at = NULL,
                    watch_desired_until = NULL,
                    access_token_expires_at = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """
            ),
            (
                expires_at if using_postgres() else expires_at.isoformat(),
                connection_id,
            ),
        )
        _log_event(
            conn,
            user["organization_id"],
            connection_id,
            "info",
            "gmail_watch_stopped",
            "Monitor Gmail inactivado manualmente",
            {},
        )

    return GmailWatchResponse(
        google_connection_id=connection_id,
        history_id=connection["gmail_history_id"],
        expiration=None,
        desired_until=None,
        active=False,
    )


@router.post("/connections/{connection_id}/history-sync", response_model=GmailSyncResponse)
def sync_connection_history(connection_id: int, user: dict = CurrentUser) -> GmailSyncResponse:
    require_owner(user)
    with db_session() as conn:
        connection = _get_connection(conn, connection_id, user["organization_id"])
        start_history_id = connection["gmail_history_id"]

    if not start_history_id:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La conexion no tiene gmail_history_id. Sincroniza o registra watch primero.")

    return _sync_history_range(user["organization_id"], connection_id, start_history_id)


@router.post("/pubsub")
def gmail_pubsub_push(payload: PubSubPushRequest) -> dict:
    message = payload.message or {}
    encoded_data = message.get("data")
    if not encoded_data:
        return {"status": "ignored", "reason": "missing data"}

    try:
        data = json.loads(_decode_gmail_data(encoded_data).decode("utf-8"))
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Payload Pub/Sub invalido") from exc

    email = data.get("emailAddress")
    history_id = data.get("historyId")
    if not email:
        return {"status": "ignored", "reason": "missing emailAddress"}

    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT * FROM google_connections WHERE email = ? ORDER BY updated_at DESC LIMIT 1"),
            (email,),
        ).fetchone()
        if not connection:
            _log_event(conn, None, None, "warning", "gmail_pubsub_unmatched", "Pub/Sub recibido para cuenta no vinculada", data)
            return {"status": "ignored", "reason": "connection not found"}

        if _connection_rule_count(conn, connection["organization_id"], connection["id"]) == 0:
            _log_event(
                conn,
                connection["organization_id"],
                connection["id"],
                "info",
                "gmail_pubsub_ignored_no_rules",
                "Pub/Sub ignorado porque la cuenta no tiene reglas activas",
                data,
            )
            return {"status": "ignored", "reason": "connection has no active rules"}

        previous_history_id = connection["gmail_history_id"]

    if previous_history_id:
        result = _sync_history_range(connection["organization_id"], connection["id"], previous_history_id)
        return {"status": "ok", "email": email, "history_id": history_id, "synced": result.model_dump()}

    with db_session() as conn:
        conn.execute(
            sql("UPDATE google_connections SET gmail_history_id = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
            (history_id, connection["id"]),
        )

    return {"status": "ok", "email": email, "history_id": history_id}


@router.get("/messages", response_model=list[EmailMessageResponse])
def list_messages(
    connection_id: int | None = Query(None),
    user: dict = CurrentUser,
) -> list[EmailMessageResponse]:
    if user.get("role") != "owner":
        connection_id = user.get("assigned_connection_id")
        if not connection_id:
            return []
    with db_session() as conn:
        if connection_id:
            rows = conn.execute(
                sql(
                    """
                    SELECT em.*, gc.email AS connection_email
                    FROM email_messages em
                    JOIN google_connections gc ON gc.id = em.google_connection_id
                    WHERE gc.organization_id = ? AND gc.id = ?
                    ORDER BY COALESCE(em.received_at, em.created_at) DESC
                    LIMIT 50
                    """
                ),
                (user["organization_id"], connection_id),
            ).fetchall()
        else:
            rows = conn.execute(
                sql(
                    """
                    SELECT em.*, gc.email AS connection_email
                    FROM email_messages em
                    JOIN google_connections gc ON gc.id = em.google_connection_id
                    WHERE gc.organization_id = ?
                    ORDER BY COALESCE(em.received_at, em.created_at) DESC
                    LIMIT 50
                    """
                ),
                (user["organization_id"],),
            ).fetchall()

    return [_serialize_message(row) for row in rows]
