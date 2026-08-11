from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn) -> None:
    if using_postgres():
        add_column_if_missing(conn, "organizations", "business_timezone", "business_timezone TEXT NOT NULL DEFAULT 'America/Bogota'")
        add_column_if_missing(conn, "organizations", "business_days", "business_days TEXT NOT NULL DEFAULT '[1,2,3,4,5]'")
        add_column_if_missing(conn, "organizations", "business_start_time", "business_start_time TEXT NOT NULL DEFAULT '08:00'")
        add_column_if_missing(conn, "organizations", "business_end_time", "business_end_time TEXT NOT NULL DEFAULT '18:00'")
        add_column_if_missing(conn, "organizations", "holiday_country", "holiday_country TEXT NOT NULL DEFAULT 'CO'")
        add_column_if_missing(conn, "google_connections", "followup_enabled", "followup_enabled BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(conn, "google_connections", "followup_response_time_minutes", "followup_response_time_minutes INTEGER NOT NULL DEFAULT 120")
        add_column_if_missing(conn, "google_connections", "followup_notify_whatsapp_on_overdue", "followup_notify_whatsapp_on_overdue BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(conn, "email_followups", "tracking_source", "tracking_source TEXT NOT NULL DEFAULT 'rule'")
        add_column_if_missing(conn, "email_followups", "tracking_started_at", "tracking_started_at TIMESTAMPTZ")
        add_column_if_missing(conn, "email_followups", "warn_before_minutes", "warn_before_minutes INTEGER")
        add_column_if_missing(conn, "email_followups", "notify_whatsapp_on_overdue", "notify_whatsapp_on_overdue BOOLEAN NOT NULL DEFAULT FALSE")
        add_column_if_missing(conn, "email_followups", "escalation_minutes", "escalation_minutes INTEGER")
        add_column_if_missing(conn, "email_followups", "warned_at", "warned_at TIMESTAMPTZ")
        add_column_if_missing(conn, "email_followups", "escalation_notified_at", "escalation_notified_at TIMESTAMPTZ")
        add_column_if_missing(conn, "email_followups", "closed_at", "closed_at TIMESTAMPTZ")
        add_column_if_missing(conn, "email_followups", "closure_reason", "closure_reason TEXT")
        add_column_if_missing(conn, "email_followups", "business_minutes_elapsed", "business_minutes_elapsed INTEGER")
        add_column_if_missing(conn, "email_followups", "business_due_at", "business_due_at TIMESTAMPTZ")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS organization_holidays (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                holiday_date DATE NOT NULL,
                name TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (organization_id, holiday_date)
            )
            """
        )
        return

    add_column_if_missing(conn, "organizations", "business_timezone", "business_timezone TEXT NOT NULL DEFAULT 'America/Bogota'")
    add_column_if_missing(conn, "organizations", "business_days", "business_days TEXT NOT NULL DEFAULT '[1,2,3,4,5]'")
    add_column_if_missing(conn, "organizations", "business_start_time", "business_start_time TEXT NOT NULL DEFAULT '08:00'")
    add_column_if_missing(conn, "organizations", "business_end_time", "business_end_time TEXT NOT NULL DEFAULT '18:00'")
    add_column_if_missing(conn, "organizations", "holiday_country", "holiday_country TEXT NOT NULL DEFAULT 'CO'")
    add_column_if_missing(conn, "google_connections", "followup_enabled", "followup_enabled INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "google_connections", "followup_response_time_minutes", "followup_response_time_minutes INTEGER NOT NULL DEFAULT 120")
    add_column_if_missing(conn, "google_connections", "followup_notify_whatsapp_on_overdue", "followup_notify_whatsapp_on_overdue INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "email_followups", "tracking_source", "tracking_source TEXT NOT NULL DEFAULT 'rule'")
    add_column_if_missing(conn, "email_followups", "tracking_started_at", "tracking_started_at TEXT")
    add_column_if_missing(conn, "email_followups", "warn_before_minutes", "warn_before_minutes INTEGER")
    add_column_if_missing(conn, "email_followups", "notify_whatsapp_on_overdue", "notify_whatsapp_on_overdue INTEGER NOT NULL DEFAULT 0")
    add_column_if_missing(conn, "email_followups", "escalation_minutes", "escalation_minutes INTEGER")
    add_column_if_missing(conn, "email_followups", "warned_at", "warned_at TEXT")
    add_column_if_missing(conn, "email_followups", "escalation_notified_at", "escalation_notified_at TEXT")
    add_column_if_missing(conn, "email_followups", "closed_at", "closed_at TEXT")
    add_column_if_missing(conn, "email_followups", "closure_reason", "closure_reason TEXT")
    add_column_if_missing(conn, "email_followups", "business_minutes_elapsed", "business_minutes_elapsed INTEGER")
    add_column_if_missing(conn, "email_followups", "business_due_at", "business_due_at TEXT")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS organization_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            holiday_date TEXT NOT NULL,
            name TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (organization_id, holiday_date),
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE
        )
        """
    )
