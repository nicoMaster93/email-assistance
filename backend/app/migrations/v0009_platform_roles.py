from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn):
    add_column_if_missing(conn, "users", "platform_role", "platform_role TEXT NOT NULL DEFAULT 'root'")

    if using_postgres():
        conn.execute(
            """
            UPDATE users
            SET platform_role = 'account_user'
            WHERE id IN (
                SELECT assigned_user_id
                FROM google_connections
                WHERE assigned_user_id IS NOT NULL
            )
            """
        )
    else:
        conn.execute(
            """
            UPDATE users
            SET platform_role = 'account_user'
            WHERE id IN (
                SELECT assigned_user_id
                FROM google_connections
                WHERE assigned_user_id IS NOT NULL
            )
            """
        )
