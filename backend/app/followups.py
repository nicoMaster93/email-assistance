import json
from dataclasses import dataclass
from datetime import date, datetime, time, timedelta, timezone
from email.utils import parseaddr
from zoneinfo import ZoneInfo

from app.db import sql, using_postgres
from app.google_client import gmail_get, refresh_access_token
from app.holidays import HolidaySyncError, ensure_country_holidays, normalize_country_code
from app.whatsapp_client import send_whatsapp_text_to_number


@dataclass
class FollowupSettings:
    enabled: bool
    response_time_minutes: int
    notify_whatsapp_on_overdue: bool
    warn_before_minutes: int | None = None
    escalation_minutes: int | None = None
    source: str = "rule"


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


def _db_datetime(value: datetime | None):
    if value is None:
        return None
    return value if using_postgres() else value.isoformat()


def _header(headers: list[dict], name: str) -> str | None:
    for header in headers:
        if header.get("name", "").lower() == name.lower():
            return header.get("value")
    return None


def _email_address(value: str | None) -> str:
    _, address = parseaddr(value or "")
    return address.lower().strip()


def _message_datetime(message: dict) -> datetime | None:
    internal_date = message.get("internalDate")
    if internal_date:
        return datetime.fromtimestamp(int(internal_date) / 1000, tz=timezone.utc)
    headers = (message.get("payload") or {}).get("headers") or []
    date_header = _header(headers, "Date")
    if not date_header:
        return None
    try:
        return _parse_datetime(date_header)
    except Exception:
        return None


def _time_from_text(value: str | None, fallback: time) -> time:
    if not value:
        return fallback
    try:
        hour, minute = str(value).split(":", 1)
        return time(int(hour), int(minute[:2]))
    except Exception:
        return fallback


def _organization_calendar(conn, organization_id: int) -> dict:
    row = conn.execute(
        sql(
            """
            SELECT business_timezone, business_days, business_start_time, business_end_time, business_day_hours, holiday_country
            FROM organizations
            WHERE id = ?
            """
        ),
        (organization_id,),
    ).fetchone()
    days = [1, 2, 3, 4, 5]
    if row and row["business_days"]:
        try:
            days = [int(day) for day in json.loads(row["business_days"])]
        except Exception:
            days = [1, 2, 3, 4, 5]
    day_hours = {}
    if row and "business_day_hours" in row.keys() and row["business_day_hours"]:
        try:
            day_hours = json.loads(row["business_day_hours"] or "{}")
        except Exception:
            day_hours = {}

    country_code = normalize_country_code(row["holiday_country"] if row else "CO")
    local_holidays = conn.execute(
        sql(
            """
            SELECT holiday_date FROM organization_holidays
            WHERE organization_id = ?
              AND UPPER(COALESCE(country_code, ?)) = ?
            """
        ),
        (
            organization_id,
            country_code,
            country_code,
        ),
    ).fetchall()
    public_holidays = conn.execute(
        sql(
            """
            SELECT holiday_date FROM country_holidays
            WHERE UPPER(country_code) = ?
            """
        ),
        (country_code,),
    ).fetchall()
    return {
        "timezone": ZoneInfo(row["business_timezone"] if row else "America/Bogota"),
        "days": set(days),
        "start": _time_from_text(row["business_start_time"] if row else None, time(8, 0)),
        "end": _time_from_text(row["business_end_time"] if row else None, time(18, 0)),
        "day_hours": day_hours,
        "holidays": {str(item["holiday_date"])[:10] for item in [*local_holidays, *public_holidays]},
    }


def _ensure_holidays_for_range(conn, organization_id: int, country_code: str, start: datetime, end: datetime) -> None:
    years = list(range(start.year, end.year + 1))
    try:
        ensure_country_holidays(conn, organization_id, country_code, years)
    except HolidaySyncError:
        return


