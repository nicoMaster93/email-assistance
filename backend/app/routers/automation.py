import json
import time

import httpx
from fastapi import APIRouter, HTTPException, Query, status

from app.db import db_session, insert_and_get_id, sql, using_postgres
from app.dependencies import CurrentUser, require_owner
from app.openai_client import draft_rule_from_text, generate_rule_title
from app.rule_api_dispatcher import _build_payload
from app.schemas import (
    AutomationRuleCreate,
    AutomationRuleResponse,
    AutomationRuleUpdate,
    RuleApiConnectionCreate,
    RuleApiConnectionResponse,
    RuleApiConnectionTestRequest,
    RuleApiConnectionTestResponse,
    RuleApiConnectionUpdate,
    RuleDraftFromTextRequest,
    RuleDraftResponse,
    RuleFollowupConfigUpdate,
    RuleTitleGenerateRequest,
    RuleTitleGenerateResponse,
    RuleWhatsAppNotificationsUpdate,
    SystemEventResponse,
)

router = APIRouter(prefix="/automation", tags=["automation"])

BUSINESS_EVENT_TYPES = (
    "gmail_message_matched",
    "gmail_message_ignored",
    "gmail_message_deleted",
    "whatsapp_email_notification_sent",
    "whatsapp_connected",
    "whatsapp_blocked_unknown_number",
    "followup_whatsapp_warning_sent",
    "followup_whatsapp_overdue_sent",
    "followup_whatsapp_escalation_sent",
    "followup_whatsapp_late_response_sent",
    "followup_whatsapp_response_sent",
    "followup_evaluation_failed",
    "gmail_pubsub_unmatched",
    "gmail_pubsub_ignored_no_rules",
    "rule_api_call_sent",
    "rule_api_call_failed",
)


def _normalize_event_date_filter(value: str | None, end_of_day: bool = False) -> str | None:
    if not value:
        return None
    normalized = value.strip()
    if len(normalized) == 10:
        return f"{normalized} {'23:59:59' if end_of_day else '00:00:00'}"
    return normalized.replace("T", " ")[:19]


