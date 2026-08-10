from fastapi import Depends, HTTPException, Request, status

from app.db import db_session, sql
from app.security import decode_token


def authenticated_user(request: Request) -> dict:
    auth_header = request.headers.get("Authorization", "")
    scheme, _, token = auth_header.partition(" ")
    if scheme.lower() != "bearer" or not token:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Falta Authorization Bearer token")

    payload = decode_token(token)
    with db_session() as conn:
        user = conn.execute(
            sql(
            """
            SELECT u.id, u.name, u.email
            FROM users u
            WHERE u.id = ?
            LIMIT 1
            """,
            ),
            (payload["sub"],),
        ).fetchone()

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")

    return dict(user)


def current_user(request: Request, user: dict = Depends(authenticated_user)) -> dict:
    requested_org = request.headers.get("X-Organization-Id")

    with db_session() as conn:
        if requested_org:
            membership = conn.execute(
                sql(
                    """
                    SELECT organization_id, role
                    FROM organization_members
                    WHERE user_id = ? AND organization_id = ?
                    LIMIT 1
                    """
                ),
                (user["id"], requested_org),
            ).fetchone()
        else:
            membership = conn.execute(
                sql(
                    """
                    SELECT organization_id, role
                    FROM organization_members
                    WHERE user_id = ?
                    ORDER BY created_at ASC
                    LIMIT 1
                    """
                ),
                (user["id"],),
            ).fetchone()

    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Selecciona una organizacion valida")

    return {
        **user,
        "organization_id": membership["organization_id"],
        "role": membership["role"],
    }


AuthenticatedUser = Depends(authenticated_user)
CurrentUser = Depends(current_user)
