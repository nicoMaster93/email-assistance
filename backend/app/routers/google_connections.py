import json

from fastapi import APIRouter, HTTPException, status

from app.db import db_session, insert_and_get_id, sql
from app.dependencies import CurrentUser, require_owner
from app.schemas import AccountFollowupConfigUpdate, CreateAccountAccessRequest, GoogleConnectionResponse, LinkGoogleAccountRequest, UpdateGoogleConnectionRequest
from app.security import encrypt_secret, hash_password

router = APIRouter(prefix="/google-connections", tags=["google connections"])


def _token_placeholder(refresh_token: str | None) -> str | None:
    return encrypt_secret(refresh_token)


def _serialize(row) -> GoogleConnectionResponse:
    return GoogleConnectionResponse(
        id=row["id"],
        assigned_user_id=row["assigned_user_id"] if "assigned_user_id" in row.keys() else None,
        assigned_user_email=row["assigned_user_email"] if "assigned_user_email" in row.keys() else None,
        assigned_user_name=row["assigned_user_name"] if "assigned_user_name" in row.keys() else None,
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
        whatsapp_notifications_enabled=bool(row["whatsapp_notifications_enabled"]) if "whatsapp_notifications_enabled" in row.keys() else True,
        whatsapp_notify_new_email=bool(row["whatsapp_notify_new_email"]) if "whatsapp_notify_new_email" in row.keys() else True,
        whatsapp_notify_followup_overdue=bool(row["whatsapp_notify_followup_overdue"]) if "whatsapp_notify_followup_overdue" in row.keys() else True,
        whatsapp_notify_followup_warning=bool(row["whatsapp_notify_followup_warning"]) if "whatsapp_notify_followup_warning" in row.keys() else True,
        whatsapp_notify_followup_late=bool(row["whatsapp_notify_followup_late"]) if "whatsapp_notify_followup_late" in row.keys() else True,
        whatsapp_notify_followup_responded=bool(row["whatsapp_notify_followup_responded"]) if "whatsapp_notify_followup_responded" in row.keys() else True,
        followup_enabled=bool(row["followup_enabled"]),
        followup_response_time_minutes=row["followup_response_time_minutes"],
        followup_notify_whatsapp_on_overdue=bool(row["followup_notify_whatsapp_on_overdue"]),
        followup_warn_before_minutes=row["followup_warn_before_minutes"] if "followup_warn_before_minutes" in row.keys() else None,
        followup_escalation_minutes=row["followup_escalation_minutes"] if "followup_escalation_minutes" in row.keys() else None,
        created_at=str(row["created_at"]),
        updated_at=str(row["updated_at"]),
    )


@router.get("", response_model=list[GoogleConnectionResponse])
def list_connections(user: dict = CurrentUser) -> list[GoogleConnectionResponse]:
    with db_session() as conn:
        filters = ["gc.organization_id = ?"]
        params: list[object] = [user["organization_id"]]
        if user.get("role") != "owner":
            filters.append("gc.assigned_user_id = ?")
            params.append(user["id"])
        rows = conn.execute(
            sql(
            f"""
            SELECT gc.*, u.email AS assigned_user_email, u.name AS assigned_user_name
            FROM google_connections gc
            LEFT JOIN users u ON u.id = gc.assigned_user_id
            WHERE {" AND ".join(filters)}
            ORDER BY gc.created_at DESC
            """,
            ),
            tuple(params),
        ).fetchall()
    return [_serialize(row) for row in rows]


@router.post("", response_model=GoogleConnectionResponse, status_code=status.HTTP_201_CREATED)
def link_connection(payload: LinkGoogleAccountRequest, user: dict = CurrentUser) -> GoogleConnectionResponse:
    require_owner(user)
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

        row = conn.execute(
            sql(
                """
                SELECT gc.*, u.email AS assigned_user_email, u.name AS assigned_user_name
                FROM google_connections gc
                LEFT JOIN users u ON u.id = gc.assigned_user_id
                WHERE gc.id = ?
                """
            ),
            (connection_id,),
        ).fetchone()

    return _serialize(row)


