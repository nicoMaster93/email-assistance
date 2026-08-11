import sqlite3
from contextlib import contextmanager
from typing import Any, Iterator

import psycopg
from psycopg.rows import dict_row

from app.config import ATTACHMENTS_DIR, DATABASE_URL, DATA_DIR, DATABASE_PATH, DEMO_USER, SUPER_ROOT_USER
from app.security import hash_password


def using_postgres() -> bool:
    return bool(DATABASE_URL and DATABASE_URL.startswith(("postgresql://", "postgres://")))


def sql(statement: str) -> str:
    if using_postgres():
        return statement.replace("?", "%s")
    return statement


def row_to_dict(row: Any) -> dict:
    return dict(row)


def get_connection():
    if using_postgres():
        return psycopg.connect(DATABASE_URL, row_factory=dict_row)

    conn = sqlite3.connect(DATABASE_PATH)
    conn.row_factory = sqlite3.Row
    conn.execute("PRAGMA foreign_keys = ON")
    return conn


@contextmanager
def db_session() -> Iterator[Any]:
    conn = get_connection()
    try:
        yield conn
        conn.commit()
    finally:
        conn.close()


def init_db() -> None:
    DATA_DIR.mkdir(parents=True, exist_ok=True)
    ATTACHMENTS_DIR.mkdir(parents=True, exist_ok=True)

    with db_session() as conn:
        from app.migrations.runner import run_migrations

        run_migrations(conn)
        seed_demo_user(conn)
        seed_super_root_user(conn)


def insert_and_get_id(conn: Any, statement: str, values: tuple) -> int:
    if using_postgres():
        row = conn.execute(f"{sql(statement)} RETURNING id", values).fetchone()
        return row["id"]

    cursor = conn.execute(statement, values)
    return cursor.lastrowid


def seed_demo_user(conn: Any) -> None:
    user = conn.execute(sql("SELECT id FROM users WHERE email = ?"), (DEMO_USER["email"],)).fetchone()
    if user:
        conn.execute(sql("UPDATE users SET platform_role = 'root' WHERE id = ?"), (user["id"],))
        return

    user_id = insert_and_get_id(
        conn,
        "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'root')",
        (DEMO_USER["name"], DEMO_USER["email"], hash_password(DEMO_USER["password"])),
    )
    organization_id = insert_and_get_id(
        conn,
        "INSERT INTO organizations (name) VALUES (?)",
        (DEMO_USER["organization_name"],),
    )
    conn.execute(
        sql("INSERT INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'owner')"),
        (organization_id, user_id),
    )


def seed_super_root_user(conn: Any) -> None:
    user = conn.execute(sql("SELECT id FROM users WHERE email = ?"), (SUPER_ROOT_USER["email"],)).fetchone()
    if user:
        conn.execute(sql("UPDATE users SET platform_role = 'super_root' WHERE id = ?"), (user["id"],))
        return

    insert_and_get_id(
        conn,
        "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'super_root')",
        (SUPER_ROOT_USER["name"], SUPER_ROOT_USER["email"], hash_password(SUPER_ROOT_USER["password"])),
    )


