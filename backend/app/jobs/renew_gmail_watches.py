from datetime import datetime, timedelta, timezone

from app.config import GOOGLE_PUBSUB_TOPIC
from app.db import db_session, sql, using_postgres
from app.routers.gmail import _parse_datetime, _register_gmail_watch


def main() -> None:
    if not GOOGLE_PUBSUB_TOPIC:
        print("GOOGLE_PUBSUB_TOPIC not configured; skipping watch renewal")
        return

    now = datetime.now(timezone.utc)
    renew_before = now + timedelta(days=1)

    with db_session() as conn:
        rows = conn.execute(
            sql(
                """
                SELECT *
                FROM google_connections
                WHERE watch_desired_until IS NOT NULL
                  AND encrypted_refresh_token IS NOT NULL
                """
            )
        ).fetchall()

        renewed = 0
        skipped = 0
        for connection in rows:
            desired_until = _parse_datetime(connection["watch_desired_until"])
            watch_expiration = _parse_datetime(connection["watch_expiration_at"])

            if not desired_until or desired_until <= now:
                conn.execute(
                    sql(
                        """
                        UPDATE google_connections
                        SET watch_expiration_at = NULL,
                            watch_desired_until = NULL,
                            updated_at = CURRENT_TIMESTAMP
                        WHERE id = ?
                        """
                    ),
                    (connection["id"],),
                )
                skipped += 1
                continue

            if watch_expiration and watch_expiration > renew_before:
                skipped += 1
                continue

            _register_gmail_watch(conn, connection, desired_until, manual=False)
            renewed += 1

    backend = "postgres" if using_postgres() else "sqlite"
    print(f"gmail watch renewal done backend={backend} renewed={renewed} skipped={skipped}")


if __name__ == "__main__":
    main()
