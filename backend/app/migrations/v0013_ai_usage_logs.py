from app.db import using_postgres


def upgrade(conn):
    if using_postgres():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage_logs (
                id BIGSERIAL PRIMARY KEY,
                purpose TEXT NOT NULL,
                model TEXT,
                organization_id INTEGER REFERENCES organizations(id) ON DELETE SET NULL,
                user_id INTEGER REFERENCES users(id) ON DELETE SET NULL,
                google_connection_id INTEGER REFERENCES google_connections(id) ON DELETE SET NULL,
                automation_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                success BOOLEAN NOT NULL DEFAULT TRUE,
                error_message TEXT,
                metadata TEXT,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at ON ai_usage_logs (created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_purpose ON ai_usage_logs (purpose)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_organization_id ON ai_usage_logs (organization_id)")
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS ai_usage_logs (
                id INTEGER PRIMARY KEY AUTOINCREMENT,
                purpose TEXT NOT NULL,
                model TEXT,
                organization_id INTEGER,
                user_id INTEGER,
                google_connection_id INTEGER,
                automation_rule_id INTEGER,
                input_tokens INTEGER NOT NULL DEFAULT 0,
                output_tokens INTEGER NOT NULL DEFAULT 0,
                total_tokens INTEGER NOT NULL DEFAULT 0,
                success INTEGER NOT NULL DEFAULT 1,
                error_message TEXT,
                metadata TEXT,
                created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_created_at ON ai_usage_logs (created_at DESC)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_purpose ON ai_usage_logs (purpose)")
        conn.execute("CREATE INDEX IF NOT EXISTS idx_ai_usage_logs_organization_id ON ai_usage_logs (organization_id)")
