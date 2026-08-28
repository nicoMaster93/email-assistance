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
            SELECT u.id, u.name, u.email, u.platform_role, u.is_active
            FROM users u
            WHERE u.id = ?
            LIMIT 1
            """,
            ),
            (payload["sub"],),
        ).fetchone()

    if not user:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario no encontrado")
    if not bool(user["is_active"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Usuario inactivo")

    return dict(user)


def current_user(request: Request, user: dict = Depends(authenticated_user)) -> dict:
    if user.get("platform_role") == "super_root":
        return {
            **user,
            "organization_id": None,
            "role": "super_root",
            "assigned_connection_id": None,
        }

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

    if not membership and user.get("platform_role") == "root":
        return {
            **user,
            "organization_id": None,
            "role": "root",
            "assigned_connection_id": None,
        }

    if not membership:
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Selecciona una organizacion valida")

    assigned_connection_id = None
    with db_session() as conn:
        assigned = conn.execute(
            sql(
                """
                SELECT id
                FROM google_connections
                WHERE assigned_user_id = ? AND organization_id = ?
                LIMIT 1
                """
            ),
            (user["id"], membership["organization_id"]),
        ).fetchone()
        if assigned:
            assigned_connection_id = assigned["id"]

    return {
        **user,
        "organization_id": membership["organization_id"],
        "role": membership["role"],
        "assigned_connection_id": assigned_connection_id,
    }


def require_owner(user: dict) -> None:
    if user.get("role") != "owner":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para esta accion")


def require_super_root(user: dict) -> None:
    if user.get("platform_role") != "super_root" and user.get("role") != "super_root":
        raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo el super root puede realizar esta accion")


def require_connection_access(user: dict, connection_id: int) -> None:
    if user.get("role") == "owner":
        return
    if user.get("assigned_connection_id") == connection_id:
        return
    raise HTTPException(status.HTTP_403_FORBIDDEN, "Solo puedes acceder a tu cuenta asignada")


AuthenticatedUser = Depends(authenticated_user)
CurrentUser = Depends(current_user)
