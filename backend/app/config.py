import os
from pathlib import Path

from dotenv import load_dotenv


BASE_DIR = Path(__file__).resolve().parent.parent
load_dotenv(BASE_DIR / ".env")

DATA_DIR = BASE_DIR / "data"
STORAGE_DIR = BASE_DIR / "storage"
ATTACHMENTS_DIR = STORAGE_DIR / "attachments"
DATABASE_PATH = DATA_DIR / "app.sqlite3"
DATABASE_URL = os.getenv("DATABASE_URL")

APP_SECRET = os.getenv("APP_SECRET", "change-this-local-dev-secret")
TOKEN_TTL_SECONDS = 60 * 60 * 8
FRONTEND_ORIGIN = os.getenv("FRONTEND_ORIGIN", "http://127.0.0.1:5173")
GOOGLE_CLIENT_ID = os.getenv("GOOGLE_CLIENT_ID", "")
GOOGLE_CLIENT_SECRET = os.getenv("GOOGLE_CLIENT_SECRET", "")
GOOGLE_REDIRECT_URI = os.getenv("GOOGLE_REDIRECT_URI", "http://127.0.0.1:8000/google/oauth/callback")
GOOGLE_PUBSUB_TOPIC = os.getenv("GOOGLE_PUBSUB_TOPIC", "")
OPENAI_API_KEY = os.getenv("OPENAI_API_KEY", "")
OPENAI_MODEL = os.getenv("OPENAI_MODEL", "gpt-5-mini")
WHATSAPP_NUMBER_ASSISTANT = os.getenv("WHATSAPP_NUMBER_ASSISTANT", "")
WHATSAPP_SEND_TEXT_URL = os.getenv("WHATSAPP_SEND_TEXT_URL", "")
WHATSAPP_SEND_TEXT_TOKEN = os.getenv("WHATSAPP_SEND_TEXT_TOKEN", "")
WHATSAPP_SEND_SESSION = os.getenv("WHATSAPP_SEND_SESSION", "email-assistance")
NAGER_DATE_BASE_URL = os.getenv("NAGER_DATE_BASE_URL", "https://date.nager.at/api/v4/Holidays")
SEED_DEMO_USER = os.getenv("SEED_DEMO_USER", "false").lower() in {"1", "true", "yes"}

DEMO_USER = {
    "name": os.getenv("DEMO_USER_NAME", "Usuario local"),
    "email": os.getenv("DEMO_USER_EMAIL", ""),
    "password": os.getenv("DEMO_USER_PASSWORD", ""),
    "organization_name": os.getenv("DEMO_ORGANIZATION_NAME", "Organizacion local"),
}