def _is_business_minute(local_dt: datetime, calendar: dict) -> bool:
    local_date = local_dt.date().isoformat()
    day_key = str(local_dt.isoweekday())
    day_config = calendar["day_hours"].get(day_key) if isinstance(calendar.get("day_hours"), dict) else None
    if isinstance(day_config, dict):
        if not bool(day_config.get("enabled")):
            return False
        if not bool(day_config.get("uses_default", True)):
            start = _time_from_text(day_config.get("start_time"), calendar["start"])
            end = _time_from_text(day_config.get("end_time"), calendar["end"])
            return local_date not in calendar["holidays"] and start <= local_dt.time() < end

    return (
        local_dt.isoweekday() in calendar["days"]
        and local_date not in calendar["holidays"]
        and calendar["start"] <= local_dt.time() < calendar["end"]
    )


def _add_business_minutes(conn, organization_id: int, start: datetime, minutes: int) -> datetime:
    if minutes <= 0:
        return start
    row = conn.execute(sql("SELECT holiday_country FROM organizations WHERE id = ?"), (organization_id,)).fetchone()
    _ensure_holidays_for_range(
        conn,
        organization_id,
        normalize_country_code(row["holiday_country"] if row else "CO"),
        start,
        start + timedelta(days=370),
    )
    calendar = _organization_calendar(conn, organization_id)
    current = start.astimezone(calendar["timezone"])
    remaining = minutes
    guard = 0
    while remaining > 0 and guard < 600_000:
        if _is_business_minute(current, calendar):
            remaining -= 1
        current += timedelta(minutes=1)
        guard += 1
    return current.astimezone(timezone.utc)


def _business_minutes_between(conn, organization_id: int, start: datetime | None, end: datetime | None) -> int | None:
    if not start or not end or end <= start:
        return 0
    row = conn.execute(sql("SELECT holiday_country FROM organizations WHERE id = ?"), (organization_id,)).fetchone()
    _ensure_holidays_for_range(conn, organization_id, normalize_country_code(row["holiday_country"] if row else "CO"), start, end)
    calendar = _organization_calendar(conn, organization_id)
    current = start.astimezone(calendar["timezone"])
    stop = end.astimezone(calendar["timezone"])
    elapsed = 0
    guard = 0
    while current < stop and guard < 600_000:
        if _is_business_minute(current, calendar):
            elapsed += 1
        current += timedelta(minutes=1)
        guard += 1
    return elapsed


def _followup_config(rule) -> dict:
    configuration = json.loads(rule["configuration"] or "{}")
    config = configuration.get("followup") if isinstance(configuration.get("followup"), dict) else {}
    return {
        "enabled": bool(config.get("enabled")),
        "response_time_minutes": int(config.get("response_time_minutes") or 120),
        "notify_whatsapp_on_overdue": bool(config.get("notify_whatsapp_on_overdue")),
        "warn_before_minutes": config.get("warn_before_minutes"),
        "escalation_minutes": config.get("escalation_minutes"),
    }


def _settings_from_rule(rule) -> FollowupSettings:
    config = _followup_config(rule)
    return FollowupSettings(
        enabled=config["enabled"],
        response_time_minutes=config["response_time_minutes"],
        notify_whatsapp_on_overdue=config["notify_whatsapp_on_overdue"],
        warn_before_minutes=config.get("warn_before_minutes"),
        escalation_minutes=config.get("escalation_minutes"),
        source="rule",
    )


def _settings_from_connection(connection) -> FollowupSettings:
    return FollowupSettings(
        enabled=bool(connection["followup_enabled"]),
        response_time_minutes=int(connection["followup_response_time_minutes"] or 120),
        notify_whatsapp_on_overdue=bool(connection["followup_notify_whatsapp_on_overdue"]),
        warn_before_minutes=connection["followup_warn_before_minutes"] if "followup_warn_before_minutes" in connection.keys() else None,
        escalation_minutes=connection["followup_escalation_minutes"] if "followup_escalation_minutes" in connection.keys() else None,
        source="account",
    )


def _effective_settings(rule, connection) -> FollowupSettings:
    rule_settings = _settings_from_rule(rule)
    if rule_settings.enabled:
        return rule_settings
    return _settings_from_connection(connection)


def _log_event(conn, organization_id: int | None, connection_id: int | None, level: str, event_type: str, message: str, metadata: dict | None = None) -> None:
    conn.execute(
        sql(
            """
            INSERT INTO system_events (organization_id, google_connection_id, level, event_type, message, metadata)
            VALUES (?, ?, ?, ?, ?, ?)
            """
        ),
        (organization_id, connection_id, level, event_type, message, json.dumps(metadata or {}, ensure_ascii=False)),
    )


