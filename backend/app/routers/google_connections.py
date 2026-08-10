import json

from fastapi import APIRouter, HTTPException, status

from app.db import db_session, insert_and_get_id, sql
from app.dependencies import CurrentUser
from app.schemas import GoogleConnectionResponse, LinkGoogleAccountRequest, UpdateGoogleConnectionRequest
from app.security import encrypt_secret

router = APIRouter(prefix="/google-connections", tags=["google connections"])


def _token_placeholder(refresh_token: str | None) -> str | None:
    return encrypt_secret(refresh_token)


def _serialize(row) -> GoogleConnectionResponse:
    return GoogleConnectionResponse(
        id=row["id"],
        display_name=row["display_name"],
        purpose=row["purpose"],
        email=row["email"],
        google_user_id=row["google_user_id"],
        scopes=json.loads(row["scopes"]),
        status=row["status"],
        watch_expiration_at=str(row["watch_expiration_at"]) if row["watch_expiration_at"] else None,
        watch_desired_until=str(row["watch_desired_until"]) if row["watch_desired_until"] else None,
        whatsapp_number=row["whatsapp_number"],
        whatsapp_status=row["whatsapp_status"],
        whatsapp_contact_name=row["whatsapp_contact_name"],
        whatsapp_last_message_id=row["whatsapp_last_message_id"],
        whatsapp_last_message_at=str(row["whatsapp_last_message_at"]) if row["whatsapp_last_message_at"] else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=list[GoogleConnectionResponse])
def list_connections(user: dict = CurrentUser) -> list[GoogleConnectionResponse]:
    with db_session() as conn:
        rows = conn.execute(
            sql(
            """
            SELECT *
            FROM google_connections
            WHERE organization_id = ?
            ORDER BY created_at DESC
            """,
            ),
            (user["organization_id"],),
        ).fetchall()
    return [_serialize(row) for row in rows]


@router.post("", response_model=GoogleConnectionResponse, status_code=status.HTTP_201_CREATED)
def link_connection(payload: LinkGoogleAccountRequest, user: dict = CurrentUser) -> GoogleConnectionResponse:
    with db_session() as conn:
        try:
            connection_id = insert_and_get_id(
                conn,
                """
                INSERT INTO google_connections (
                    organization_id,
                    connected_by_user_id,
                    google_user_id,
                    display_name,
                    purpose,
                    email,
                    encrypted_refresh_token,
                    scopes
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?)
                """,
                (
                    user["organization_id"],
                    user["id"],
                    payload.google_user_id,
                    payload.display_name or str(payload.email),
                    payload.purpose,
                    payload.email,
                    _token_placeholder(payload.refresh_token),
                    json.dumps(payload.scopes),
                ),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise HTTPException(status.HTTP_409_CONFLICT, "Esa cuenta ya esta vinculada") from exc
            raise

        row = conn.execute(sql("SELECT * FROM google_connections WHERE id = ?"), (connection_id,)).fetchone()

    return _serialize(row)


@router.patch("/{connection_id}", response_model=GoogleConnectionResponse)
def update_connection(
    connection_id: int,
    payload: UpdateGoogleConnectionRequest,
    user: dict = CurrentUser,
) -> GoogleConnectionResponse:
    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT * FROM google_connections WHERE id = ? AND organization_id = ?"),
            (connection_id, user["organization_id"]),
        ).fetchone()
        if not connection:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        display_name = payload.display_name if payload.display_name is not None else connection["display_name"]
        purpose = payload.purpose if payload.purpose is not None else connection["purpose"]
        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET display_name = ?, purpose = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (display_name, purpose, connection_id, user["organization_id"]),
        )
        row = conn.execute(sql("SELECT * FROM google_connections WHERE id = ?"), (connection_id,)).fetchone()

    return _serialize(row)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_connection(connection_id: int, user: dict = CurrentUser) -> None:
    with db_session() as conn:
        cursor = conn.execute(
            sql(
            """
            DELETE FROM google_connections
            WHERE id = ? AND organization_id = ?
            """,
            ),
            (connection_id, user["organization_id"]),
        )
        deleted_count = cursor.rowcount

    if deleted_count == 0:
        raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")
