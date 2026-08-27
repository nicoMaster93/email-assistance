from app.db import using_postgres


def upgrade(conn):
    if using_postgres():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rule_api_connections (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                rule_id INTEGER NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
                name TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'POST',
                url TEXT NOT NULL,
                headers TEXT NOT NULL DEFAULT '[]',
                query_params TEXT NOT NULL DEFAULT '[]',
                body_fields TEXT NOT NULL DEFAULT '[]',
                timeout_seconds INTEGER NOT NULL DEFAULT 15,
                is_active BOOLEAN NOT NULL DEFAULT TRUE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_rule_api_connections_rule
            ON rule_api_connections (rule_id, is_active)
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rule_api_connections (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                organization_id INTEGER NOT NULL,
                rule_id INTEGER NOT NULL,
                name TEXT NOT NULL,
                method TEXT NOT NULL DEFAULT 'POST',
                url TEXT NOT NULL,
                headers TEXT NOT NULL DEFAULT '[]',
                query_params TEXT NOT NULL DEFAULT '[]',
                body_fields TEXT NOT NULL DEFAULT '[]',
                timeout_seconds INTEGER NOT NULL DEFAULT 15,
                is_active INTEGER NOT NULL DEFAULT 1,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
                FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
                FOREIGN KEY (rule_id) REFERENCES automation_rules(id) ON DELETE CASCADE
            )
            """
        )
        conn.execute(
            """
            CREATE INDEX IF NOT EXISTS ix_rule_api_connections_rule
            ON rule_api_connections (rule_id, is_active)
            """
        )