def ensure_schema_columns(conn: Any) -> None:
    if using_postgres():
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS access_token_expires_at TIMESTAMPTZ")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS display_name TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS purpose TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS watch_desired_until TIMESTAMPTZ")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_number TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_status TEXT NOT NULL DEFAULT 'not_configured'")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_verification_token TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_contact_name TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_last_message_id TEXT")
        conn.execute("ALTER TABLE google_connections ADD COLUMN IF NOT EXISTS whatsapp_last_message_at TIMESTAMPTZ")
        conn.execute("UPDATE google_connections SET display_name = email WHERE display_name IS NULL OR display_name = ''")
        conn.execute("ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS matched_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL")
        conn.execute("ALTER TABLE email_messages ADD COLUMN IF NOT EXISTS matched_rule_name TEXT")
        conn.execute("ALTER TABLE email_attachments ADD COLUMN IF NOT EXISTS email_message_id INTEGER REFERENCES email_messages(id) ON DELETE CASCADE")
        conn.execute("ALTER TABLE email_attachments ADD COLUMN IF NOT EXISTS gmail_attachment_id TEXT")
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS uq_email_attachments_message_attachment
            ON email_attachments (email_message_id, gmail_attachment_id)
            WHERE email_message_id IS NOT NULL AND gmail_attachment_id IS NOT NULL
            """
        )
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS rule_connections (
                id SERIAL PRIMARY KEY,
                rule_id INTEGER NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
                google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
                whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (rule_id, google_connection_id)
            )
            """
        )
        conn.execute("ALTER TABLE rule_connections ADD COLUMN IF NOT EXISTS whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE")
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS email_followups (
                id SERIAL PRIMARY KEY,
                organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
                google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
                automation_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
                email_message_id INTEGER REFERENCES email_messages(id) ON DELETE CASCADE,
                gmail_thread_id TEXT NOT NULL,
                initial_message_id TEXT NOT NULL,
                subject TEXT,
                sender TEXT,
                received_at TIMESTAMPTZ,
                status TEXT NOT NULL DEFAULT 'pending',
                response_due_at TIMESTAMPTZ,
                first_response_at TIMESTAMPTZ,
                response_time_minutes INTEGER,
                message_count INTEGER NOT NULL DEFAULT 1,
                last_message_at TIMESTAMPTZ,
                last_message_from TEXT,
                notified_overdue_at TIMESTAMPTZ,
                escalated_at TIMESTAMPTZ,
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (email_message_id)
            )
            """
        )
        return

    connection_columns = {row["name"] for row in conn.execute("PRAGMA table_info(google_connections)").fetchall()}
    if "access_token_expires_at" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN access_token_expires_at TEXT")
    if "display_name" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN display_name TEXT")
    if "purpose" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN purpose TEXT")
    if "watch_desired_until" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN watch_desired_until TEXT")
    if "whatsapp_number" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_number TEXT")
    if "whatsapp_status" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_status TEXT NOT NULL DEFAULT 'not_configured'")
    if "whatsapp_verification_token" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_verification_token TEXT")
    if "whatsapp_contact_name" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_contact_name TEXT")
    if "whatsapp_last_message_id" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_last_message_id TEXT")
    if "whatsapp_last_message_at" not in connection_columns:
        conn.execute("ALTER TABLE google_connections ADD COLUMN whatsapp_last_message_at TEXT")
    conn.execute("UPDATE google_connections SET display_name = email WHERE display_name IS NULL OR display_name = ''")
    message_columns = {row["name"] for row in conn.execute("PRAGMA table_info(email_messages)").fetchall()}
    if "matched_rule_id" not in message_columns:
        conn.execute("ALTER TABLE email_messages ADD COLUMN matched_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL")
    if "matched_rule_name" not in message_columns:
        conn.execute("ALTER TABLE email_messages ADD COLUMN matched_rule_name TEXT")
    attachment_columns = {row["name"] for row in conn.execute("PRAGMA table_info(email_attachments)").fetchall()}
    if "email_message_id" not in attachment_columns:
        conn.execute("ALTER TABLE email_attachments ADD COLUMN email_message_id INTEGER REFERENCES email_messages(id) ON DELETE CASCADE")
    if "gmail_attachment_id" not in attachment_columns:
        conn.execute("ALTER TABLE email_attachments ADD COLUMN gmail_attachment_id TEXT")
    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS uq_email_attachments_message_attachment
        ON email_attachments (email_message_id, gmail_attachment_id)
        WHERE email_message_id IS NOT NULL AND gmail_attachment_id IS NOT NULL
        """
    )
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS rule_connections (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            rule_id INTEGER NOT NULL,
            google_connection_id INTEGER NOT NULL,
            whatsapp_notifications_enabled INTEGER NOT NULL DEFAULT 0,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (rule_id, google_connection_id),
            FOREIGN KEY (rule_id) REFERENCES automation_rules(id) ON DELETE CASCADE,
            FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE
        )
        """
    )
    rule_connection_columns = {row["name"] for row in conn.execute("PRAGMA table_info(rule_connections)").fetchall()}
    if "whatsapp_notifications_enabled" not in rule_connection_columns:
        conn.execute("ALTER TABLE rule_connections ADD COLUMN whatsapp_notifications_enabled INTEGER NOT NULL DEFAULT 0")
    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS email_followups (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            organization_id INTEGER NOT NULL,
            google_connection_id INTEGER NOT NULL,
            automation_rule_id INTEGER,
            email_message_id INTEGER,
            gmail_thread_id TEXT NOT NULL,
            initial_message_id TEXT NOT NULL,
            subject TEXT,
            sender TEXT,
            received_at TEXT,
            status TEXT NOT NULL DEFAULT 'pending',
            response_due_at TEXT,
            first_response_at TEXT,
            response_time_minutes INTEGER,
            message_count INTEGER NOT NULL DEFAULT 1,
            last_message_at TEXT,
            last_message_from TEXT,
            notified_overdue_at TEXT,
            escalated_at TEXT,
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (email_message_id),
            FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
            FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE,
            FOREIGN KEY (automation_rule_id) REFERENCES automation_rules(id) ON DELETE SET NULL,
            FOREIGN KEY (email_message_id) REFERENCES email_messages(id) ON DELETE CASCADE
        )
        """
    )


