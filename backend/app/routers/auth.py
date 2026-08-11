from fastapi import APIRouter, HTTPException, status

from app.db import db_session, sql
from app.dependencies import CurrentUser, require_super_root
from app.db import insert_and_get_id
from app.schemas import LoginRequest, LoginResponse, RootUserCreate, UserProfileUpdate, UserResponse
from app.security import create_token, hash_password, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    with db_session() as conn:
        user = conn.execute(
            sql(
            """
            SELECT u.id, u.name, u.email, u.password_hash, u.platform_role
            FROM users u
            WHERE u.email = ?
            LIMIT 1
            """,
            ),
            (payload.email,),
        ).fetchone()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")

    with db_session() as conn:
        membership = conn.execute(
            sql(
                """
                SELECT om.organization_id, om.role, gc.id AS assigned_connection_id
                FROM organization_members om
                LEFT JOIN google_connections gc
                  ON gc.organization_id = om.organization_id
                 AND gc.assigned_user_id = om.user_id
                WHERE om.user_id = ?
                ORDER BY om.created_at ASC
                LIMIT 1
                """
            ),
            (user["id"],),
        ).fetchone()

    role = membership["role"] if membership else user["platform_role"]
    user_data = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
        "platform_role": user["platform_role"],
        "organization_id": membership["organization_id"] if membership else None,
        "role": role,
        "assigned_connection_id": membership["assigned_connection_id"] if membership else None,
    }
    return LoginResponse(access_token=create_token(user["id"]), user=user_data)


@router.get("/me")
def me(user: dict = CurrentUser) -> dict:
    return user


@router.patch("/me")
def update_me(payload: UserProfileUpdate, user: dict = CurrentUser) -> dict:
    name = payload.name.strip() if payload.name is not None else None
    password_hash = hash_password(payload.password) if payload.password else None
    if payload.name is not None and not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre es obligatorio")
    if payload.password is not None and payload.password and len(payload.password) < 6:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contrasena debe tener al menos 6 caracteres")

    with db_session() as conn:
        try:
            conn.execute(
                sql(
                    """
                    UPDATE users
                    SET name = COALESCE(?, name),
                        email = COALESCE(?, email),
                        password_hash = COALESCE(?, password_hash)
                    WHERE id = ?
                    """
                ),
                (name, str(payload.email) if payload.email else None, password_hash, user["id"]),
            )
            if payload.email:
                conn.execute(
                    sql(
                        """
                        UPDATE google_connections
                        SET email = ?, updated_at = CURRENT_TIMESTAMP
                        WHERE assigned_user_id = ? AND status = 'pending'
                        """
                    ),
                    (str(payload.email), user["id"]),
                )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya esta en uso") from exc
            raise
        row = conn.execute(sql("SELECT id, name, email FROM users WHERE id = ?"), (user["id"],)).fetchone()

    return {
        **user,
        "name": row["name"],
        "email": row["email"],
    }


def _serialize_user(row) -> UserResponse:
    return UserResponse(
        id=row["id"],
        name=row["name"],
        email=row["email"],
        platform_role=row["platform_role"],
        created_at=str(row["created_at"]) if "created_at" in row.keys() and row["created_at"] else None,
    )


@router.get("/root-users", response_model=list[UserResponse])
def list_root_users(user: dict = CurrentUser) -> list[UserResponse]:
    require_super_root(user)
    with db_session() as conn:
        rows = conn.execute(
            sql(
                """
                SELECT id, name, email, platform_role, created_at
                FROM users
                WHERE platform_role = 'root'
                ORDER BY created_at DESC
                """
            )
        ).fetchall()
    return [_serialize_user(row) for row in rows]


@router.post("/root-users", response_model=UserResponse, status_code=status.HTTP_201_CREATED)
def create_root_user(payload: RootUserCreate, user: dict = CurrentUser) -> UserResponse:
    require_super_root(user)
    name = payload.name.strip()
    if not name:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "El nombre es obligatorio")
    if len(payload.password) < 3:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "La contrasena debe tener al menos 3 caracteres")

    with db_session() as conn:
        try:
            user_id = insert_and_get_id(
                conn,
                "INSERT INTO users (name, email, password_hash, platform_role) VALUES (?, ?, ?, 'root')",
                (name, str(payload.email), hash_password(payload.password)),
            )
        except Exception as exc:
            if "UNIQUE" in str(exc):
                raise HTTPException(status.HTTP_409_CONFLICT, "Ese correo ya esta en uso") from exc
            raise
        row = conn.execute(
            sql("SELECT id, name, email, platform_role, created_at FROM users WHERE id = ?"),
            (user_id,),
        ).fetchone()

    return _serialize_user(row)
