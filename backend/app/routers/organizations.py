import json
import shutil
from datetime import datetime

from fastapi import APIRouter, HTTPException, status

from app.config import ATTACHMENTS_DIR
from app.db import db_session, insert_and_get_id, sql
from app.dependencies import AuthenticatedUser
from app.holidays import HolidaySyncError, ensure_country_holidays, normalize_country_code
from app.schemas import OrganizationBusinessHoursUpdate, OrganizationCreate, OrganizationResponse, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _serialize(row) -> OrganizationResponse:
    return OrganizationResponse(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        business_timezone=row["business_timezone"],
        business_days=json.loads(row["business_days"] or "[1,2,3,4,5]"),
        business_start_time=row["business_start_time"],
        business_end_time=row["business_end_time"],
        business_day_hours=json.loads(row["business_day_hours"] or "{}") if "business_day_hours" in row.keys() else {},
        holiday_country=row["holiday_country"],
        created_at=str(row["created_at"]),
    )


def _normalize_business_day_hours(value: dict | None) -> dict:
    normalized = {}
    for key, item in (value or {}).items():
        try:
            day = int(key)
        except Exception:
            continue
        if day < 1 or day > 7 or not isinstance(item, dict):
            continue
        enabled = bool(item.get("enabled"))
        uses_default = bool(item.get("uses_default", True))
        start_time = str(item.get("start_time") or "")[:5]
        end_time = str(item.get("end_time") or "")[:5]
        if not uses_default and (not start_time or not end_time or start_time >= end_time):
            raise HTTPException(status.HTTP_400_BAD_REQUEST, f"Horario invalido para el dia {day}")
        normalized[str(day)] = {
            "enabled": enabled,
            "uses_default": uses_default,
            "start_time": start_time if not uses_default else None,
            "end_time": end_time if not uses_default else None,
        }
    return normalized


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(user: dict = AuthenticatedUser) -> list[OrganizationResponse]:
    with db_session() as conn:
        rows = conn.execute(
            sql(
                """
                SELECT o.*, om.role
                FROM organizations o
                JOIN organization_members om ON om.organization_id = o.id
                WHERE om.user_id = ?
                ORDER BY o.created_at ASC
                """
            ),
            (user["id"],),
        ).fetchall()

    return [_serialize(row) for row in rows]


@router.post("", response_model=OrganizationResponse, status_code=status.HTTP_201_CREATED)
def create_organization(payload: OrganizationCreate, user: dict = AuthenticatedUser) -> OrganizationResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre de la organizacion es obligatorio")

    with db_session() as conn:
        if user.get("platform_role") != "root":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para crear organizaciones")
        organization_id = insert_and_get_id(conn, "INSERT INTO organizations (name) VALUES (?)", (name,))
        conn.execute(
            sql("INSERT INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'owner')"),
            (organization_id, user["id"]),
        )
        row = conn.execute(
            sql(
                """
                SELECT o.*, om.role
                FROM organizations o
                JOIN organization_members om ON om.organization_id = o.id
                WHERE o.id = ? AND om.user_id = ?
                """
            ),
            (organization_id, user["id"]),
        ).fetchone()

    return _serialize(row)


@router.patch("/{organization_id}", response_model=OrganizationResponse)
def update_organization(
    organization_id: int,
    payload: OrganizationUpdate,
    user: dict = AuthenticatedUser,
) -> OrganizationResponse:
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre de la organizacion es obligatorio")

    with db_session() as conn:
        membership = conn.execute(
            sql("SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?"),
            (organization_id, user["id"]),
        ).fetchone()
        if not membership:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizacion no encontrada")
        if membership["role"] != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para editar esta organizacion")

        conn.execute(sql("UPDATE organizations SET name = ? WHERE id = ?"), (name, organization_id))
        row = conn.execute(
            sql(
                """
                SELECT o.*, om.role
                FROM organizations o
                JOIN organization_members om ON om.organization_id = o.id
                WHERE o.id = ? AND om.user_id = ?
                """
            ),
            (organization_id, user["id"]),
        ).fetchone()

    return _serialize(row)


@router.patch("/{organization_id}/business-hours", response_model=OrganizationResponse)
def update_business_hours(
    organization_id: int,
    payload: OrganizationBusinessHoursUpdate,
    user: dict = AuthenticatedUser,
) -> OrganizationResponse:
    if not payload.business_days or any(day < 1 or day > 7 for day in payload.business_days):
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Los dias habiles deben estar entre 1 y 7")
    if payload.business_start_time >= payload.business_end_time:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La hora de inicio debe ser menor que la hora de fin")
    day_hours = _normalize_business_day_hours(payload.business_day_hours)
    holiday_country = normalize_country_code(payload.holiday_country)

    with db_session() as conn:
        membership = conn.execute(
            sql("SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?"),
            (organization_id, user["id"]),
        ).fetchone()
        if not membership:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizacion no encontrada")
        if membership["role"] != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para editar el horario")

        conn.execute(
            sql(
                """
                UPDATE organizations
                SET business_timezone = ?,
                    business_days = ?,
                    business_start_time = ?,
                    business_end_time = ?,
                    business_day_hours = ?,
                    holiday_country = ?
                WHERE id = ?
                """
            ),
            (
                payload.business_timezone,
                json.dumps(payload.business_days),
                payload.business_start_time,
                payload.business_end_time,
                json.dumps(day_hours),
                holiday_country,
                organization_id,
            ),
        )
        try:
            year = datetime.utcnow().year
            ensure_country_holidays(conn, organization_id, holiday_country, [year, year + 1])
        except HolidaySyncError as exc:
            raise HTTPException(status.HTTP_502_BAD_GATEWAY, str(exc)) from exc
        row = conn.execute(
            sql(
                """
                SELECT o.*, om.role
                FROM organizations o
                JOIN organization_members om ON om.organization_id = o.id
                WHERE o.id = ? AND om.user_id = ?
                """
            ),
            (organization_id, user["id"]),
        ).fetchone()

    return _serialize(row)


@router.delete("/{organization_id}", status_code=status.HTTP_204_NO_CONTENT)
def delete_organization(organization_id: int, user: dict = AuthenticatedUser) -> None:
    with db_session() as conn:
        membership = conn.execute(
            sql("SELECT role FROM organization_members WHERE organization_id = ? AND user_id = ?"),
            (organization_id, user["id"]),
        ).fetchone()
        if not membership:
            raise HTTPException(status.HTTP_404_NOT_FOUND, "Organizacion no encontrada")
        if membership["role"] != "owner":
            raise HTTPException(status.HTTP_403_FORBIDDEN, "No tienes permisos para eliminar esta organizacion")

        conn.execute(sql("DELETE FROM organizations WHERE id = ?"), (organization_id,))

    organization_folder = (ATTACHMENTS_DIR / str(organization_id)).resolve()
    try:
        organization_folder.relative_to(ATTACHMENTS_DIR.resolve())
    except ValueError:
        return
    if organization_folder.exists():
        shutil.rmtree(organization_folder)