SQLITE_SCHEMA = """
CREATE TABLE IF NOT EXISTS users (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    email TEXT NOT NULL UNIQUE,
    password_hash TEXT NOT NULL,
    platform_role TEXT NOT NULL DEFAULT 'root',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organizations (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    name TEXT NOT NULL,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
);

CREATE TABLE IF NOT EXISTS organization_members (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    user_id INTEGER NOT NULL,
    role TEXT NOT NULL DEFAULT 'owner',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, user_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS google_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    connected_by_user_id INTEGER NOT NULL,
    google_user_id TEXT,
    display_name TEXT,
    purpose TEXT,
    email TEXT NOT NULL,
    encrypted_refresh_token TEXT,
    access_token_expires_at TEXT,
    scopes TEXT NOT NULL DEFAULT '[]',
    status TEXT NOT NULL DEFAULT 'connected',
    gmail_history_id TEXT,
    watch_expiration_at TEXT,
    watch_desired_until TEXT,
    whatsapp_number TEXT,
    whatsapp_status TEXT NOT NULL DEFAULT 'not_configured',
    whatsapp_verification_token TEXT,
    whatsapp_contact_name TEXT,
    whatsapp_last_message_id TEXT,
    whatsapp_last_message_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (organization_id, email),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (connected_by_user_id) REFERENCES users(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_messages (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    google_connection_id INTEGER NOT NULL,
    gmail_message_id TEXT NOT NULL,
    gmail_thread_id TEXT,
    subject TEXT,
    sender TEXT,
    recipients TEXT,
    received_at TEXT,
    snippet TEXT,
    body_text TEXT,
    body_html TEXT,
    has_attachments INTEGER NOT NULL DEFAULT 0,
    matched_rule_id INTEGER,
    matched_rule_name TEXT,
    status TEXT NOT NULL DEFAULT 'detected',
    raw_metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (google_connection_id, gmail_message_id),
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE,
    FOREIGN KEY (matched_rule_id) REFERENCES automation_rules(id) ON DELETE SET NULL
);

CREATE TABLE IF NOT EXISTS email_attachments (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    email_message_id INTEGER,
    google_connection_id INTEGER NOT NULL,
    gmail_attachment_id TEXT,
    filename TEXT NOT NULL,
    mime_type TEXT NOT NULL,
    size_bytes INTEGER NOT NULL,
    storage_provider TEXT NOT NULL DEFAULT 'local',
    storage_path TEXT NOT NULL,
    processing_status TEXT NOT NULL DEFAULT 'stored',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (email_message_id) REFERENCES email_messages(id) ON DELETE CASCADE,
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS automation_rules (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    google_connection_id INTEGER,
    name TEXT NOT NULL,
    is_active INTEGER NOT NULL DEFAULT 1,
    sender_contains TEXT,
    subject_contains TEXT,
    has_attachment INTEGER,
    action_type TEXT NOT NULL DEFAULT 'mark_detected',
    configuration TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS rule_connections (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    rule_id INTEGER NOT NULL,
    google_connection_id INTEGER NOT NULL,
    whatsapp_notifications_enabled INTEGER NOT NULL DEFAULT 0,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (rule_id, google_connection_id),
    FOREIGN KEY (rule_id) REFERENCES automation_rules(id) ON DELETE CASCADE,
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS system_events (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER,
    google_connection_id INTEGER,
    level TEXT NOT NULL DEFAULT 'info',
    event_type TEXT NOT NULL,
    message TEXT NOT NULL,
    metadata TEXT NOT NULL DEFAULT '{}',
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE
);

CREATE TABLE IF NOT EXISTS email_followups (
    id INTEGER PRIMARY KEY AUTOINCREMENT,
    organization_id INTEGER NOT NULL,
    google_connection_id INTEGER NOT NULL,
    automation_rule_id INTEGER,
    email_message_id INTEGER,
    gmail_thread_id TEXT NOT NULL,
    initial_message_id TEXT NOT NULL,
    subject TEXT,
    sender TEXT,
    received_at TEXT,
    status TEXT NOT NULL DEFAULT 'pending',
    response_due_at TEXT,
    first_response_at TEXT,
    response_time_minutes INTEGER,
    message_count INTEGER NOT NULL DEFAULT 1,
    last_message_at TEXT,
    last_message_from TEXT,
    notified_overdue_at TEXT,
    escalated_at TEXT,
    created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    updated_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
    UNIQUE (email_message_id),
    FOREIGN KEY (organization_id) REFERENCES organizations(id) ON DELETE CASCADE,
    FOREIGN KEY (google_connection_id) REFERENCES google_connections(id) ON DELETE CASCADE,
    FOREIGN KEY (automation_rule_id) REFERENCES automation_rules(id) ON DELETE SET NULL,
    FOREIGN KEY (email_message_id) REFERENCES email_messages(id) ON DELETE CASCADE
);
"""

