import json

import httpx
from fastapi import HTTPException, status

from app.ai_usage import extract_usage_tokens, log_ai_usage
from app.config import OPENAI_API_KEY, OPENAI_MODEL


def _openai_output_text(payload: dict) -> str:
    output_text = payload.get("output_text")
    if output_text:
        return str(output_text)
    chunks = []
    for item in payload.get("output", []):
        for content in item.get("content", []):
            if content.get("type") in {"output_text", "text"}:
                chunks.append(content.get("text", ""))
    return "".join(chunks)


def _call_openai(
    prompt: str,
    *,
    purpose: str,
    organization_id: int | None = None,
    user_id: int | None = None,
    google_connection_id: int | None = None,
    automation_rule_id: int | None = None,
    metadata: dict | None = None,
) -> str:
    if not OPENAI_API_KEY:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "Falta OPENAI_API_KEY en backend/.env")

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
        log_ai_usage(
            purpose=purpose,
            model=OPENAI_MODEL,
            success=False,
            error_message=f"http_{response.status_code}",
            organization_id=organization_id,
            user_id=user_id,
            google_connection_id=google_connection_id,
            automation_rule_id=automation_rule_id,
            metadata=metadata,
        )
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI rechazo la solicitud")

    payload = response.json()
    input_tokens, output_tokens, total_tokens = extract_usage_tokens(payload)
    output_text = _openai_output_text(payload)
    log_ai_usage(
        purpose=purpose,
        model=OPENAI_MODEL,
        input_tokens=input_tokens,
        output_tokens=output_tokens,
        total_tokens=total_tokens,
        success=True,
        organization_id=organization_id,
        user_id=user_id,
        google_connection_id=google_connection_id,
        automation_rule_id=automation_rule_id,
        metadata={**(metadata or {}), "response_chars": len(output_text)},
    )
    return output_text


def draft_rule_from_text(
    text: str,
    connection_ids: list[int],
    *,
    organization_id: int | None = None,
    user_id: int | None = None,
) -> dict:
    prompt = f"""
Convierte esta instruccion en una regla JSON para filtrar correos de Gmail.
Devuelve solo JSON valido con estas claves:
name, connection_ids, sender_contains, subject_contains, has_attachment, action_type, configuration.

Reglas:
- name debe ser un titulo corto, alusivo y facil de escanear (maximo 6 palabras), en espanol. Ejemplos: "Facturas PDF", "Pruebas de integracion", "Alertas de cobranza". No uses la descripcion completa como name.
- action_type debe ser "mark_detected".
- Si no hay remitente, sender_contains debe ser null.
- Si no hay asunto, subject_contains debe ser null.
- has_attachment puede ser true, false o null.
- configuration puede incluir allowed_mime_types o notas.
- Usa estos connection_ids por defecto si el usuario no especifica otros: {connection_ids}.

Texto del usuario:
{text}
"""
    output_text = _call_openai(
        prompt,
        purpose="draft_rule",
        organization_id=organization_id,
        user_id=user_id,
        metadata={"connection_ids": connection_ids},
    )

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


def generate_rule_title(
    text: str,
    *,
    organization_id: int | None = None,
    user_id: int | None = None,
) -> str:
    """Genera un titulo corto alusivo para reglas creadas con IA."""
    fallback = text.strip()
    if len(fallback) > 48:
        fallback = f"{fallback[:45].rstrip()}..."
    if not OPENAI_API_KEY:
        return fallback or "Regla IA"

    prompt = f"""
Genera un titulo corto para una regla de filtrado de correos.
Devuelve solo JSON valido: {{"name": "..."}}

Requisitos del titulo:
- Espanol
- Maximo 6 palabras
- Alusivo al proposito de la regla
- Facil de escanear en una lista
- Sin comillas ni puntuacion final
- No copies la descripcion completa

Descripcion de la regla:
{text}
"""
    try:
        output_text = _call_openai(
            prompt,
            purpose="generate_rule_title",
            organization_id=organization_id,
            user_id=user_id,
        )
        result = json.loads(output_text)
        name = str(result.get("name") or "").strip()
    except Exception:
        return fallback or "Regla IA"

    if not name:
        return fallback or "Regla IA"
    if len(name) > 60:
        name = f"{name[:57].rstrip()}..."
    return name


def email_matches_ai_rule(
    rule_description: str,
    email_context: dict,
    *,
    organization_id: int | None = None,
    google_connection_id: int | None = None,
    automation_rule_id: int | None = None,
) -> bool:
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
    output_text = _call_openai(
        prompt,
        purpose="email_match",
        organization_id=organization_id,
        google_connection_id=google_connection_id,
        automation_rule_id=automation_rule_id,
        metadata={"has_subject": bool(email_context.get("subject"))},
    )

    try:
        result = json.loads(output_text)
    except Exception as exc:
        raise HTTPException(status.HTTP_400_BAD_REQUEST, "OpenAI no devolvio JSON valido") from exc

    return bool(result.get("matches"))


def answer_whatsapp_assistant(
    user_message: str,
    context: dict,
    *,
    organization_id: int | None = None,
    google_connection_id: int | None = None,
) -> str:
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
    try:
        output_text = _call_openai(
            prompt,
            purpose="whatsapp_assistant",
            organization_id=organization_id,
            google_connection_id=google_connection_id,
        )
        return output_text.strip() or "Por ahora puedo notificarte sobre correos que coincidan con tus reglas habilitadas para WhatsApp."
    except Exception:
        return "Por ahora puedo notificarte sobre correos que coincidan con tus reglas habilitadas para WhatsApp."
