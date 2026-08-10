import json

import httpx
from fastapi import HTTPException, status

from app.config import OPENAI_API_KEY, OPENAI_MODEL


def draft_rule_from_text(text: str, connection_ids: list[int]) -> dict:
    if not OPENAI_API_KEY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falta OPENAI_API_KEY en backend/.env")

    prompt = f"""
Convierte esta instruccion en una regla JSON para filtrar correos de Gmail.
Devuelve solo JSON valido con estas claves:
name, connection_ids, sender_contains, subject_contains, has_attachment, action_type, configuration.

Reglas:
- action_type debe ser "mark_detected".
- Si no hay remitente, sender_contains debe ser null.
- Si no hay asunto, subject_contains debe ser null.
- has_attachment puede ser true, false o null.
- configuration puede incluir allowed_mime_types o notas.
- Usa estos connection_ids por defecto si el usuario no especifica otros: {connection_ids}.

Texto del usuario:
{text}
"""
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "input": prompt,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI rechazo la generacion de regla")

    payload = response.json()
    output_text = payload.get("output_text")
    if not output_text:
        chunks = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        output_text = "".join(chunks)

    try:
        draft = json.loads(output_text)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI no devolvio JSON valido") from exc

    return {
        "name": draft.get("name") or "Regla generada",
        "connection_ids": draft.get("connection_ids") or connection_ids,
        "sender_contains": draft.get("sender_contains"),
        "subject_contains": draft.get("subject_contains"),
        "has_attachment": draft.get("has_attachment"),
        "action_type": "mark_detected",
        "configuration": draft.get("configuration") or {},
    }


def email_matches_ai_rule(rule_description: str, email_context: dict) -> bool:
    if not OPENAI_API_KEY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falta OPENAI_API_KEY en backend/.env")

    prompt = f"""
Evalua si este correo cumple la intencion de negocio descrita por el usuario.
Responde solo JSON valido con esta forma:
{{"matches": true|false, "reason": "explicacion breve"}}

Descripcion de la regla:
{rule_description}

Correo:
{json.dumps(email_context, ensure_ascii=False)}

Criterios:
- Razona semanticamente; no dependas solo de coincidencias literales.
- Si la descripcion dice que puede o no venir con adjuntos, los adjuntos no deben ser obligatorios.
- Considera remitente, asunto, fragmento, destinatarios y si tiene adjuntos.
- Marca matches true solo cuando el correo claramente pertenece al caso descrito.
"""
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "input": prompt,
            },
        )

    if response.status_code >= 400:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI rechazo la evaluacion de regla")

    payload = response.json()
    output_text = payload.get("output_text")
    if not output_text:
        chunks = []
        for item in payload.get("output", []):
            for content in item.get("content", []):
                if content.get("type") in {"output_text", "text"}:
                    chunks.append(content.get("text", ""))
        output_text = "".join(chunks)

    try:
        result = json.loads(output_text)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI no devolvio JSON valido") from exc

    return bool(result.get("matches"))


def answer_whatsapp_assistant(user_message: str, context: dict) -> str:
    if not OPENAI_API_KEY:
        rules = ", ".join(rule["name"] for rule in context.get("rules", [])) or "ninguna regla"
        return f"Puedo notificarte sobre correos asociados a estas reglas: {rules}."

    prompt = f"""
Eres el asistente WhatsApp de una plataforma de asistencia de correos.
Tu alcance actual esta restringido a explicar y operar notificaciones sobre correos que coinciden con reglas que tienen WhatsApp habilitado.
No prometas acciones fuera de ese alcance.

Contexto disponible:
{json.dumps(context, ensure_ascii=False)}

Mensaje del usuario:
{user_message}

Responde en espanol, breve y claro.
"""
    with httpx.Client(timeout=30, trust_env=False) as client:
        response = client.post(
            "https://api.openai.com/v1/responses",
            headers={
                "Authorization": f"Bearer {OPENAI_API_KEY}",
                "Content-Type": "application/json",
            },
            json={
                "model": OPENAI_MODEL,
                "input": prompt,
            },
        )

    if response.status_code >= 400:
        return "Por ahora puedo notificarte sobre correos que coincidan con tus reglas habilitadas para WhatsApp."

    payload = response.json()
    output_text = payload.get("output_text")
    if output_text:
        return output_text.strip()

    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return ("".join(chunks).strip() or "Por ahora puedo notificarte sobre correos que coincidan con tus reglas habilitadas para WhatsApp.")
