import json
import time
from datetime import datetime, timedelta, timezone
from urllib.parse import urlencode

import httpx
from fastapi import APIRouter, HTTPException, Query, status
from fastapi.responses import RedirectResponse

from app.config import (
    FRONTEND_ORIGIN,
    GOOGLE_CLIENT_ID,
    GOOGLE_CLIENT_SECRET,
    GOOGLE_REDIRECT_URI,
)
from app.db import db_session, sql, using_postgres
from app.dependencies import CurrentUser
from app.schemas import GoogleConnectionResponse, GoogleOAuthStartResponse
from app.security import create_signed_payload, decode_signed_payload, encrypt_secret

router = APIRouter(prefix="/google/oauth", tags=["google oauth"])

GOOGLE_AUTH_URL = "https://accounts.google.com/o/oauth2/v2/auth"
GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GMAIL_PROFILE_URL = "https://gmail.googleapis.com/gmail/v1/users/me/profile"
GOOGLE_SCOPES = ["https://www.googleapis.com/auth/gmail.readonly"]


def _ensure_google_config() -> None:
    if not GOOGLE_CLIENT_ID or not GOOGLE_CLIENT_SECRET:
        raise HTTPException(
            status.HTTP_500_INTERNAL_SERVER_ERROR,
            "Faltan GOOGLE_CLIENT_ID y/o GOOGLE_CLIENT_SECRET en backend/.env",
        )


