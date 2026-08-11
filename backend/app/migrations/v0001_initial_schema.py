from app.db import POSTGRES_SCHEMA, SQLITE_SCHEMA, ensure_schema_columns, using_postgres


def upgrade(conn) -> None:
    if using_postgres():
        for statement in POSTGRES_SCHEMA:
            conn.execute(statement)
    else:
        conn.executescript(SQLITE_SCHEMA)
    ensure_schema_columns(conn)
