from fastapi import APIRouter, HTTPException, Query, status

from app.db import db_session, sql
from app.dependencies import CurrentUser, require_owner
from app.followups import create_manual_followup_for_email, evaluate_pending_followups
from app.schemas import EmailFollowupResponse, ManualFollowupCreate

router = APIRouter(prefix="/followups", tags=["followups"])


def _serialize(row) -> EmailFollowupResponse:
    return EmailFollowupResponse(
        id=row["id"],
        organization_id=row["organization_id"],
        google_connection_id=row["google_connection_id"],
        connection_email=row["connection_email"] if "connection_email" in row.keys() else None,
        automation_rule_id=row["automation_rule_id"],
        automation_rule_name=row["automation_rule_name"] if "automation_rule_name" in row.keys() else None,
        email_message_id=row["email_message_id"],
        gmail_thread_id=row["gmail_thread_id"],
        initial_message_id=row["initial_message_id"],
        subject=row["subject"],
        sender=row["sender"],
        received_at=str(row["received_at"]) if row["received_at"] else None,
        status=row["status"],
        response_due_at=str(row["response_due_at"]) if row["response_due_at"] else None,
        first_response_at=str(row["first_response_at"]) if row["first_response_at"] else None,
        response_time_minutes=row["response_time_minutes"],
        message_count=row["message_count"],
        last_message_at=str(row["last_message_at"]) if row["last_message_at"] else None,
        last_message_from=row["last_message_from"],
        notified_overdue_at=str(row["notified_overdue_at"]) if row["notified_overdue_at"] else None,
        escalated_at=str(row["escalated_at"]) if row["escalated_at"] else None,
        tracking_source=row["tracking_source"] if "tracking_source" in row.keys() else "rule",
        tracking_started_at=str(row["tracking_started_at"]) if "tracking_started_at" in row.keys() and row["tracking_started_at"] else None,
        warn_before_minutes=row["warn_before_minutes"] if "warn_before_minutes" in row.keys() else None,
        notify_whatsapp_on_overdue=bool(row["notify_whatsapp_on_overdue"]) if "notify_whatsapp_on_overdue" in row.keys() else False,
        escalation_minutes=row["escalation_minutes"] if "escalation_minutes" in row.keys() else None,
        warned_at=str(row["warned_at"]) if "warned_at" in row.keys() and row["warned_at"] else None,
        escalation_notified_at=str(row["escalation_notified_at"]) if "escalation_notified_at" in row.keys() and row["escalation_notified_at"] else None,
        closed_at=str(row["closed_at"]) if "closed_at" in row.keys() and row["closed_at"] else None,
        closure_reason=row["closure_reason"] if "closure_reason" in row.keys() else None,
        business_minutes_elapsed=row["business_minutes_elapsed"] if "business_minutes_elapsed" in row.keys() else None,
        business_due_at=str(row["business_due_at"]) if "business_due_at" in row.keys() and row["business_due_at"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=list[EmailFollowupResponse])
def list_followups(
    connection_id: int | None = Query(default=None),
    status_filter: str | None = Query(default=None, alias="status"),
    user: dict = CurrentUser,
) -> list[EmailFollowupResponse]:
    require_owner(user)
    filters = ["ef.organization_id = ?"]
    params: list = [user["organization_id"]]
    if connection_id:
        filters.append("ef.google_connection_id = ?")
        params.append(connection_id)
    if status_filter and status_filter != "all":
        filters.append("ef.status = ?")
        params.append(status_filter)

    where = " AND ".join(filters)
    with db_session() as conn:
        rows = conn.execute(
            sql(
                f"""
                SELECT ef.*,
                       gc.email AS connection_email,
                       ar.name AS automation_rule_name
                FROM email_followups ef
                JOIN google_connections gc ON gc.id = ef.google_connection_id
                LEFT JOIN automation_rules ar ON ar.id = ef.automation_rule_id
                WHERE {where}
                ORDER BY
                  CASE ef.status
                    WHEN 'overdue' THEN 1
                    WHEN 'pending' THEN 2
                    WHEN 'responded_late' THEN 3
                    ELSE 4
                  END,
                  ef.response_due_at ASC
                LIMIT 200
                """
            ),
            tuple(params),
        ).fetchall()
    return [_serialize(row) for row in rows]


@router.post("", response_model=EmailFollowupResponse, status_code=status.HTTP_201_CREATED)
def create_manual_followup(payload: ManualFollowupCreate, user: dict = CurrentUser) -> EmailFollowupResponse:
    require_owner(user)
    if payload.response_time_minutes < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El tiempo maximo de respuesta debe ser mayor a cero")

    with db_session() as conn:
        followup_id = create_manual_followup_for_email(
            conn,
            user["organization_id"],
            payload.email_message_id,
            payload.response_time_minutes,
            payload.notify_whatsapp_on_overdue,
            payload.warn_before_minutes,
            payload.escalation_minutes,
        )
        if not followup_id:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Correo no encontrado o sin hilo Gmail")
        row = conn.execute(
            sql(
                """
                SELECT ef.*,
                       gc.email AS connection_email,
                       ar.name AS automation_rule_name
                FROM email_followups ef
                JOIN google_connections gc ON gc.id = ef.google_connection_id
                LEFT JOIN automation_rules ar ON ar.id = ef.automation_rule_id
                WHERE ef.id = ? AND ef.organization_id = ?
                """
            ),
            (followup_id, user["organization_id"]),
        ).fetchone()
    return _serialize(row)


@router.get("/summary")
def followup_summary(user: dict = CurrentUser) -> dict:
    require_owner(user)
    with db_session() as conn:
        rows = conn.execute(
            sql(
                """
                SELECT status, COUNT(*) AS total
                FROM email_followups
                WHERE organization_id = ?
                GROUP BY status
                """
            ),
            (user["organization_id"],),
        ).fetchall()
        avg_row = conn.execute(
            sql(
                """
                SELECT AVG(response_time_minutes) AS avg_response
                FROM email_followups
                WHERE organization_id = ?
                  AND response_time_minutes IS NOT NULL
                """
            ),
            (user["organization_id"],),
        ).fetchone()
    return {
        "totals": {row["status"]: row["total"] for row in rows},
        "avg_response_minutes": int(avg_row["avg_response"]) if avg_row and avg_row["avg_response"] is not None else None,
    }


@router.post("/evaluate")
def evaluate_followups(
    connection_id: int | None = Query(default=None),
    user: dict = CurrentUser,
) -> dict:
    require_owner(user)
    with db_session() as conn:
        if connection_id:
            connection = conn.execute(
                sql("SELECT id FROM google_connections WHERE id = ? AND organization_id = ?"),
                (connection_id, user["organization_id"]),
            ).fetchone()
            if not connection:
                raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")
        result = evaluate_pending_followups(conn, connection_id, user["organization_id"])
    return {"status": "ok", **result}
