from app.db import using_postgres
from app.migrations.runner import add_column_if_missing


def upgrade(conn) -> None:
    add_column_if_missing(conn, "organization_holidays", "country_code", "country_code TEXT")
    add_column_if_missing(conn, "organization_holidays", "holiday_year", "holiday_year INTEGER")
    add_column_if_missing(conn, "organization_holidays", "source", "source TEXT")

    conn.execute("UPDATE organization_holidays SET country_code = 'CO' WHERE country_code IS NULL")
    conn.execute(
        "UPDATE organization_holidays SET holiday_year = CAST(SUBSTR(CAST(holiday_date AS TEXT), 1, 4) AS INTEGER) WHERE holiday_year IS NULL"
    )
    conn.execute("UPDATE organization_holidays SET source = 'local' WHERE source IS NULL")

    if using_postgres():
        conn.execute(
            """
            CREATE UNIQUE INDEX IF NOT EXISTS idx_organization_holidays_org_country_date
            ON organization_holidays (organization_id, country_code, holiday_date)
            """
        )
        return

    conn.execute(
        """
        CREATE UNIQUE INDEX IF NOT EXISTS idx_organization_holidays_org_country_date
        ON organization_holidays (organization_id, country_code, holiday_date)
        """
    )