@router.post("/access", response_model=GoogleConnectionResponse, status_code=status.HTTP_201_CREATED)
def create_account_access(payload: CreateAccountAccessRequest, user: dict = CurrentUser) -> GoogleConnectionResponse:
    require_owner(user)
    display_name = payload.display_name.strip()
    if not display_name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre de la cuenta es obligatorio")
    if len(payload.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contrasena debe tener al menos 6 caracteres")

    with db_session() as conn:
        existing_user = conn.execute(sql("SELECT id FROM users WHERE email = ?"), (str(payload.user_email),)).fetchone()
        if existing_user:
            raise HTTPException(status.HTTP_409_CONFLICT, "Ya existe un usuario con ese correo")

        account_user_id = insert_and_get_id(
            conn,
            "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'account_user')",
            (display_name, str(payload.user_email), hash_password(payload.password)),
        )
        conn.execute(
            sql("INSERT INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'account_user')"),
            (user["organization_id"], account_user_id),
        )
        connection_id = insert_and_get_id(
            conn,
            """
            INSERT INTO google_connections (
                organization_id,
                connected_by_user_id,
                assigned_user_id,
                display_name,
                purpose,
                email,
                encrypted_refresh_token,
                scopes,
                status
            )
            VALUES (?, ?, ?, ?, ?, ?, NULL, ?, 'pending')
            """,
            (
                user["organization_id"],
                user["id"],
                account_user_id,
                display_name,
                payload.purpose,
                str(payload.user_email),
                json.dumps([]),
            ),
        )
        row = conn.execute(
            sql(
                """
                SELECT gc.*, u.email AS assigned_user_email, u.name AS assigned_user_name
                FROM google_connections gc
                LEFT JOIN users u ON u.id = gc.assigned_user_id
                WHERE gc.id = ?
                """
            ),
            (connection_id,),
        ).fetchone()

    return _serialize(row)


@router.patch("/{connection_id}", response_model=GoogleConnectionResponse)
def update_connection(
    connection_id: int,
    payload: UpdateGoogleConnectionRequest,
    user: dict = CurrentUser,
) -> GoogleConnectionResponse:
    require_owner(user)
    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT * FROM google_connections WHERE id = ? AND organization_id = ?"),
            (connection_id, user["organization_id"]),
        ).fetchone()
        if not connection:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")
        if payload.password is not None and payload.password and len(payload.password) < 6:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contrasena debe tener al menos 6 caracteres")

        display_name = payload.display_name if payload.display_name is not None else connection["display_name"]
        purpose = payload.purpose if payload.purpose is not None else connection["purpose"]
        assigned_user_id = connection["assigned_user_id"]

        if payload.user_email:
            existing_user = conn.execute(sql("SELECT id FROM users WHERE email = ?"), (str(payload.user_email),)).fetchone()
            if existing_user and existing_user["id"] != assigned_user_id:
                raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya esta asociado a otro usuario")

            if assigned_user_id:
                params = [display_name or str(payload.user_email), str(payload.user_email)]
                password_sql = ""
                if payload.password:
                    password_sql = ", password_hash = ?"
                    params.append(hash_password(payload.password))
                params.append(assigned_user_id)
                conn.execute(
                    sql(
                        f"""
                        UPDATE users
                        SET name = ?, email = ?{password_sql}
                        WHERE id = ?
                        """
                    ),
                    tuple(params),
                )
            else:
                if not payload.password:
                    raise HTTPException(status.HTTP_400_BAD_REQUEST, "Define una contrasena para crear el usuario de la cuenta")
                assigned_user_id = insert_and_get_id(
                    conn,
                    "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'account_user')",
                    (display_name or str(payload.user_email), str(payload.user_email), hash_password(payload.password)),
                )
                conn.execute(
                    sql("INSERT INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'account_user')"),
                    (user["organization_id"], assigned_user_id),
                )

        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET display_name = ?, purpose = ?, assigned_user_id = ?, updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (display_name, purpose, assigned_user_id, connection_id, user["organization_id"]),
        )
        row = conn.execute(
            sql(
                """
                SELECT gc.*, u.email AS assigned_user_email, u.name AS assigned_user_name
                FROM google_connections gc
                LEFT JOIN users u ON u.id = gc.assigned_user_id
                WHERE gc.id = ?
                """
            ),
            (connection_id,),
        ).fetchone()

    return _serialize(row)


@router.patch("/{connection_id}/followup", response_model=GoogleConnectionResponse)
def update_connection_followup(
    connection_id: int,
    payload: AccountFollowupConfigUpdate,
    user: dict = CurrentUser,
) -> GoogleConnectionResponse:
    require_owner(user)
    if payload.response_time_minutes < 1:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El tiempo maximo de respuesta debe ser mayor a cero")

    with db_session() as conn:
        connection = conn.execute(
            sql("SELECT * FROM google_connections WHERE id = ? AND organization_id = ?"),
            (connection_id, user["organization_id"]),
        ).fetchone()
        if not connection:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        conn.execute(
            sql(
                """
                UPDATE google_connections
                SET followup_enabled = ?,
                    followup_response_time_minutes = ?,
                    followup_notify_whatsapp_on_overdue = ?,
                    followup_warn_before_minutes = ?,
                    followup_escalation_minutes = ?,
                    updated_at = CURRENT_TIMESTAMP
                WHERE id = ? AND organization_id = ?
                """
            ),
            (
                payload.enabled if payload.enabled in (True, False) else False,
                payload.response_time_minutes,
                payload.notify_whatsapp_on_overdue if payload.notify_whatsapp_on_overdue in (True, False) else False,
                payload.warn_before_minutes,
                payload.escalation_minutes,
                connection_id,
                user["organization_id"],
            ),
        )
        row = conn.execute(sql("SELECT * FROM google_connections WHERE id = ?"), (connection_id,)).fetchone()

    return _serialize(row)


@router.delete("/{connection_id}", status_code=status.HTTP_204_NO_CONTENT)
def unlink_connection(connection_id: int, user: dict = CurrentUser) -> None:
    require_owner(user)
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
