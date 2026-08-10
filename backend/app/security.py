import base64
import hashlib
import hmac
import json
import os
import time
from typing import Any

from cryptography.hazmat.primitives.ciphers.aead import AESGCM
from fastapi import HTTPException, status

from app.config import APP_SECRET, TOKEN_TTL_SECONDS


def hash_password(password: str, salt: bytes | None = None) -> str:
    salt = salt or os.urandom(16)
    digest = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return f"{base64.urlsafe_b64encode(salt).decode()}.{base64.urlsafe_b64encode(digest).decode()}"


def verify_password(password: str, stored_hash: str) -> bool:
    try:
        salt_text, digest_text = stored_hash.split(".", 1)
        salt = base64.urlsafe_b64decode(salt_text.encode())
        expected = base64.urlsafe_b64decode(digest_text.encode())
    except ValueError:
        return False

    actual = hashlib.pbkdf2_hmac("sha256", password.encode("utf-8"), salt, 120_000)
    return hmac.compare_digest(actual, expected)


def _sign(payload: str) -> str:
    signature = hmac.new(APP_SECRET.encode(), payload.encode(), hashlib.sha256).digest()
    return base64.urlsafe_b64encode(signature).decode().rstrip("=")


def create_token(user_id: int) -> str:
    payload = {
        "sub": user_id,
        "exp": int(time.time()) + TOKEN_TTL_SECONDS,
    }
    payload_text = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{payload_text}.{_sign(payload_text)}"


def decode_token(token: str) -> dict[str, Any]:
    try:
        payload_text, signature = token.split(".", 1)
    except ValueError as exc:
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido") from exc

    if not hmac.compare_digest(signature, _sign(payload_text)):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token invalido")

    padded = payload_text + "=" * (-len(payload_text) % 4)
    payload = json.loads(base64.urlsafe_b64decode(padded.encode()))
    if payload["exp"] < int(time.time()):
        raise HTTPException(status.HTTP_401_UNAUTHORIZED, "Token expirado")
    return payload


def _encryption_key() -> bytes:
    return hashlib.sha256(APP_SECRET.encode("utf-8")).digest()


def encrypt_secret(value: str | None) -> str | None:
    if not value:
        return None

    nonce = os.urandom(12)
    encrypted = AESGCM(_encryption_key()).encrypt(nonce, value.encode("utf-8"), None)
    return base64.urlsafe_b64encode(nonce + encrypted).decode("utf-8")


def decrypt_secret(value: str | None) -> str | None:
    if not value:
        return None

    raw = base64.urlsafe_b64decode(value.encode("utf-8"))
    nonce, encrypted = raw[:12], raw[12:]
    return AESGCM(_encryption_key()).decrypt(nonce, encrypted, None).decode("utf-8")


def create_signed_payload(payload: dict[str, Any], ttl_seconds: int = 600) -> str:
    payload = {**payload, "exp": int(time.time()) + ttl_seconds}
    payload_text = base64.urlsafe_b64encode(json.dumps(payload).encode()).decode().rstrip("=")
    return f"{payload_text}.{_sign(payload_text)}"


def decode_signed_payload(token: str) -> dict[str, Any]:
    return decode_token(token)
