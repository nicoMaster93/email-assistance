from fastapi import APIRouter, Query

from app.db import db_session, sql, using_postgres
from app.dependencies import CurrentUser, require_super_root
from app.schemas import AiUsageDashboardResponse, AiUsageDayStat, AiUsageOrgStat, AiUsagePurposeStat, AiUsageRecentItem

router = APIRouter(prefix="/ai-usage", tags=["ai-usage"])

PURPOSE_LABELS = {
    "draft_rule": "Borrador de regla",
    "generate_rule_title": "Titulo de regla",
    "email_match": "Evaluacion de correo",
    "whatsapp_assistant": "Asistente WhatsApp",
}


@router.get("/dashboard", response_model=AiUsageDashboardResponse)
def ai_usage_dashboard(
    days: int = Query(default=30, ge=1, le=365),
    user: dict = CurrentUser,
) -> AiUsageDashboardResponse:
    require_super_root(user)

    with db_session() as conn:
        if using_postgres():
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS calls,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(CASE WHEN success THEN 1 ELSE 0 END), 0) AS success_calls
                FROM ai_usage_logs
                WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
                """,
                (days,),
            ).fetchone()

            by_purpose_rows = conn.execute(
                """
                SELECT
                    purpose,
                    COUNT(*) AS calls,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM ai_usage_logs
                WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
                GROUP BY purpose
                ORDER BY total_tokens DESC, calls DESC
                """,
                (days,),
            ).fetchall()

            by_day_rows = conn.execute(
                """
                SELECT
                    TO_CHAR(DATE(created_at), 'YYYY-MM-DD') AS day,
                    COUNT(*) AS calls,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM ai_usage_logs
                WHERE created_at >= NOW() - (%s * INTERVAL '1 day')
                GROUP BY DATE(created_at)
                ORDER BY DATE(created_at) ASC
                """,
                (days,),
            ).fetchall()

            by_org_rows = conn.execute(
                """
                SELECT
                    o.id AS organization_id,
                    COALESCE(o.name, 'Sin organizacion') AS organization_name,
                    COUNT(*) AS calls,
                    COALESCE(SUM(l.total_tokens), 0) AS total_tokens
                FROM ai_usage_logs l
                LEFT JOIN organizations o ON o.id = l.organization_id
                WHERE l.created_at >= NOW() - (%s * INTERVAL '1 day')
                GROUP BY o.id, o.name
                ORDER BY total_tokens DESC, calls DESC
                LIMIT 20
                """,
                (days,),
            ).fetchall()

            recent_rows = conn.execute(
                """
                SELECT
                    l.id,
                    l.purpose,
                    l.model,
                    l.organization_id,
                    o.name AS organization_name,
                    l.input_tokens,
                    l.output_tokens,
                    l.total_tokens,
                    l.success,
                    l.error_message,
                    l.created_at::text AS created_at
                FROM ai_usage_logs l
                LEFT JOIN organizations o ON o.id = l.organization_id
                ORDER BY l.created_at DESC, l.id DESC
                LIMIT 50
                """
            ).fetchall()
        else:
            totals = conn.execute(
                """
                SELECT
                    COUNT(*) AS calls,
                    COALESCE(SUM(input_tokens), 0) AS input_tokens,
                    COALESCE(SUM(output_tokens), 0) AS output_tokens,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens,
                    COALESCE(SUM(CASE WHEN success THEN 1 ELSE 0 END), 0) AS success_calls
                FROM ai_usage_logs
                WHERE datetime(created_at) >= datetime('now', ?)
                """,
                (f"-{days} days",),
            ).fetchone()

            by_purpose_rows = conn.execute(
                """
                SELECT
                    purpose,
                    COUNT(*) AS calls,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM ai_usage_logs
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY purpose
                ORDER BY total_tokens DESC, calls DESC
                """,
                (f"-{days} days",),
            ).fetchall()

            by_day_rows = conn.execute(
                """
                SELECT
                    date(created_at) AS day,
                    COUNT(*) AS calls,
                    COALESCE(SUM(total_tokens), 0) AS total_tokens
                FROM ai_usage_logs
                WHERE datetime(created_at) >= datetime('now', ?)
                GROUP BY date(created_at)
                ORDER BY date(created_at) ASC
                """,
                (f"-{days} days",),
            ).fetchall()

            by_org_rows = conn.execute(
                """
                SELECT
                    o.id AS organization_id,
                    COALESCE(o.name, 'Sin organizacion') AS organization_name,
                    COUNT(*) AS calls,
                    COALESCE(SUM(l.total_tokens), 0) AS total_tokens
                FROM ai_usage_logs l
                LEFT JOIN organizations o ON o.id = l.organization_id
                WHERE datetime(l.created_at) >= datetime('now', ?)
                GROUP BY o.id, o.name
                ORDER BY total_tokens DESC, calls DESC
                LIMIT 20
                """,
                (f"-{days} days",),
            ).fetchall()

            recent_rows = conn.execute(
                """
                SELECT
                    l.id,
                    l.purpose,
                    l.model,
                    l.organization_id,
                    o.name AS organization_name,
                    l.input_tokens,
                    l.output_tokens,
                    l.total_tokens,
                    l.success,
                    l.error_message,
                    l.created_at
                FROM ai_usage_logs l
                LEFT JOIN organizations o ON o.id = l.organization_id
                ORDER BY l.created_at DESC, l.id DESC
                LIMIT 50
                """
            ).fetchall()

    calls = int(totals["calls"] or 0) if totals else 0
    success_calls = int(totals["success_calls"] or 0) if totals else 0
    return AiUsageDashboardResponse(
        days=days,
        calls=calls,
        input_tokens=int(totals["input_tokens"] or 0) if totals else 0,
        output_tokens=int(totals["output_tokens"] or 0) if totals else 0,
        total_tokens=int(totals["total_tokens"] or 0) if totals else 0,
        success_rate=round((success_calls / calls) * 100, 1) if calls else 100.0,
        by_purpose=[
            AiUsagePurposeStat(
                purpose=row["purpose"],
                label=PURPOSE_LABELS.get(row["purpose"], row["purpose"]),
                calls=int(row["calls"] or 0),
                total_tokens=int(row["total_tokens"] or 0),
            )
            for row in by_purpose_rows
        ],
        by_day=[
            AiUsageDayStat(
                day=str(row["day"]),
                calls=int(row["calls"] or 0),
                total_tokens=int(row["total_tokens"] or 0),
            )
            for row in by_day_rows
        ],
        by_organization=[
            AiUsageOrgStat(
                organization_id=row["organization_id"],
                organization_name=row["organization_name"] or "Sin organizacion",
                calls=int(row["calls"] or 0),
                total_tokens=int(row["total_tokens"] or 0),
            )
            for row in by_org_rows
        ],
        recent=[
            AiUsageRecentItem(
                id=int(row["id"]),
                purpose=row["purpose"],
                label=PURPOSE_LABELS.get(row["purpose"], row["purpose"]),
                model=row["model"],
                organization_id=row["organization_id"],
                organization_name=row["organization_name"],
                input_tokens=int(row["input_tokens"] or 0),
                output_tokens=int(row["output_tokens"] or 0),
                total_tokens=int(row["total_tokens"] or 0),
                success=bool(row["success"]),
                error_message=row["error_message"],
                created_at=str(row["created_at"]) if row["created_at"] else None,
            )
            for row in recent_rows
        ],
    )