def create_followup_for_message(
    conn,
    organization_id: int,
    connection_id: int,
    rule,
    email_message_id: int,
    gmail_thread_id: str | None,
    initial_message_id: str,
    subject: str | None,
    sender: str | None,
    received_at: str | datetime | None,
) -> None:
    connection = conn.execute(
        sql("SELECT * FROM google_connections WHERE id = ? AND organization_id = ?"),
        (connection_id, organization_id),
    ).fetchone()
    if not connection:
        return

    settings = _effective_settings(rule, connection)
    if not settings.enabled or not gmail_thread_id:
        return

    received = _parse_datetime(received_at) or datetime.now(timezone.utc)
    due_at = _add_business_minutes(conn, organization_id, received, settings.response_time_minutes)

    if using_postgres():
        conn.execute(
            """
            INSERT INTO email_followups (
                organization_id, google_connection_id, automation_rule_id, email_message_id,
                gmail_thread_id, initial_message_id, subject, sender, received_at, response_due_at,
                business_due_at, last_message_at, last_message_from, tracking_source, tracking_started_at,
                warn_before_minutes, notify_whatsapp_on_overdue, escalation_minutes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email_message_id) DO NOTHING
            """,
            (
                organization_id,
                connection_id,
                rule["id"],
                email_message_id,
                gmail_thread_id,
                initial_message_id,
                subject,
                sender,
                _db_datetime(received),
                _db_datetime(due_at),
                _db_datetime(due_at),
                _db_datetime(received),
                sender,
                settings.source,
                _db_datetime(datetime.now(timezone.utc)),
                settings.warn_before_minutes,
                settings.notify_whatsapp_on_overdue,
                settings.escalation_minutes,
            ),
        )
    else:
        conn.execute(
            """
            INSERT OR IGNORE INTO email_followups (
                organization_id, google_connection_id, automation_rule_id, email_message_id,
                gmail_thread_id, initial_message_id, subject, sender, received_at, response_due_at,
                business_due_at, last_message_at, last_message_from, tracking_source, tracking_started_at,
                warn_before_minutes, notify_whatsapp_on_overdue, escalation_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            (
                organization_id,
                connection_id,
                rule["id"],
                email_message_id,
                gmail_thread_id,
                initial_message_id,
                subject,
                sender,
                _db_datetime(received),
                _db_datetime(due_at),
                _db_datetime(due_at),
                _db_datetime(received),
                sender,
                settings.source,
                _db_datetime(datetime.now(timezone.utc)),
                settings.warn_before_minutes,
                int(settings.notify_whatsapp_on_overdue),
                settings.escalation_minutes,
            ),
        )


def create_manual_followup_for_email(
    conn,
    organization_id: int,
    email_message_id: int,
    response_time_minutes: int,
    notify_whatsapp_on_overdue: bool,
    warn_before_minutes: int | None = None,
    escalation_minutes: int | None = None,
) -> int | None:
    row = conn.execute(
        sql(
            """
            SELECT em.*, gc.id AS connection_id
            FROM email_messages em
            JOIN google_connections gc ON gc.id = em.google_connection_id
            WHERE em.id = ? AND gc.organization_id = ?
            """
        ),
        (email_message_id, organization_id),
    ).fetchone()
    if not row or not row["gmail_thread_id"]:
        return None

    received = _parse_datetime(row["received_at"]) or datetime.now(timezone.utc)
    due_at = _add_business_minutes(conn, organization_id, received, response_time_minutes)
    values = (
        organization_id,
        row["connection_id"],
        row["matched_rule_id"],
        email_message_id,
        row["gmail_thread_id"],
        row["gmail_message_id"],
        row["subject"],
        row["sender"],
        _db_datetime(received),
        _db_datetime(due_at),
        _db_datetime(due_at),
        _db_datetime(received),
        row["sender"],
        "manual",
        _db_datetime(datetime.now(timezone.utc)),
        warn_before_minutes,
        notify_whatsapp_on_overdue if using_postgres() else int(notify_whatsapp_on_overdue),
        escalation_minutes,
    )
    if using_postgres():
        created = conn.execute(
            """
            INSERT INTO email_followups (
                organization_id, google_connection_id, automation_rule_id, email_message_id,
                gmail_thread_id, initial_message_id, subject, sender, received_at, response_due_at,
                business_due_at, last_message_at, last_message_from, tracking_source, tracking_started_at,
                warn_before_minutes, notify_whatsapp_on_overdue, escalation_minutes
            )
            VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s, %s)
            ON CONFLICT (email_message_id) DO UPDATE
            SET tracking_source = 'manual',
                response_due_at = EXCLUDED.response_due_at,
                business_due_at = EXCLUDED.business_due_at,
                warn_before_minutes = EXCLUDED.warn_before_minutes,
                notify_whatsapp_on_overdue = EXCLUDED.notify_whatsapp_on_overdue,
                escalation_minutes = EXCLUDED.escalation_minutes,
                updated_at = CURRENT_TIMESTAMP
            RETURNING id
            """,
            values,
        ).fetchone()
    else:
        conn.execute(
            """
            INSERT OR IGNORE INTO email_followups (
                organization_id, google_connection_id, automation_rule_id, email_message_id,
                gmail_thread_id, initial_message_id, subject, sender, received_at, response_due_at,
                business_due_at, last_message_at, last_message_from, tracking_source, tracking_started_at,
                warn_before_minutes, notify_whatsapp_on_overdue, escalation_minutes
            )
            VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?, ?)
            """,
            values,
        )
        conn.execute(
            """
            UPDATE email_followups
            SET tracking_source = 'manual',
                response_due_at = ?,
                business_due_at = ?,
                warn_before_minutes = ?,
                notify_whatsapp_on_overdue = ?,
                escalation_minutes = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE email_message_id = ?
            """,
            (_db_datetime(due_at), _db_datetime(due_at), warn_before_minutes, int(notify_whatsapp_on_overdue), escalation_minutes, email_message_id),
        )
        created = conn.execute("SELECT id FROM email_followups WHERE email_message_id = ?", (email_message_id,)).fetchone()
    return created["id"] if created else None


def _notification_enabled(connection, preference_column: str) -> bool:
    return bool(connection[preference_column]) if preference_column in connection.keys() else True


def _send_followup_whatsapp(
    conn,
    followup,
    connection,
    event_type: str,
    title: str,
    timestamp_column: str,
    preference_column: str,
    state_label: str,
) -> bool:
    if followup[timestamp_column]:
        return False
    if connection["whatsapp_status"] != "connected" or not connection["whatsapp_number"]:
        return False
    if not _notification_enabled(connection, preference_column):
        return False

    text = (
        f"{title}.\n"
        f"Cuenta: {connection['display_name'] or connection['email']}\n"
        f"Correo cuenta: {connection['email']}\n"
        f"Regla: {followup['automation_rule_name'] or 'Sin regla'}\n"
        f"Estado: {state_label}\n"
        f"Asunto: {followup['subject'] or 'Sin asunto'}\n"
        f"De: {followup['sender'] or 'No disponible'}\n"
        f"Vencia: {followup['response_due_at']}"
    )
    sent = send_whatsapp_text_to_number(connection["whatsapp_number"], text)
    now = datetime.now(timezone.utc)
    conn.execute(
        sql(f"UPDATE email_followups SET {timestamp_column} = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
        (_db_datetime(now), followup["id"]),
    )
    _log_event(
        conn,
        followup["organization_id"],
        followup["google_connection_id"],
        "info",
        event_type,
        title,
        {
            "followup_id": followup["id"],
            "sent": sent,
            "account": connection["display_name"] or connection["email"],
            "account_email": connection["email"],
            "rule": followup["automation_rule_name"],
            "state": state_label,
            "subject": followup["subject"],
        },
    )
    return sent


def _notify_overdue_if_needed(conn, followup, connection) -> bool:
    if not bool(followup["notify_whatsapp_on_overdue"]):
        return False
    return _send_followup_whatsapp(
        conn,
        followup,
        connection,
        "followup_whatsapp_overdue_sent",
        "Seguimiento vencido",
        "notified_overdue_at",
        "whatsapp_notify_followup_overdue",
        "vencido",
    )


def _notify_warning_if_needed(conn, followup, connection, now: datetime) -> bool:
    warn_before = followup["warn_before_minutes"]
    due_at = _parse_datetime(followup["response_due_at"])
    if not warn_before or not due_at or now < due_at - timedelta(minutes=int(warn_before)):
        return False
    if not bool(followup["notify_whatsapp_on_overdue"]):
        return False
    return _send_followup_whatsapp(
        conn,
        followup,
        connection,
        "followup_whatsapp_warning_sent",
        "Seguimiento proximo a vencer",
        "warned_at",
        "whatsapp_notify_followup_warning",
        "por vencer",
    )


def _notify_escalation_if_needed(conn, followup, connection, now: datetime) -> bool:
    escalation_minutes = followup["escalation_minutes"]
    due_at = _parse_datetime(followup["response_due_at"])
    if not escalation_minutes or not due_at or now < due_at + timedelta(minutes=int(escalation_minutes)):
        return False
    if not bool(followup["notify_whatsapp_on_overdue"]):
        return False
    conn.execute(
        sql("UPDATE email_followups SET status = 'escalated', escalated_at = ?, updated_at = CURRENT_TIMESTAMP WHERE id = ?"),
        (_db_datetime(now), followup["id"]),
    )
    return _send_followup_whatsapp(
        conn,
        followup,
        connection,
        "followup_whatsapp_escalation_sent",
        "Seguimiento escalado",
        "escalation_notified_at",
        "whatsapp_notify_followup_overdue",
        "escalado",
    )


def _notify_response_if_needed(conn, followup, connection, status: str, first_response_at: datetime) -> bool:
    preference_column = "whatsapp_notify_followup_late" if status == "responded_late" else "whatsapp_notify_followup_responded"
    event_type = "followup_whatsapp_late_response_sent" if status == "responded_late" else "followup_whatsapp_response_sent"
    title = "Seguimiento contestado tarde" if status == "responded_late" else "Seguimiento respondido"
    state_label = "contestado tarde" if status == "responded_late" else "respondido"
    if not bool(followup["notify_whatsapp_on_overdue"]):
        return False
    if connection["whatsapp_status"] != "connected" or not connection["whatsapp_number"]:
        return False
    if not _notification_enabled(connection, preference_column):
        return False

    text = (
        f"{title}.\n"
        f"Cuenta: {connection['display_name'] or connection['email']}\n"
        f"Correo cuenta: {connection['email']}\n"
        f"Regla: {followup['automation_rule_name'] or 'Sin regla'}\n"
        f"Estado: {state_label}\n"
        f"Asunto: {followup['subject'] or 'Sin asunto'}\n"
        f"De: {followup['sender'] or 'No disponible'}\n"
        f"Respuesta: {_db_datetime(first_response_at)}\n"
        f"Vencia: {followup['response_due_at']}"
    )
    sent = send_whatsapp_text_to_number(connection["whatsapp_number"], text)
    _log_event(
        conn,
        followup["organization_id"],
        followup["google_connection_id"],
        "info",
        event_type,
        title,
        {
            "followup_id": followup["id"],
            "sent": sent,
            "account": connection["display_name"] or connection["email"],
            "account_email": connection["email"],
            "rule": followup["automation_rule_name"],
            "state": state_label,
            "subject": followup["subject"],
        },
    )
    return sent


def evaluate_followup(conn, followup, connection) -> str:
    access_token, expires_at = refresh_access_token(connection["encrypted_refresh_token"])
    thread = gmail_get(access_token, f"/users/me/threads/{followup['gmail_thread_id']}", {"format": "metadata"})
    messages = thread.get("messages") or []
    connected_email = _email_address(connection["email"])
    received_at = _parse_datetime(followup["received_at"])

    message_count = len(messages)
    last_message_at = None
    last_message_from = None
    first_response_at = None
    first_response_from = None

    for message in messages:
        payload = message.get("payload") or {}
        headers = payload.get("headers") or []
        sender = _header(headers, "From")
        sent_at = _message_datetime(message)
        if sent_at and (last_message_at is None or sent_at > last_message_at):
            last_message_at = sent_at
            last_message_from = sender

        if not sent_at or not received_at:
            continue
        if message.get("id") == followup["initial_message_id"] or sent_at <= received_at:
            continue
        if _email_address(sender) == connected_email:
            first_response_at = sent_at
            first_response_from = sender
            break

    conn.execute(
        sql(
            """
            UPDATE google_connections
            SET access_token_expires_at = ?, updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
        ),
        (_db_datetime(expires_at), connection["id"]),
    )

    if first_response_at:
        due_at = _parse_datetime(followup["response_due_at"])
        response_minutes = _business_minutes_between(conn, followup["organization_id"], received_at, first_response_at)
        status = "responded_late" if due_at and first_response_at > due_at else "responded"
        conn.execute(
            sql(
                """
                UPDATE email_followups
                SET status = ?,
                    first_response_at = ?,
                    response_time_minutes = ?,
                    business_minutes_elapsed = ?,
                    message_count = ?,
                    last_message_at = ?,
                    last_message_from = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ?
                """
            ),
            (
                status,
                _db_datetime(first_response_at),
                response_minutes,
                response_minutes,
                message_count,
                _db_datetime(last_message_at),
                first_response_from or last_message_from,
                followup["id"],
            ),
        )
        _notify_response_if_needed(conn, followup, connection, status, first_response_at)
        return status

    now = datetime.now(timezone.utc)
    due_at = _parse_datetime(followup["response_due_at"])
    next_status = "overdue" if due_at and now > due_at else "pending"
    business_minutes = _business_minutes_between(conn, followup["organization_id"], received_at, now)

    conn.execute(
        sql(
            """
            UPDATE email_followups
            SET status = ?,
                message_count = ?,
                last_message_at = ?,
                last_message_from = ?,
                business_minutes_elapsed = ?,
                updated_at = CURRENT_TIMESTAMP
            WHERE id = ?
            """
        ),
        (next_status, message_count, _db_datetime(last_message_at), last_message_from, business_minutes, followup["id"]),
    )
    if next_status == "pending":
        _notify_warning_if_needed(conn, followup, connection, now)
    if next_status == "overdue":
        _notify_overdue_if_needed(conn, followup, connection)
        _notify_escalation_if_needed(conn, followup, connection, now)
    return next_status