POSTGRES_SCHEMA = [
    """
    CREATE TABLE IF NOT EXISTS users (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        email TEXT NOT NULL UNIQUE,
        password_hash TEXT NOT NULL,
        platform_role TEXT NOT NULL DEFAULT 'root',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS organizations (
        id SERIAL PRIMARY KEY,
        name TEXT NOT NULL,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS organization_members (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        role TEXT NOT NULL DEFAULT 'owner',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (organization_id, user_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS google_connections (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        connected_by_user_id INTEGER NOT NULL REFERENCES users(id) ON DELETE CASCADE,
        google_user_id TEXT,
        display_name TEXT,
        purpose TEXT,
        email TEXT NOT NULL,
        encrypted_refresh_token TEXT,
        access_token_expires_at TIMESTAMPTZ,
        scopes TEXT NOT NULL DEFAULT '[]',
        status TEXT NOT NULL DEFAULT 'connected',
        gmail_history_id TEXT,
        watch_expiration_at TIMESTAMPTZ,
        watch_desired_until TIMESTAMPTZ,
        whatsapp_number TEXT,
        whatsapp_status TEXT NOT NULL DEFAULT 'not_configured',
        whatsapp_verification_token TEXT,
        whatsapp_contact_name TEXT,
        whatsapp_last_message_id TEXT,
        whatsapp_last_message_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (organization_id, email)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS automation_rules (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        google_connection_id INTEGER REFERENCES google_connections(id) ON DELETE CASCADE,
        name TEXT NOT NULL,
        is_active BOOLEAN NOT NULL DEFAULT TRUE,
        sender_contains TEXT,
        subject_contains TEXT,
        has_attachment BOOLEAN,
        action_type TEXT NOT NULL DEFAULT 'mark_detected',
        configuration TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS email_messages (
        id SERIAL PRIMARY KEY,
        google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
        gmail_message_id TEXT NOT NULL,
        gmail_thread_id TEXT,
        subject TEXT,
        sender TEXT,
        recipients TEXT,
        received_at TIMESTAMPTZ,
        snippet TEXT,
        body_text TEXT,
        body_html TEXT,
        has_attachments BOOLEAN NOT NULL DEFAULT FALSE,
        matched_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
        matched_rule_name TEXT,
        status TEXT NOT NULL DEFAULT 'detected',
        raw_metadata TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (google_connection_id, gmail_message_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS email_attachments (
        id SERIAL PRIMARY KEY,
        email_message_id INTEGER REFERENCES email_messages(id) ON DELETE CASCADE,
        google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
        gmail_attachment_id TEXT,
        filename TEXT NOT NULL,
        mime_type TEXT NOT NULL,
        size_bytes INTEGER NOT NULL,
        storage_provider TEXT NOT NULL DEFAULT 'local',
        storage_path TEXT NOT NULL,
        processing_status TEXT NOT NULL DEFAULT 'stored',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS system_events (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER REFERENCES organizations(id) ON DELETE CASCADE,
        google_connection_id INTEGER REFERENCES google_connections(id) ON DELETE CASCADE,
        level TEXT NOT NULL DEFAULT 'info',
        event_type TEXT NOT NULL,
        message TEXT NOT NULL,
        metadata TEXT NOT NULL DEFAULT '{}',
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS rule_connections (
        id SERIAL PRIMARY KEY,
        rule_id INTEGER NOT NULL REFERENCES automation_rules(id) ON DELETE CASCADE,
        google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
        whatsapp_notifications_enabled BOOLEAN NOT NULL DEFAULT FALSE,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (rule_id, google_connection_id)
    )
    """,
    """
    CREATE TABLE IF NOT EXISTS email_followups (
        id SERIAL PRIMARY KEY,
        organization_id INTEGER NOT NULL REFERENCES organizations(id) ON DELETE CASCADE,
        google_connection_id INTEGER NOT NULL REFERENCES google_connections(id) ON DELETE CASCADE,
        automation_rule_id INTEGER REFERENCES automation_rules(id) ON DELETE SET NULL,
        email_message_id INTEGER REFERENCES email_messages(id) ON DELETE CASCADE,
        gmail_thread_id TEXT NOT NULL,
        initial_message_id TEXT NOT NULL,
        subject TEXT,
        sender TEXT,
        received_at TIMESTAMPTZ,
        status TEXT NOT NULL DEFAULT 'pending',
        response_due_at TIMESTAMPTZ,
        first_response_at TIMESTAMPTZ,
        response_time_minutes INTEGER,
        message_count INTEGER NOT NULL DEFAULT 1,
        last_message_at TIMESTAMPTZ,
        last_message_from TEXT,
        notified_overdue_at TIMESTAMPTZ,
        escalated_at TIMESTAMPTZ,
        created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        updated_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
        UNIQUE (email_message_id)
    )
    """,
]