def _serialize_rule(row) -> AutomationRuleResponse:
    connection_ids = []
    if "connection_ids" in row.keys() and row["connection_ids"]:
        connection_ids = [int(value) for value in str(row["connection_ids"]).split(",") if value]
    whatsapp_enabled_connection_ids = []
    if "whatsapp_enabled_connection_ids" in row.keys() and row["whatsapp_enabled_connection_ids"]:
        whatsapp_enabled_connection_ids = [int(value) for value in str(row["whatsapp_enabled_connection_ids"]).split(",") if value]

    return AutomationRuleResponse(
        id=row["id"],
        organization_id=row["organization_id"],
        google_connection_id=row["google_connection_id"],
        connection_ids=connection_ids,
        whatsapp_enabled_connection_ids=whatsapp_enabled_connection_ids,
        api_connection_count=int(row["api_connection_count"]) if "api_connection_count" in row.keys() and row["api_connection_count"] is not None else 0,
        name=row["name"],
        is_active=bool(row["is_active"]),
        sender_contains=row["sender_contains"],
        subject_contains=row["subject_contains"],
        has_attachment=None if row["has_attachment"] is None else bool(row["has_attachment"]),
        action_type=row["action_type"],
        configuration=json.loads(row["configuration"] or "{}"),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _serialize_event(row) -> SystemEventResponse:
    return SystemEventResponse(
        id=row["id"],
        organization_id=row["organization_id"],
        google_connection_id=row["google_connection_id"],
        level=row["level"],
        event_type=row["event_type"],
        message=row["message"],
        metadata=json.loads(row["metadata"] or "{}"),
        created_at=str(row["created_at"]),
    )


def _serialize_rule_api(row) -> RuleApiConnectionResponse:
    return RuleApiConnectionResponse(
        id=row["id"],
        organization_id=row["organization_id"],
        rule_id=row["rule_id"],
        name=row["name"],
        method=row["method"],
        url=row["url"],
        headers=json.loads(row["headers"] or "[]"),
        query_params=json.loads(row["query_params"] or "[]"),
        body_fields=json.loads(row["body_fields"] or "[]"),
        timeout_seconds=row["timeout_seconds"],
        is_active=bool(row["is_active"]),
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


def _validate_rule_api_payload(payload: RuleApiConnectionCreate | RuleApiConnectionUpdate) -> None:
    if not payload.name.strip():
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre de la API es obligatorio")
    if payload.method.upper() not in {"GET", "POST", "PUT", "PATCH", "DELETE"}:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Metodo HTTP no soportado")
    if not payload.url.startswith(("https://", "http://")):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La URL debe iniciar con http:// o https://")
    if payload.timeout_seconds < 1 or payload.timeout_seconds > 60:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El timeout debe estar entre 1 y 60 segundos")


def _sample_rule_api_source(rule_name: str) -> dict:
    return {
        "subject": "Correo de prueba de Email Assistance",
        "body_text": "Este es un mensaje de prueba para validar la configuracion de una API conectada a una regla.",
        "snippet": "Mensaje de prueba para validar API conectada",
        "sender": "remitente@example.com",
        "recipients": "cuenta@example.com",
        "received_at": "2026-08-27T10:00:00-05:00",
        "account_email": "cuenta@example.com",
        "rule_name": rule_name,
        "gmail_message_id": "gmail-message-test",
        "gmail_thread_id": "gmail-thread-test",
        "gmail_history_id": "gmail-history-test",
        "has_attachments": False,
        "attachment_count": 0,
        "attachments": [],
    }


def _rules_query() -> str:
    aggregate = "STRING_AGG(rc.google_connection_id::text, ',')" if using_postgres() else "GROUP_CONCAT(rc.google_connection_id)"
    whatsapp_aggregate = (
        "STRING_AGG(CASE WHEN rc.whatsapp_notifications_enabled THEN rc.google_connection_id::text END, ',')"
        if using_postgres()
        else "GROUP_CONCAT(CASE WHEN rc.whatsapp_notifications_enabled THEN rc.google_connection_id END)"
    )
    return f"""
        SELECT ar.*,
               {aggregate} AS connection_ids,
               {whatsapp_aggregate} AS whatsapp_enabled_connection_ids,
               MAX(COALESCE(api_counts.total, 0)) AS api_connection_count
        FROM automation_rules ar
        LEFT JOIN rule_connections rc ON rc.rule_id = ar.id
        LEFT JOIN (
            SELECT rule_id, COUNT(*) AS total
            FROM rule_api_connections
            GROUP BY rule_id
        ) api_counts ON api_counts.rule_id = ar.id
        WHERE ar.organization_id = ?
        GROUP BY ar.id
        ORDER BY ar.created_at DESC
    """


def _rule_query_by_id() -> str:
    aggregate = "STRING_AGG(rc.google_connection_id::text, ',')" if using_postgres() else "GROUP_CONCAT(rc.google_connection_id)"
    whatsapp_aggregate = (
        "STRING_AGG(CASE WHEN rc.whatsapp_notifications_enabled THEN rc.google_connection_id::text END, ',')"
        if using_postgres()
        else "GROUP_CONCAT(CASE WHEN rc.whatsapp_notifications_enabled THEN rc.google_connection_id END)"
    )
    return f"""
        SELECT ar.*,
               {aggregate} AS connection_ids,
               {whatsapp_aggregate} AS whatsapp_enabled_connection_ids,
               MAX(COALESCE(api_counts.total, 0)) AS api_connection_count
        FROM automation_rules ar
        LEFT JOIN rule_connections rc ON rc.rule_id = ar.id
        LEFT JOIN (
            SELECT rule_id, COUNT(*) AS total
            FROM rule_api_connections
            GROUP BY rule_id
        ) api_counts ON api_counts.rule_id = ar.id
        WHERE ar.id = ?
        GROUP BY ar.id
    """


@router.get("/rules", response_model=list[AutomationRuleResponse])
def list_rules(user: dict = CurrentUser) -> list[AutomationRuleResponse]:
    with db_session() as conn:
        if user.get("role") == "owner":
            rows = conn.execute(
                sql(_rules_query()),
                (user["organization_id"],),
            ).fetchall()
        elif user.get("assigned_connection_id"):
            rows = conn.execute(
                sql(
                    """
                    SELECT ar.*,
                           rc.google_connection_id AS connection_ids,
                           CASE WHEN rc.whatsapp_notifications_enabled THEN rc.google_connection_id ELSE NULL END AS whatsapp_enabled_connection_ids,
                           (
                               SELECT COUNT(*)
                               FROM rule_api_connections rac
                               WHERE rac.rule_id = ar.id
                           ) AS api_connection_count
                    FROM automation_rules ar
                    JOIN rule_connections rc ON rc.rule_id = ar.id
                    WHERE ar.organization_id = ?
                      AND rc.google_connection_id = ?
                    ORDER BY ar.created_at DESC
                    """
                ),
                (user["organization_id"], user["assigned_connection_id"]),
            ).fetchall()
        else:
            rows = []
    return [_serialize_rule(row) for row in rows]


@router.post("/rules", response_model=AutomationRuleResponse, status_code=status.HTTP_201_CREATED)
def create_rule(payload: AutomationRuleCreate, user: dict = CurrentUser) -> AutomationRuleResponse:
    require_owner(user)
    with db_session() as conn:
        for connection_id in payload.connection_ids:
            connection = conn.execute(
                sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
                (connection_id, user["organization_id"]),
            ).fetchone()
            if not connection:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        rule_id = insert_and_get_id(
            conn,
            """
            INSERT INTO automation_rules (
                organization_id,
                google_connection_id,
                name,
                sender_contains,
                subject_contains,
                has_attachment,
                action_type,
                configuration
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["organization_id"],
                None,
                payload.name,
                payload.sender_contains,
                payload.subject_contains,
                payload.has_attachment,
                payload.action_type,
                json.dumps(payload.configuration),
            ),
        )
        for connection_id in payload.connection_ids:
            if using_postgres():
                conn.execute(
                    "INSERT INTO rule_connections (rule_id, google_connection_id) VALUES (%s, %s) ON CONFLICT DO NOTHING",
                    (rule_id, connection_id),
                )
            else:
                conn.execute(
                    "INSERT OR IGNORE INTO rule_connections (rule_id, google_connection_id) VALUES (?, ?)",
                    (rule_id, connection_id),
                )
        row = conn.execute(
            sql(_rule_query_by_id()),
            (rule_id,),
        ).fetchone()

    return _serialize_rule(row)


@router.patch("/rules/{rule_id}", response_model=AutomationRuleResponse)
def update_rule(rule_id: int, payload: AutomationRuleUpdate, user: dict = CurrentUser) -> AutomationRuleResponse:
    require_owner(user)
    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT id FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

        for connection_id in payload.connection_ids:
            connection = conn.execute(
                sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
                (connection_id, user["organization_id"]),
            ).fetchone()
            if not connection:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        conn.execute(
            sql(
                """
                UPDATE automation_rules
                SET name = ?,
                    sender_contains = ?,
                    subject_contains = ?,
                    has_attachment = ?,
                    action_type = ?,
                    configuration = ?,
                    is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (
                payload.name,
                payload.sender_contains,
                payload.subject_contains,
                payload.has_attachment,
                payload.action_type,
                json.dumps(payload.configuration),
                payload.is_active if using_postgres() else int(payload.is_active),
                rule_id,
                user["organization_id"],
            ),
        )

        existing_rows = conn.execute(
            sql("SELECT google_connection_id, whatsapp_notifications_enabled FROM rule_connections WHERE rule_id = ?"),
            (rule_id,),
        ).fetchall()
        whatsapp_enabled_ids = {
            row["google_connection_id"]
            for row in existing_rows
            if bool(row["whatsapp_notifications_enabled"]) and row["google_connection_id"] in payload.connection_ids
        }

        conn.execute(sql("DELETE FROM rule_connections WHERE rule_id = ?"), (rule_id,))
        for connection_id in payload.connection_ids:
            whatsapp_enabled = connection_id in whatsapp_enabled_ids
            if using_postgres():
                conn.execute(
                    """
                    INSERT INTO rule_connections (rule_id, google_connection_id, whatsapp_notifications_enabled)
                    VALUES (%s, %s, %s)
                    ON CONFLICT (rule_id, google_connection_id) DO UPDATE
                    SET whatsapp_notifications_enabled = EXCLUDED.whatsapp_notifications_enabled
                    """,
                    (rule_id, connection_id, whatsapp_enabled),
                )
            else:
                conn.execute(
                    """
                    INSERT OR REPLACE INTO rule_connections (rule_id, google_connection_id, whatsapp_notifications_enabled)
                    VALUES (?, ?, ?)
                    """,
                    (rule_id, connection_id, int(whatsapp_enabled)),
                )

        row = conn.execute(sql(_rule_query_by_id()), (rule_id,)).fetchone()

    return _serialize_rule(row)


@router.post("/rules/draft-from-text", response_model=RuleDraftResponse)
def draft_from_text(payload: RuleDraftFromTextRequest, user: dict = CurrentUser) -> RuleDraftResponse:
    require_owner(user)
    with db_session() as conn:
        for connection_id in payload.connection_ids:
            connection = conn.execute(
                sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
                (connection_id, user["organization_id"]),
            ).fetchone()
            if not connection:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

    return RuleDraftResponse(
        **draft_rule_from_text(
            payload.text,
            payload.connection_ids,
            organization_id=user.get("organization_id"),
            user_id=user.get("id"),
        )
    )


@router.post("/rules/generate-title", response_model=RuleTitleGenerateResponse)
def generate_title(payload: RuleTitleGenerateRequest, user: dict = CurrentUser) -> RuleTitleGenerateResponse:
    require_owner(user)
    text = payload.text.strip()
    if not text:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Describe la regla para generar el titulo")
    return RuleTitleGenerateResponse(
        name=generate_rule_title(
            text,
            organization_id=user.get("organization_id"),
            user_id=user.get("id"),
        )
    )

@router.patch("/rules/{rule_id}/whatsapp-notifications", response_model=AutomationRuleResponse)
def update_rule_whatsapp_notifications(
    rule_id: int,
    payload: RuleWhatsAppNotificationsUpdate,
    user: dict = CurrentUser,
) -> AutomationRuleResponse:
    require_owner(user)
    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT id FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

        current_rows = conn.execute(
            sql("SELECT google_connection_id FROM rule_connections WHERE rule_id = ?"),
            (rule_id,),
        ).fetchall()
        current_ids = {row["google_connection_id"] for row in current_rows}
        requested_ids = set(payload.connection_ids)
        invalid_ids = requested_ids - current_ids
        if invalid_ids:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Solo puedes habilitar cuentas asociadas a la regla")

        conn.execute(
            sql("UPDATE rule_connections SET whatsapp_notifications_enabled = ? WHERE rule_id = ?"),
            (False if using_postgres() else 0, rule_id),
        )
        for connection_id in requested_ids:
            conn.execute(
                sql(
                    """
                    UPDATE rule_connections
                    SET whatsapp_notifications_enabled = ?
                    WHERE rule_id = ? AND google_connection_id = ?
                    """
                ),
                (True if using_postgres() else 1, rule_id, connection_id),
            )

        row = conn.execute(sql(_rule_query_by_id()), (rule_id,)).fetchone()

    return _serialize_rule(row)


@router.patch("/rules/{rule_id}/followup", response_model=AutomationRuleResponse)
def update_rule_followup_config(
    rule_id: int,
    payload: RuleFollowupConfigUpdate,
    user: dict = CurrentUser,
) -> AutomationRuleResponse:
    require_owner(user)
    if payload.response_time_minutes < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El tiempo maximo de respuesta debe ser mayor a cero")
    if payload.escalation_minutes is not None and payload.escalation_minutes < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El tiempo de escalamiento debe ser mayor a cero")
    if payload.warn_before_minutes is not None and payload.warn_before_minutes < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El preaviso debe ser mayor a cero")

    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT * FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

        configuration = json.loads(rule["configuration"] or "{}")
        configuration["followup"] = {
            "enabled": payload.enabled,
            "response_time_minutes": payload.response_time_minutes,
            "notify_whatsapp_on_overdue": payload.notify_whatsapp_on_overdue,
            "warn_before_minutes": payload.warn_before_minutes,
            "escalation_minutes": payload.escalation_minutes,
        }
        conn.execute(
            sql(
                """
                UPDATE automation_rules
                SET configuration = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (json.dumps(configuration), rule_id, user["organization_id"]),
        )
        row = conn.execute(sql(_rule_query_by_id()), (rule_id,)).fetchone()

    return _serialize_rule(row)


@router.get("/rules/{rule_id}/api-connections", response_model=list[RuleApiConnectionResponse])
def list_rule_api_connections(rule_id: int, user: dict = CurrentUser) -> list[RuleApiConnectionResponse]:
    require_owner(user)
    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT id FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

        rows = conn.execute(
            sql(
                """
                SELECT *
                FROM rule_api_connections
                WHERE rule_id = ? AND organization_id = ?
                ORDER BY created_at DESC
                """
            ),
            (rule_id, user["organization_id"]),
        ).fetchall()
    return [_serialize_rule_api(row) for row in rows]


@router.post("/rules/{rule_id}/api-connections/test", response_model=RuleApiConnectionTestResponse)
def test_rule_api_connection(
    rule_id: int,
    payload: RuleApiConnectionTestRequest,
    user: dict = CurrentUser,
) -> RuleApiConnectionTestResponse:
    require_owner(user)
    _validate_rule_api_payload(payload)
    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT id, name FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

    source_data = _sample_rule_api_source(rule["name"])
    headers = _build_payload(payload.headers, source_data, stringify=True)
    query_params = _build_payload(payload.query_params, source_data, stringify=True)
    body = _build_payload(payload.body_fields, source_data)
    method = payload.method.upper()
    headers = {"X-Email-Assistance-Test": "true", **headers}

    started_at = time.perf_counter()
    try:
        with httpx.Client(timeout=payload.timeout_seconds, trust_env=False) as client:
            response = client.request(
                method,
                payload.url.strip(),
                headers=headers or None,
                params=query_params or None,
                json=body if body and method not in {"GET", "DELETE"} else None,
            )
    except httpx.TimeoutException:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return RuleApiConnectionTestResponse(
            ok=False,
            method=method,
            url=payload.url.strip(),
            elapsed_ms=elapsed_ms,
            message=f"La API no respondio antes de {payload.timeout_seconds} segundos.",
        )
    except Exception as exc:
        elapsed_ms = int((time.perf_counter() - started_at) * 1000)
        return RuleApiConnectionTestResponse(
            ok=False,
            method=method,
            url=payload.url.strip(),
            elapsed_ms=elapsed_ms,
            message=f"No fue posible conectar con la API: {exc}",
        )

    elapsed_ms = int((time.perf_counter() - started_at) * 1000)
    preview = response.text[:500] if response.text else None
    ok = response.status_code < 400
    return RuleApiConnectionTestResponse(
        ok=ok,
        method=method,
        url=payload.url.strip(),
        status_code=response.status_code,
        elapsed_ms=elapsed_ms,
        message=(
            "Prueba exitosa. La API respondio correctamente."
            if ok
            else f"La API respondio con estado {response.status_code}. Revisa metodo, URL o payload."
        ),
        response_preview=preview,
    )


@router.post("/rules/{rule_id}/api-connections", response_model=RuleApiConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_rule_api_connection(
    rule_id: int,
    payload: RuleApiConnectionCreate,
    user: dict = CurrentUser,
) -> RuleApiConnectionResponse:
    require_owner(user)
    _validate_rule_api_payload(payload)
    with db_session() as conn:
        rule = conn.execute(
            sql("SELECT id FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        ).fetchone()
        if not rule:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")

        api_id = insert_and_get_id(
            conn,
            """
            INSERT INTO rule_api_connections (
                organization_id,
                rule_id,
                name,
                method,
                url,
                headers,
                query_params,
                body_fields,
                timeout_seconds,
                is_active
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                user["organization_id"],
                rule_id,
                payload.name.strip(),
                payload.method.upper(),
                payload.url.strip(),
                json.dumps(payload.headers),
                json.dumps(payload.query_params),
                json.dumps(payload.body_fields),
                payload.timeout_seconds,
                payload.is_active if using_postgres() else int(payload.is_active),
            ),
        )
        row = conn.execute(sql("SELECT * FROM rule_api_connections WHERE id = ?"), (api_id,)).fetchone()
    return _serialize_rule_api(row)


@router.patch("/api-connections/{api_connection_id}", response_model=RuleApiConnectionResponse)
def update_rule_api_connection(
    api_connection_id: int,
    payload: RuleApiConnectionUpdate,
    user: dict = CurrentUser,
) -> RuleApiConnectionResponse:
    require_owner(user)
    _validate_rule_api_payload(payload)
    with db_session() as conn:
        existing = conn.execute(
            sql("SELECT id FROM rule_api_connections WHERE id = ? AND organization_id = ?"),
            (api_connection_id, user["organization_id"]),
        ).fetchone()
        if not existing:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API no encontrada")

        conn.execute(
            sql(
                """
                UPDATE rule_api_connections
                SET name = ?,
                    method = ?,
                    url = ?,
                    headers = ?,
                    query_params = ?,
                    body_fields = ?,
                    timeout_seconds = ?,
                    is_active = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (
                payload.name.strip(),
                payload.method.upper(),
                payload.url.strip(),
                json.dumps(payload.headers),
                json.dumps(payload.query_params),
                json.dumps(payload.body_fields),
                payload.timeout_seconds,
                payload.is_active if using_postgres() else int(payload.is_active),
                api_connection_id,
                user["organization_id"],
            ),
        )
        row = conn.execute(sql("SELECT * FROM rule_api_connections WHERE id = ?"), (api_connection_id,)).fetchone()
    return _serialize_rule_api(row)


@router.delete("/api-connections/{api_connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule_api_connection(api_connection_id: int, user: dict = CurrentUser) -> None:
    require_owner(user)
    with db_session() as conn:
        cursor = conn.execute(
            sql("DELETE FROM rule_api_connections WHERE id = ? AND organization_id = ?"),
            (api_connection_id, user["organization_id"]),
        )
        if cursor.rowcount == 0:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "API no encontrada")


@router.delete("/rules/{rule_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_rule(rule_id: int, user: dict = CurrentUser) -> None:
    require_owner(user)
    with db_session() as conn:
        cursor = conn.execute(
            sql("DELETE FROM automation_rules WHERE id = ? AND organization_id = ?"),
            (rule_id, user["organization_id"]),
        )
        deleted_count = cursor.rowcount

    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Regla no encontrada")


@router.get("/events", response_model=list[SystemEventResponse])
def list_events(
    connection_id: int | None = Query(None),
    event_type: str | None = Query(None),
    date_from: str | None = Query(None),
    date_to: str | None = Query(None),
    limit: int = Query(100, ge=1, le=500),
    user: dict = CurrentUser,
) -> list[SystemEventResponse]:
    require_owner(user)
    filters = ["(organization_id = ? OR organization_id IS NULL)"]
    params: list[object] = [user["organization_id"]]

    if connection_id is not None:
        filters.append("google_connection_id = ?")
        params.append(connection_id)
    if event_type == "business":
        placeholders = ", ".join("?" for _ in BUSINESS_EVENT_TYPES)
        filters.append(f"event_type IN ({placeholders})")
        params.extend(BUSINESS_EVENT_TYPES)
    elif event_type:
        filters.append("event_type = ?")
        params.append(event_type)
    normalized_date_from = _normalize_event_date_filter(date_from)
    normalized_date_to = _normalize_event_date_filter(date_to, end_of_day=True)

    if normalized_date_from:
        filters.append("created_at >= ?")
        params.append(normalized_date_from)
    if normalized_date_to:
        filters.append("created_at <= ?")
        params.append(normalized_date_to)

    params.append(limit)
    with db_session() as conn:
        rows = conn.execute(
            sql(
                f"""
                SELECT *
                FROM system_events
                WHERE {" AND ".join(filters)}
                ORDER BY created_at DESC
                LIMIT ?
                """
            ),
            tuple(params),
        ).fetchall()
    return [_serialize_event(row) for row in rows]
