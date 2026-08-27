from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import CORS_ORIGINS, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, WHATSAPP_NUMBER_ASSISTANT
from app.db import init_db
from app.routers import attachments, auth, automation, followups, gmail, google_connections, google_oauth, organizations, whatsapp

app = FastAPI(
    title="Email Assistance API",
    description="V1 local para usuarios, organizaciones, cuentas Google conectadas y adjuntos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=CORS_ORIGINS,
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.middleware("http")
async def security_headers(request, call_next):
    response = await call_next(request)
    response.headers.setdefault("X-Content-Type-Options", "nosniff")
    response.headers.setdefault("X-Frame-Options", "DENY")
    response.headers.setdefault("Referrer-Policy", "strict-origin-when-cross-origin")
    response.headers.setdefault("Permissions-Policy", "camera=(), microphone=(), geolocation=()")
    if request.url.scheme == "https":
        response.headers.setdefault("Strict-Transport-Security", "max-age=31536000; includeSubDomains")
    return response


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/google/config-status", tags=["system"])
def google_config_status() -> dict:
    return {
        "client_id_configured": bool(GOOGLE_CLIENT_ID),
        "client_secret_configured": bool(GOOGLE_CLIENT_SECRET),
        "redirect_uri": GOOGLE_REDIRECT_URI,
        "whatsapp_assistant_configured": bool(WHATSAPP_NUMBER_ASSISTANT),
    }


app.include_router(auth.router)
app.include_router(organizations.router)
app.include_router(google_connections.router)
app.include_router(google_oauth.router)
app.include_router(gmail.router)
app.include_router(attachments.router)
app.include_router(automation.router)
app.include_router(followups.router)
app.include_router(whatsapp.router)
