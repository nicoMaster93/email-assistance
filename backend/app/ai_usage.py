from __future__ import annotations

import json

from app.db import db_session, sql, using_postgres


def extract_usage_tokens(payload: dict | None) -> tuple[int, int, int]:
    usage = (payload or {}).get("usage") or {}
    input_tokens = int(usage.get("input_tokens") or usage.get("prompt_tokens") or 0)
    output_tokens = int(usage.get("output_tokens") or usage.get("completion_tokens") or 0)
    total_tokens = int(usage.get("total_tokens") or (input_tokens + output_tokens))
    return input_tokens, output_tokens, total_tokens


def log_ai_usage(
    *,
    purpose: str,
    model: str | None,
    input_tokens: int = 0,
    output_tokens: int = 0,
    total_tokens: int = 0,
    success: bool = True,
    error_message: str | None = None,
    organization_id: int | None = None,
    user_id: int | None = None,
    google_connection_id: int | None = None,
    automation_rule_id: int | None = None,
    metadata: dict | None = None,
) -> None:
    try:
        meta_value = json.dumps(metadata or {}, ensure_ascii=False)
        with db_session() as conn:
            conn.execute(
                sql(
                    """
                    INSERT INTO ai_usage_logs (
                        purpose, model, organization_id, user_id, google_connection_id, automation_rule_id,
                        input_tokens, output_tokens, total_tokens, success, error_message, metadata
                    )
                    VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
                    """
                ),
                (
                    purpose,
                    model,
                    organization_id,
                    user_id,
                    google_connection_id,
                    automation_rule_id,
                    input_tokens,
                    output_tokens,
                    total_tokens or (input_tokens + output_tokens),
                    success if using_postgres() else (1 if success else 0),
                    error_message,
                    meta_value,
                ),
            )
    except Exception:
        # Nunca interrumpir el flujo principal por fallos de telemetria.
        pass
