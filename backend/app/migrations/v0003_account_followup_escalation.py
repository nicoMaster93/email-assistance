from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn) -> None:
    if using_postgres():
        add_column_if_missing(conn, "google_connections", "followup_warn_before_minutes", "followup_warn_before_minutes INTEGER")
        add_column_if_missing(conn, "google_connections", "followup_escalation_minutes", "followup_escalation_minutes INTEGER")
        return

    add_column_if_missing(conn, "google_connections", "followup_warn_before_minutes", "followup_warn_before_minutes INTEGER")
    add_column_if_missing(conn, "google_connections", "followup_escalation_minutes", "followup_escalation_minutes INTEGER")
