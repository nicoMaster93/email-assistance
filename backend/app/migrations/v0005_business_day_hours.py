from app.migrations.runner import add_column_if_missing


def upgrade(conn) -> None:
    add_column_if_missing(conn, "organizations", "business_day_hours", "business_day_hours TEXT NOT NULL DEFAULT '{}'")
