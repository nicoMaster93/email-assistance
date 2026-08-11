from app.migrations.runner import add_column_if_missing
from app.db import using_postgres


def upgrade(conn):
    if using_postgres():
        add_column_if_missing(
            conn,
            "google_connections",
            "assigned_user_id",
            "assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL",
        )
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_google_connections_assigned_user
            ON google_connections (assigned_user_id)
            WHERE assigned_user_id IS NOT NULL
            """
        )
    else:
        add_column_if_missing(conn, "google_connections", "assigned_user_id", "assigned_user_id INTEGER REFERENCES users(id) ON DELETE SET NULL")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_google_connections_assigned_user
            ON google_connections (assigned_user_id)
            WHERE assigned_user_id IS NOT NULL
            """
        )
