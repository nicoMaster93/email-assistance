from app.db import using_postgres


def upgrade(conn) -> None:
    if using_postgres():
        conn.execute(
            """
            CREATE TABLE IF NOT EXISTS country_holidays (
                id SERIAL PRIMARY KEY,
                country_code TEXT NOT NULL,
                holiday_year INTEGER NOT NULL,
                holiday_date DATE NOT NULL,
                name TEXT NOT NULL,
                source TEXT NOT NULL DEFAULT 'nager.date',
                created_at TIMESTAMPTZ NOT NULL DEFAULT CURRENT_TIMESTAMP,
                UNIQUE (country_code, holiday_date)
            )
            """
        )
        return

    conn.execute(
        """
        CREATE TABLE IF NOT EXISTS country_holidays (
            id INTEGER PRIMARY KEY AUTOINCREMENT,
            country_code TEXT NOT NULL,
            holiday_year INTEGER NOT NULL,
            holiday_date TEXT NOT NULL,
            name TEXT NOT NULL,
            source TEXT NOT NULL DEFAULT 'nager.date',
            created_at TEXT NOT NULL DEFAULT CURRENT_TIMESTAMP,
            UNIQUE (country_code, holiday_date)
        )
        """
    )
