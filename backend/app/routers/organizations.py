from fastapi import APIRouter, HTTPException, status

from app.db import db_session, insert_and_get_id, sql
from app.dependencies import AuthenticatedUser
from app.schemas import OrganizationCreate, OrganizationResponse, OrganizationUpdate

router = APIRouter(prefix="/organizations", tags=["organizations"])


def _serialize(row) -> OrganizationResponse:
    return OrganizationResponse(
        id=row["id"],
        name=row["name"],
        role=row["role"],
        created_at=str(row["created_at"]),
    )


@router.get("", response_model=list[OrganizationResponse])
def list_organizations(user: dict = AuthenticatedUser) -> list[OrganizationResponse]:
    with db_session() as conn:
        rows = conn.execute(
            sql(
                """
                SELECT o.id, o.name, o.created_at, om.role
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
        organization_id = insert_and_get_id(conn, "INSERT INTO organizations (name) VALUES (?)", (name,))
        conn.execute(
            sql("INSERT INTO organization_members (organization_id, user_id, role) VALUES (?, ?, 'owner')"),
            (organization_id, user["id"]),
        )
        row = conn.execute(
            sql(
                """
                SELECT o.id, o.name, o.created_at, om.role
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

        conn.execute(sql("UPDATE organizations SET name = ? WHERE id = ?"), (name, organization_id))
        row = conn.execute(
            sql(
                """
                SELECT o.id, o.name, o.created_at, om.role
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

        conn.execute(sql("DELETE FROM organizations WHERE id = ?"), (organization_id,))
