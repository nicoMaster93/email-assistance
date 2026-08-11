from app.db import db_session, using_postgres
from app.followups import evaluate_pending_followups


def main() -> None:
    with db_session() as conn:
        result = evaluate_pending_followups(conn)
    backend = "postgres" if using_postgres() else "sqlite"
    print(f"followups evaluation done backend={backend} {result}")


if __name__ == "__main__":
    main()
