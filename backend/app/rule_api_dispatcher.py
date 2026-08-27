import json
from typing import Any

import httpx

from app.db import sql


SOURCE_LABELS = {
    "subject": "Asunto",
    "body_text": "Cuerpo",
    "snippet": "Resumen",
    "sender": "Remitente",
    "recipients": "Destinatarios",
    "received_at": "Fecha de recepcion",
    "account_email": "Cuenta Gmail",
    "rule_name": "Regla",
    "gmail_message_id": "Gmail Message ID",
    "gmail_thread_id": "Gmail Thread ID",
    "gmail_history_id": "Gmail History ID",
    "has_attachments": "Tiene adjuntos",
    "attachment_count": "Cantidad de adjuntos",
    "attachments": "Adjuntos",
}


def _log_event(conn, organization_id: int, connection_id: int, level: str, event_type: str, message: str, metadata: dict) -> None:
    conn.execute(
        sql(
            """
            INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        ),
        (organization_id, connection_id, level, event_type, message, json.dumps(metadata)),
    )


def _load_mapping(value: str | None) -> list[dict]:
    try:
        parsed = json.loads(value or "[]")
    except json.JSONDecodeError:
        return []
    return parsed if isinstance(parsed, list) else []


def _resolve_mapping(mapping: dict, source_data: dict) -> Any:
    if mapping.get("source_type") == "literal":
        return mapping.get("literal", "")
    source_key = mapping.get("source_key")
    return source_data.get(source_key)


def _build_payload(mappings: list[dict], source_data: dict, stringify: bool = False) -> dict:
    payload = {}
    for mapping in mappings:
        target = str(mapping.get("target") or "").strip()
        if not target:
            continue
        value = _resolve_mapping(mapping, source_data)
        if value is None:
            value = ""
        if stringify and not isinstance(value, str):
            value = json.dumps(value, ensure_ascii=False)
        payload[target] = value
    return payload


def _attachment_metadata(conn, connection_id: int, email_message_id: int) -> list[dict]:
    rows = conn.execute(
        sql(
            """
            SELECT filename, mime_type, size_bytes, storage_provider, storage_path
            FROM email_attachments
            WHERE google_connection_id = ? AND email_message_id = ?
            ORDER BY created_at ASC
            """
        ),
        (connection_id, email_message_id),
    ).fetchall()
    return [dict(row) for row in rows]


def dispatch_rule_api_connections(
    conn,
    organization_id: int,
    connection_id: int,
    email_message_id: int,
    matched_rule: dict,
    source_data: dict,
) -> None:
    rows = conn.execute(
        sql(
            """
            SELECT *
            FROM rule_api_connections
            WHERE organization_id = ?
              AND rule_id = ?
              AND is_active = ?
            ORDER BY created_at ASC
            """
        ),
        (organization_id, matched_rule["id"], True),
    ).fetchall()
    if not rows:
        return

    attachments = _attachment_metadata(conn, connection_id, email_message_id)
    enriched_source = {
        **source_data,
        "rule_id": matched_rule["id"],
        "rule_name": matched_rule["name"],
        "attachment_count": len(attachments),
        "attachments": attachments,
    }

    for row in rows:
        headers = _build_payload(_load_mapping(row["headers"]), enriched_source, stringify=True)
        query_params = _build_payload(_load_mapping(row["query_params"]), enriched_source, stringify=True)
        body = _build_payload(_load_mapping(row["body_fields"]), enriched_source)
        method = str(row["method"]).upper()
        try:
            with httpx.Client(timeout=int(row["timeout_seconds"]), trust_env=False) as client:
                response = client.request(
                    method,
                    row["url"],
                    headers=headers or None,
                    params=query_params or None,
                    json=body if body and method not in {"GET", "DELETE"} else None,
                )
            ok = response.status_code < 400
            _log_event(
                conn,
                organization_id,
                connection_id,
                "info" if ok else "warning",
                "rule_api_call_sent" if ok else "rule_api_call_failed",
                f"API \"{row['name']}\" ejecutada para regla \"{matched_rule['name']}\"",
                {
                    "api_connection_id": row["id"],
                    "api_name": row["name"],
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "method": method,
                    "url": row["url"],
                    "status_code": response.status_code,
                    "target_fields": list(body.keys()),
                    "query_fields": list(query_params.keys()),
                    "header_fields": list(headers.keys()),
                },
            )
        except Exception as exc:
            _log_event(
                conn,
                organization_id,
                connection_id,
                "warning",
                "rule_api_call_failed",
                f"API \"{row['name']}\" fallo para regla \"{matched_rule['name']}\"",
                {
                    "api_connection_id": row["id"],
                    "api_name": row["name"],
                    "rule_id": matched_rule["id"],
                    "rule_name": matched_rule["name"],
                    "method": method,
                    "url": row["url"],
                    "error": str(exc),
                },
            )