def _serialize(row) -> GoogleConnectionResponse:
    return GoogleConnectionResponse(
        id=row["id"],
        email=row["email"],
        display_name=row["display_name"],
        purpose=row["purpose"],
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


@router.get("/start", response_model=GoogleOAuthStartResponse)
def start_google_oauth(
    display_name: str | None = Query(None, max_length=160),
    purpose: str | None = Query(None, max_length=800),
    user: dict = CurrentUser,
) -> GoogleOAuthStartResponse:
    _ensure_google_config()
    state = create_signed_payload(
        {
            "sub": user["id"],
            "organization_id": user["organization_id"],
            "display_name": (display_name or "").strip(),
            "purpose": (purpose or "").strip(),
            "nonce": str(time.time_ns()),
        },
        ttl_seconds=600,
    )
    query = urlencode(
        {
            "client_id": GOOGLE_CLIENT_ID,
            "redirect_uri": GOOGLE_REDIRECT_URI,
            "response_type": "code",
            "scope": " ".join(GOOGLE_SCOPES),
            "access_type": "offline",
            "prompt": "consent",
            "include_granted_scopes": "true",
            "state": state,
        }
    )
    return GoogleOAuthStartResponse(authorization_url=f"{GOOGLE_AUTH_URL}?{query}")


@router.get("/callback")
def google_oauth_callback(
    code: str | None = Query(None),
    state: str = Query(...),
    error: str | None = Query(None),
):
    _ensure_google_config()

    if error:
        return _redirect_with_error(f"Google OAuth devolvio error: {error}")
    if not code:
        return _redirect_with_error("Google no devolvio codigo OAuth")

    try:
        state_payload = decode_signed_payload(state)
    except HTTPException:
        return _redirect_with_error("Estado OAuth invalido o expirado")

    try:
        connection = _exchange_and_store_connection(code, state_payload)
    except HTTPException as exc:
        return _redirect_with_error(str(exc.detail))
    except Exception as exc:
        return _redirect_with_error(f"Error interno procesando OAuth: {exc}")

    return RedirectResponse(
        f"{FRONTEND_ORIGIN}?google_connected={connection.email}",
        status_code=status.HTTP_302_FOUND,
    )


def _redirect_with_error(message: str) -> RedirectResponse:
    query = urlencode({"google_error": message})
    return RedirectResponse(f"{FRONTEND_ORIGIN}?{query}", status_code=status.HTTP_302_FOUND)


def _exchange_and_store_connection(code: str, state_payload: dict) -> GoogleConnectionResponse:
    with httpx.Client(timeout=20, trust_env=False) as client:
        token_response = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "code": code,
                "grant_type": "authorization_code",
                "redirect_uri": GOOGLE_REDIRECT_URI,
            },
        )

        if token_response.status_code >= 400:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google rechazo el intercambio de codigo OAuth")

        tokens = token_response.json()
        access_token = tokens.get("access_token")
        refresh_token = tokens.get("refresh_token")

        if not access_token:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google no devolvio access_token")

        profile_response = client.get(
            GMAIL_PROFILE_URL,
            headers={"Authorization": f"Bearer {access_token}"},
        )

        if profile_response.status_code >= 400:
            raise HTTPException(status.HTTP_400_BAD_REQUEST, "No se pudo leer el perfil de Gmail")

    profile = profile_response.json()
    email = profile.get("emailAddress")
    if not email:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google no devolvio el correo de Gmail")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(tokens.get("expires_in", 3600)))
    scopes = tokens.get("scope", " ".join(GOOGLE_SCOPES)).split()
    encrypted_refresh_token = encrypt_secret(refresh_token)
    display_name = state_payload.get("display_name") or email
    purpose = state_payload.get("purpose") or "Cuenta conectada por OAuth"

    with db_session() as conn:
        existing = conn.execute(
            sql("SELECT encrypted_refresh_token FROM google_connections WHERE organization_id = ? AND email = ?"),
            (state_payload["organization_id"], email),
        ).fetchone()

        if existing and not encrypted_refresh_token:
            encrypted_refresh_token = existing["encrypted_refresh_token"]

        if not encrypted_refresh_token:
            raise HTTPException(
                status.HTTP_400_BAD_REQUEST,
                "Google no devolvio refresh_token. Reintenta con prompt=consent o revoca el acceso anterior.",
            )

        if using_postgres():
            row = conn.execute(
                """
                INSERT INTO google_connections (
                    organization_id,
                    connected_by_user_id,
                    google_user_id,
                    display_name,
                    purpose,
                    email,
                    encrypted_refresh_token,
                    access_token_expires_at,
                    scopes,
                    status,
                    gmail_history_id,
                    updated_at
                )
                VALUES (%s, %s, %s, %s, %s, %s, %s, %s, %s, 'connected', %s, CURRENT_TIMESTAMP)
                ON CONFLICT (organization_id, email)
                DO UPDATE SET
                    connected_by_user_id = EXCLUDED.connected_by_user_id,
                    google_user_id = EXCLUDED.google_user_id,
                    display_name = EXCLUDED.display_name,
                    purpose = EXCLUDED.purpose,
                    encrypted_refresh_token = EXCLUDED.encrypted_refresh_token,
                    access_token_expires_at = EXCLUDED.access_token_expires_at,
                    scopes = EXCLUDED.scopes,
                    status = 'connected',
                    gmail_history_id = EXCLUDED.gmail_history_id,
                    updated_at = CURRENT_TIMESTAMP
                RETURNING *
                """,
                (
                    state_payload["organization_id"],
                    state_payload["sub"],
                    profile.get("emailAddress"),
                    display_name,
                    purpose,
                    email,
                    encrypted_refresh_token,
                    expires_at,
                    json.dumps(scopes),
                    profile.get("historyId"),
                ),
            ).fetchone()
        else:
            conn.execute(
                """
                INSERT INTO google_connections (
                    organization_id,
                    connected_by_user_id,
                    google_user_id,
                    display_name,
                    purpose,
                    email,
                    encrypted_refresh_token,
                    access_token_expires_at,
                    scopes,
                    status,
                    gmail_history_id,
                    updated_at
                )
                VALUES (?, ?, ?, ?, ?, ?, ?, ?, ?, 'connected', ?, CURRENT_TIMESTAMP)
                ON CONFLICT (organization_id, email)
                DO UPDATE SET
                    connected_by_user_id = excluded.connected_by_user_id,
                    google_user_id = excluded.google_user_id,
                    display_name = excluded.display_name,
                    purpose = excluded.purpose,
                    encrypted_refresh_token = excluded.encrypted_refresh_token,
                    access_token_expires_at = excluded.access_token_expires_at,
                    scopes = excluded.scopes,
                    status = 'connected',
                    gmail_history_id = excluded.gmail_history_id,
                    updated_at = CURRENT_TIMESTAMP
                """,
                (
                    state_payload["organization_id"],
                    state_payload["sub"],
                    profile.get("emailAddress"),
                    display_name,
                    purpose,
                    email,
                    encrypted_refresh_token,
                    expires_at.isoformat(),
                    json.dumps(scopes),
                    profile.get("historyId"),
                ),
            )
            row = conn.execute(
                sql("SELECT * FROM google_connections WHERE organization_id = ? AND email = ?"),
                (state_payload["organization_id"], email),
            ).fetchone()

    return _serialize(row)
