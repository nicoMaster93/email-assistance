from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn):
    if using_postgres():
        add_column_if_missing(conn, "users", "is_active", "is_active BOOLEAN NOT NULL DEFAULT TRUE")
        conn.execute("UPDATE users SET is_active = TRUE WHERE is_active IS NULL")
    else:
        add_column_if_missing(conn, "users", "is_active", "is_active INTEGER NOT NULL DEFAULT 1")
        conn.execute("UPDATE users SET is_active = 1 WHERE is_active IS NULL")
