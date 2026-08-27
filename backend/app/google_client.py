from datetime import datetime, timedelta, timezone

import httpx
from fastapi import HTTPException, status

from app.config import GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET
from app.security import decrypt_secret

GOOGLE_TOKEN_URL = "https://oauth2.googleapis.com/token"
GOOGLE_REVOKE_URL = "https://oauth2.googleapis.com/revoke"
GMAIL_API_BASE = "https://gmail.googleapis.com/gmail/v1"


def refresh_access_token(encrypted_refresh_token: str | None) -> tuple[str, datetime]:
    try:
        refresh_token = decrypt_secret(encrypted_refresh_token)
    except Exception as exc:
        raise HTTPException(
            status.HTTP_400_BAD_REQUEST,
            "No se pudo descifrar el refresh_token. Reconecta esta cuenta con Google OAuth.",
        ) from exc

    if not refresh_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Esta cuenta no tiene refresh_token. Reconectala con Google.")

    with httpx.Client(timeout=20, trust_env=False) as client:
        response = client.post(
            GOOGLE_TOKEN_URL,
            data={
                "client_id": GOOGLE_CLIENT_ID,
                "client_secret": GOOGLE_CLIENT_SECRET,
                "refresh_token": refresh_token,
                "grant_type": "refresh_token",
            },
        )

    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google rechazo la renovacion del access_token")

    payload = response.json()
    access_token = payload.get("access_token")
    if not access_token:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google no devolvio access_token")

    expires_at = datetime.now(timezone.utc) + timedelta(seconds=int(payload.get("expires_in", 3600)))
    return access_token, expires_at


def gmail_get(access_token: str, path: str, params: dict | None = None) -> dict:
    with httpx.Client(timeout=20, trust_env=False) as client:
        response = client.get(
            f"{GMAIL_API_BASE}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            params=params,
        )

    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google rechazo la consulta a Gmail")

    return response.json()


def gmail_post(access_token: str, path: str, payload: dict) -> dict:
    with httpx.Client(timeout=20, trust_env=False) as client:
        response = client.post(
            f"{GMAIL_API_BASE}{path}",
            headers={"Authorization": f"Bearer {access_token}"},
            json=payload,
        )

    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Google rechazo la solicitud a Gmail")

    if not response.content:
        return {}
    return response.json()


def gmail_get_attachment(access_token: str, message_id: str, attachment_id: str) -> dict:
    return gmail_get(access_token, f"/users/me/messages/{message_id}/attachments/{attachment_id}")


def revoke_refresh_token(encrypted_refresh_token: str | None) -> bool:
    if not encrypted_refresh_token:
        return False

    try:
        refresh_token = decrypt_secret(encrypted_refresh_token)
    except Exception:
        return False

    if not refresh_token:
        return False

    try:
        with httpx.Client(timeout=10, trust_env=False) as client:
            response = client.post(GOOGLE_REVOKE_URL, data={"token": refresh_token})
    except httpx.HTTPError:
        return False

    return response.status_code in (200, 400)
