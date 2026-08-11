from fastapi import FastAPI
from fastapi.middleware.cors import CORSMiddleware

from app.config import DEMO_USER, FRONTEND_ORIGIN, GOOGLE_CLIENT_ID, GOOGLE_CLIENT_SECRET, GOOGLE_REDIRECT_URI, WHATSAPP_NUMBER_ASSISTANT
from app.db import init_db
from app.routers import attachments, auth, automation, followups, gmail, google_connections, google_oauth, organizations, whatsapp

app = FastAPI(
    title="Email Assistance API",
    description="V1 local para usuarios, organizaciones, cuentas Google conectadas y adjuntos.",
    version="0.1.0",
)

app.add_middleware(
    CORSMiddleware,
    allow_origins=[FRONTEND_ORIGIN, "http://localhost:5173", "http://127.0.0.1:5173"],
    allow_credentials=True,
    allow_methods=["*"],
    allow_headers=["*"],
)


@app.on_event("startup")
def startup() -> None:
    init_db()


@app.get("/health", tags=["system"])
def health() -> dict:
    return {"status": "ok"}


@app.get("/demo-user", tags=["system"])
def demo_user() -> dict:
    return {
        "email": DEMO_USER["email"],
        "password": DEMO_USER["password"],
        "note": "Usuario sembrado automaticamente para pruebas locales.",
    }


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
