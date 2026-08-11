from __future__ import annotations

import importlib
from dataclasses import dataclass
from typing import Any, Callable

from app.db import sql, using_postgres


@dataclass(frozen=True)
class Migration:
    version: str
    module: str


MIGRATIONS = [
    Migration("0001_initial_schema", "app.migrations.v0001_initial_schema"),
    Migration("0002_followups_v2", "app.migrations.v0002_followups_v2"),
    Migration("0003_account_followup_escalation", "app.migrations.v0003_account_followup_escalation"),
    Migration("0004_whatsapp_notification_preferences", "app.migrations.v0004_whatsapp_notification_preferences"),
    Migration("0005_business_day_hours", "app.migrations.v0005_business_day_hours"),
    Migration("0006_holiday_country_cache", "app.migrations.v0006_holiday_country_cache"),
    Migration("0007_country_holidays_cache", "app.migrations.v0007_country_holidays_cache"),
    Migration("0008_account_users", "app.migrations.v0008_account_users"),
    Migration("0009_platform_roles", "app.migrations.v0009_platform_roles"),
]


def _table_exists(conn: Any, table_name: str) -> bool:
    if using_postgres():
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.tables
            WHERE table_schema = 'public' AND table_name = %s
            LIMIT 1
            """,
            (table_name,),
        ).fetchone()
    else:
        row = conn.execute(
            "SELECT 1 FROM sqlite_master WHERE type = 'table' AND name = ? LIMIT 1",
            (table_name,),
        ).fetchone()
    return bool(row)


def _ensure_migration_table(conn: Any) -> None:
    if using_postgres():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )
    else:
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS schema_migrations (
                version TEXT PRIMARY KEY,
                applied_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP
            )
            """
        )


def _applied_versions(conn: Any) -> set[str]:
    rows = conn.execute("SELECT version FROM schema_migrations").fetchall()
    return {row["version"] for row in rows}


def _mark_applied(conn: Any, version: str) -> None:
    conn.execute(sql("INSERT INTO schema_migrations (version) VALUES (?)"), (version,))


def column_exists(conn: Any, table_name: str, column_name: str) -> bool:
    if using_postgres():
        row = conn.execute(
            """
            SELECT 1
            FROM information_schema.columns
            WHERE table_schema = 'public'
              AND table_name = %s
              AND column_name = %s
            LIMIT 1
            """,
            (table_name, column_name),
        ).fetchone()
    else:
        row = next(
            (item for item in conn.execute(f"PRAGMA table_info({table_name})").fetchall() if item["name"] == column_name),
            None,
        )
    return bool(row)


def add_column_if_missing(conn: Any, table_name: str, column_name: str, ddl: str) -> None:
    if not column_exists(conn, table_name, column_name):
        conn.execute(f"ALTER TABLE {table_name} ADD COLUMN {ddl}")


def run_migrations(conn: Any) -> None:
    _ensure_migration_table(conn)
    applied = _applied_versions(conn)

    for migration in MIGRATIONS:
        if migration.version in applied:
            continue
        module = importlib.import_module(migration.module)
        upgrade: Callable[[Any], None] = module.upgrade
        upgrade(conn)
        _mark_applied(conn, migration.version)
