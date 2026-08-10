from fastapi import APIRouter, HTTPException, status

from app.db import db_session, sql
from app.schemas import LoginRequest, LoginResponse
from app.security import create_token, verify_password

router = APIRouter(prefix="/auth", tags=["auth"])


@router.post("/login", response_model=LoginResponse)
def login(payload: LoginRequest) -> LoginResponse:
    with db_session() as conn:
        user = conn.execute(
            sql(
            """
            SELECT u.id, u.name, u.email, u.password_hash
            FROM users u
            WHERE u.email = ?
            LIMIT 1
            """,
            ),
            (payload.email,),
        ).fetchone()

    if not user or not verify_password(payload.password, user["password_hash"]):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Credenciales invalidas")

    user_data = {
        "id": user["id"],
        "name": user["name"],
        "email": user["email"],
    }
    return LoginResponse(access_token=create_token(user["id"]), user=user_data)
