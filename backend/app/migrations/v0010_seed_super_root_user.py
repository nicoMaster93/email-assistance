from app.db import insert_and_get_id, sql


SUPER_ROOT_EMAIL = "master@emailasistance.com"
SUPER_ROOT_NAME = "Master Email Assistance"
SUPER_ROOT_PASSWORD_HASH = "ZW1haWwtYXNzaXN0LXYxMA==.awLeNqtQL-D0T9anOZJbgR94nbL3_KHXYWZe4IFEjuU="


def upgrade(conn):
    existing = conn.execute(sql("SELECT id FROM users WHERE email = ?"), (SUPER_ROOT_EMAIL,)).fetchone()
    if existing:
        conn.execute(
            sql(
                """
                UPDATE users
                SET name = COALESCE(NULLIF(name, ''), ?),
                    platform_role = 'super_root'
                WHERE id = ?
                """
            ),
            (SUPER_ROOT_NAME, existing["id"]),
        )
        return

    insert_and_get_id(
        conn,
        "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'super_root')",
        (SUPER_ROOT_NAME, SUPER_ROOT_EMAIL, SUPER_ROOT_PASSWORD_HASH),
    )
