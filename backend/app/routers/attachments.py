import shutil
import uuid
from pathlib import Path

from fastapi import APIRouter, File, HTTPException, UploadFile, status

from app.config import ATTACHMENTS_DIR
from app.db import db_session, insert_and_get_id, sql
from app.dependencies import CurrentUser
from app.schemas import AttachmentResponse

router = APIRouter(prefix="/attachments", tags=["attachments"])


def _serialize_attachment(row) -> AttachmentResponse:
    data = dict(row)
    data["created_at"] = str(data["created_at"])
    return AttachmentResponse(**data)


def _connection_belongs_to_org(conn, connection_id: int, organization_id: int) -> bool:
    row = conn.execute(
        sql(
        "SELECT id FROM google_connections WHERE id = ? AND organization_id = ?",
        ),
        (connection_id, organization_id),
    ).fetchone()
    return row is not None


@router.post("/{connection_id}", response_model=AttachmentResponse, status_code=status.HTTP_201_CREATED)
def upload_attachment(connection_id: int, file: UploadFile = File(...), user: dict = CurrentUser) -> AttachmentResponse:
    with db_session() as conn:
        if not _connection_belongs_to_org(conn, connection_id, user["organization_id"]):
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Conexion no encontrada")

        safe_name = Path(file.filename or "attachment.bin").name
        org_dir = ATTACHMENTS_DIR / str(user["organization_id"]) / str(connection_id)
        org_dir.mkdir(parents=True, exist_ok=True)
        local_name = f"{uuid.uuid4().hex}-{safe_name}"
        local_path = org_dir / local_name

        with local_path.open("wb") as target:
            shutil.copyfileobj(file.file, target)

        attachment_id = insert_and_get_id(
            conn,
            """
            INSERT INTO email_attachments (
                google_connection_id,
                filename,
                mime_type,
                size_bytes,
                storage_provider,
                storage_path
            )
            VALUES (?, ?, ?, ?, 'local', ?)
            """,
            (
                connection_id,
                safe_name,
                file.content_type or "application/octet-stream",
                local_path.stat().st_size,
                str(local_path.relative_to(ATTACHMENTS_DIR)),
            ),
        )
        row = conn.execute(sql("SELECT * FROM email_attachments WHERE id = ?"), (attachment_id,)).fetchone()

    return _serialize_attachment(row)


@router.get("", response_model=list[AttachmentResponse])
def list_attachments(user: dict = CurrentUser) -> list[AttachmentResponse]:
    with db_session() as conn:
        rows = conn.execute(
            sql(
            """
            SELECT a.*
            FROM email_attachments a
            JOIN google_connections gc ON gc.id = a.google_connection_id
            WHERE gc.organization_id = ?
            ORDER BY a.created_at DESC
            """,
            ),
            (user["organization_id"],),
        ).fetchall()
    return [_serialize_attachment(row) for row in rows]
