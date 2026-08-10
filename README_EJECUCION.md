# Guia de ejecucion y despliegue

Este archivo explica como levantar Email Assistance en local o produccion, con base de datos, con o sin frontend, con Docker y sin Docker.

## Servicios

```text
backend   FastAPI, puerto 8000
frontend  React + Vite, puerto 5173
db        PostgreSQL, puerto 5432
```

Endpoints utiles:

```text
Backend health: http://127.0.0.1:8000/health
Backend docs:   http://127.0.0.1:8000/docs
Frontend:       http://127.0.0.1:5173
```

Usuario demo:

```text
email: demo@example.com
password: Demo123!
```

## Variables necesarias

Backend: `backend/.env`

```env
APP_SECRET=change-this-dev-secret-before-production
FRONTEND_ORIGIN=http://localhost:5173
DATABASE_URL=postgresql://email_assistance:email_assistance@localhost:5432/email_assistance
DEMO_USER_EMAIL=demo@example.com
DEMO_USER_PASSWORD=Demo123!
DEMO_ORGANIZATION_NAME=Organizacion Demo
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback
GOOGLE_PUBSUB_TOPIC=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5-mini
WHATSAPP_NUMBER_ASSISTANT=
WHATSAPP_SEND_TEXT_URL=
WHATSAPP_SEND_TEXT_TOKEN=
WHATSAPP_SEND_SESSION=email-assistance
```

Frontend: `frontend/.env`

```env
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Importante: en Docker Compose, el backend sobreescribe `DATABASE_URL` automaticamente para apuntar a `db:5432`.

## Local con Docker, backend + PostgreSQL

Usa este modo si solo necesitas API y base de datos.

```bash
docker compose up -d --build db backend
```

Verificar:

```bash
docker compose ps db backend
curl http://127.0.0.1:8000/health
```

La URL efectiva de base dentro del contenedor es:

```text
postgresql://email_assistance:email_assistance@db:5432/email_assistance
```

Apagar:

```bash
docker compose down
```

## Local con Docker, proyecto completo

Levanta PostgreSQL, backend y frontend.

```bash
docker compose up -d --build
```

URLs:

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000/docs
Postgres: localhost:5432
```

Ver logs:

```bash
docker compose logs -f backend
docker compose logs -f frontend
docker compose logs -f db
```

Recrear solo un servicio:

```bash
docker compose up -d --build backend
docker compose up -d --build frontend
```

## Local sin Docker, con PostgreSQL local

Primero instala y levanta PostgreSQL en tu maquina.

Crear usuario y base:

```sql
CREATE USER email_assistance WITH PASSWORD 'email_assistance';
CREATE DATABASE email_assistance OWNER email_assistance;
```

Configura `backend/.env`:

```env
DATABASE_URL=postgresql://email_assistance:email_assistance@localhost:5432/email_assistance
```

Levantar backend:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Las tablas se crean automaticamente al iniciar el backend.

Levantar frontend:

```bash
cd frontend
npm install
npm run dev
```

## Local sin Docker, sin PostgreSQL

Solo para desarrollo rapido. Usa SQLite local.

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="sqlite"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Luego, si necesitas frontend:

```bash
cd frontend
npm install
npm run dev
```

## Backend sin frontend

Con Docker:

```bash
docker compose up -d --build db backend
```

Sin Docker:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

Consumir la API desde otro cliente:

```text
http://HOST_DEL_BACKEND:8000/docs
```

Si no hay frontend, configura `FRONTEND_ORIGIN` con el origen real que consumira la API o con el origen del panel externo que uses.

## Frontend sin backend local

Usa esto si el backend esta en otro servidor.

Configura `frontend/.env`:

```env
VITE_API_BASE_URL=https://api.tu-dominio.com
```

Desarrollo:

```bash
cd frontend
npm install
npm run dev
```

Build de produccion:

```bash
cd frontend
npm run build
```

El resultado queda en:

```text
frontend/dist
```

Sirve esa carpeta con Nginx, Apache, CDN, Vercel, Netlify o cualquier hosting estatico.

## Produccion con Docker

Recomendado:

- PostgreSQL administrado o un contenedor PostgreSQL con volumen persistente y backups.
- Backend como contenedor FastAPI.
- Frontend compilado y servido como estatico.
- Proxy HTTPS delante del backend, por ejemplo Nginx, Traefik, Caddy o load balancer cloud.

Variables minimas de backend para produccion:

```env
APP_SECRET=un-secreto-largo-y-unico
FRONTEND_ORIGIN=https://app.tu-dominio.com
DATABASE_URL=postgresql://usuario:password@host-db:5432/email_assistance
GOOGLE_CLIENT_ID=...
GOOGLE_CLIENT_SECRET=...
GOOGLE_REDIRECT_URI=https://api.tu-dominio.com/google/oauth/callback
GOOGLE_PUBSUB_TOPIC=projects/tu-proyecto/topics/tu-topico
OPENAI_API_KEY=...
OPENAI_MODEL=gpt-5-mini
WHATSAPP_NUMBER_ASSISTANT=...
WHATSAPP_SEND_TEXT_URL=https://tu-agente-whatsapp/webhook/whatsapp/email-assistance
WHATSAPP_SEND_TEXT_TOKEN=
WHATSAPP_SEND_SESSION=email-assistance
```

Ejemplo backend con Docker fuera de Compose:

```bash
cd backend
docker build -t email-assistance-backend .
docker run -d --name email-assistance-backend \
  -p 8000:8000 \
  --env-file .env \
  email-assistance-backend
```

Si el backend corre en Docker y PostgreSQL corre en la maquina host, `localhost` dentro del contenedor no es la maquina host. En Docker Desktop normalmente puedes usar:

```env
DATABASE_URL=postgresql://email_assistance:email_assistance@host.docker.internal:5432/email_assistance
```

## Produccion sin Docker

Backend:

```bash
cd backend
python -m venv .venv
source .venv/bin/activate
pip install -r requirements.txt
uvicorn app.main:app --host 0.0.0.0 --port 8000
```

En Linux se recomienda ejecutarlo como servicio con `systemd`, Supervisor o el gestor del proveedor cloud. Pon un proxy HTTPS delante.

Frontend:

```bash
cd frontend
npm install
npm run build
```

Publica `frontend/dist` en un servidor estatico. Asegurate de que `VITE_API_BASE_URL` apunte al dominio publico del backend antes de compilar.

Base de datos:

- Usa PostgreSQL 15 o superior.
- Activa backups.
- Restringe acceso por red.
- No uses credenciales demo.

## Comandos de validacion

Backend:

```bash
python -m compileall backend/app
curl http://127.0.0.1:8000/health
```

Frontend:

```bash
cd frontend
npm run build
```

Docker:

```bash
docker compose ps
docker compose logs --tail 100 backend
```

PostgreSQL en Docker:

```bash
docker compose exec db psql -U email_assistance -d email_assistance
```

## Datos persistentes en Docker Compose

Compose usa estos volumenes:

```text
postgres_data        datos de PostgreSQL
backend_attachments  adjuntos guardados por el backend
```

Apagar sin borrar datos:

```bash
docker compose down
```

Apagar borrando volumenes:

```bash
docker compose down -v
```

Usa `down -v` solo si quieres perder la base de datos y adjuntos del ambiente local.