def evaluate_pending_followups(conn, connection_id: int | None = None, organization_id: int | None = None) -> dict:
    params = []
    where_connection = ""
    if connection_id:
        where_connection = "AND ef.google_connection_id = ?"
        params.append(connection_id)
    where_organization = ""
    if organization_id:
        where_organization = "AND ef.organization_id = ?"
        params.append(organization_id)

    rows = conn.execute(
        sql(
            f"""
            SELECT ef.*,
                   gc.email AS email,
                   gc.email AS connection_email,
                   gc.display_name,
                   gc.encrypted_refresh_token,
                   gc.whatsapp_number,
                   gc.whatsapp_status,
                   gc.whatsapp_notifications_enabled,
                   gc.whatsapp_notify_followup_overdue,
                   gc.whatsapp_notify_followup_warning,
                   gc.whatsapp_notify_followup_late,
                   gc.whatsapp_notify_followup_responded,
                   ar.name AS automation_rule_name,
                   ar.configuration AS rule_configuration
            FROM email_followups ef
            JOIN google_connections gc ON gc.id = ef.google_connection_id
            LEFT JOIN automation_rules ar ON ar.id = ef.automation_rule_id
            WHERE ef.status IN ('pending', 'overdue')
              {where_connection}
              {where_organization}
            ORDER BY ef.response_due_at ASC
            LIMIT 100
            """
        ),
        tuple(params),
    ).fetchall()

    evaluated = 0
    responded = 0
    overdue = 0
    errors = 0
    for followup in rows:
        try:
            status = evaluate_followup(conn, followup, followup)
            evaluated += 1
            if status in {"responded", "responded_late"}:
                responded += 1
            if status == "overdue":
                overdue += 1
        except Exception as exc:
            errors += 1
            _log_event(
                conn,
                followup["organization_id"],
                followup["google_connection_id"],
                "warning",
                "followup_evaluation_failed",
                "No se pudo evaluar seguimiento",
                {"followup_id": followup["id"], "error": str(exc)},
            )

    return {"evaluated": evaluated, "responded": responded, "overdue": overdue, "errors": errors}
