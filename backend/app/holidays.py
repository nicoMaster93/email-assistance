from __future__ import annotations

import json
from datetime import datetime
from urllib.error import HTTPError, URLError
from urllib.request import Request, urlopen

from app.config import NAGER_DATE_BASE_URL
from app.db import sql, using_postgres


class HolidaySyncError(RuntimeError):
    pass


def normalize_country_code(value: str | None) -> str:
    return (value or "CO").strip().upper()[:2]


def _db_date(value: str):
    return value


def _holiday_count(conn, organization_id: int, country_code: str, year: int) -> int:
    row = conn.execute(
        sql(
            """
            SELECT COUNT(*) AS total
            FROM country_holidays
            WHERE UPPER(country_code) = ?
              AND holiday_year = ?
            """
        ),
        (country_code, year),
    ).fetchone()
    return int(row["total"] or 0)


def _fetch_public_holidays(country_code: str, year: int) -> list[dict]:
    url = f"{NAGER_DATE_BASE_URL}/{country_code}/{year}"
    request = Request(url, headers={"Accept": "application/json", "User-Agent": "email-assistance/1.0"})
    try:
        with urlopen(request, timeout=8) as response:
            if response.status >= 400:
                raise HolidaySyncError(f"API de festivos respondio HTTP {response.status}")
            return json.loads(response.read().decode("utf-8"))
    except HTTPError as exc:
        raise HolidaySyncError(f"API de festivos respondio HTTP {exc.code}") from exc
    except URLError as exc:
        raise HolidaySyncError("No se pudo conectar con la API publica de festivos") from exc
    except Exception as exc:
        raise HolidaySyncError("No se pudo leer la respuesta de la API publica de festivos") from exc


def ensure_country_holidays(conn, organization_id: int, country_code: str | None, years: list[int]) -> dict:
    normalized_country = normalize_country_code(country_code)
    loaded = []
    skipped = []

    for year in sorted(set(int(item) for item in years)):
        if _holiday_count(conn, organization_id, normalized_country, year) > 0:
            skipped.append(year)
            continue

        holidays = _fetch_public_holidays(normalized_country, year)
        inserted = 0
        for holiday in holidays:
            holiday_date = holiday.get("date")
            name = holiday.get("localName") or holiday.get("name") or "Festivo"
            holiday_types = holiday.get("holidayTypes") or holiday.get("types") or []
            national = bool(holiday.get("nationalHoliday"))
            if holiday_types and "Public" not in holiday_types and not national:
                continue
            if not holiday_date:
                continue

            params = (
                normalized_country,
                year,
                _db_date(holiday_date),
                name,
                "nager.date",
            )
            if using_postgres():
                row = conn.execute(
                    """
                    INSERT INTO country_holidays (country_code, holiday_year, holiday_date, name, source)
                    VALUES (%s, %s, %s, %s, %s)
                    ON CONFLICT (country_code, holiday_date) DO NOTHING
                    RETURNING id
                    """,
                    params,
                ).fetchone()
                if row:
                    inserted += 1
            else:
                cursor = conn.execute(
                    """
                    INSERT OR IGNORE INTO country_holidays (
                        country_code, holiday_year, holiday_date, name, source
                    )
                    VALUES (?, ?, ?, ?, ?)
                    """,
                    params,
                )
                inserted += cursor.rowcount
        loaded.append({"year": year, "inserted": inserted})

    return {
        "country_code": normalized_country,
        "loaded": loaded,
        "skipped": skipped,
        "checked_at": datetime.utcnow().isoformat() + "Z",
    }
