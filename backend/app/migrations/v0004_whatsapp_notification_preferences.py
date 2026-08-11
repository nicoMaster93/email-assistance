from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn) -> None:
    boolean_type = "BOOLEAN" if using_postgres() else "INTEGER"
    default_true = "TRUE" if using_postgres() else "1"

    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notifications_enabled",
        f"whatsapp_notifications_enabled {boolean_type} NOT NULL DEFAULT {default_true}",
    )
    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notify_new_email",
        f"whatsapp_notify_new_email {boolean_type} NOT NULL DEFAULT {default_true}",
    )
    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notify_followup_overdue",
        f"whatsapp_notify_followup_overdue {boolean_type} NOT NULL DEFAULT {default_true}",
    )
    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notify_followup_warning",
        f"whatsapp_notify_followup_warning {boolean_type} NOT NULL DEFAULT {default_true}",
    )
    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notify_followup_late",
        f"whatsapp_notify_followup_late {boolean_type} NOT NULL DEFAULT {default_true}",
    )
    add_column_if_missing(
        conn,
        "google_connections",
        "whatsapp_notify_followup_responded",
        f"whatsapp_notify_followup_responded {boolean_type} NOT NULL DEFAULT {default_true}",
    )
