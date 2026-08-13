# Email Assistance

V1 sencilla para una suite multiusuario/multicuenta de procesamiento de correos.

Incluye:

- Backend FastAPI.
- Frontend React + TypeScript.
- Autenticacion con roles de plataforma.
- Vinculacion simulada de varias cuentas de correo.
- Inicio/callback OAuth real de Google.
- Sincronizacion manual de correos recientes desde Gmail.
- Descarga local de adjuntos detectados durante la sincronizacion.
- Registro de monitor Gmail `users.watch`.
- Webhook Pub/Sub preparado.
- Reglas basicas de automatizacion.
- Reglas asociadas a cuentas como filtro de sincronizacion.
- Borrador de reglas desde texto con OpenAI.
- Eventos internos para seguimiento.
- Adjuntos guardados en el backend.
- Docker Compose con Postgres, backend y frontend.

## Estructura

```text
backend/      API FastAPI, auth, conexiones y adjuntos
frontend/     React + TS con login y gestion basica de cuentas
docs/         Manuales de usuario y operacion
.agents/      Contexto para futuros agentes de desarrollo
proyect.md    Documento original de producto/arquitectura
```

## Manual de usuario

Consulta la guia funcional de la aplicacion en:

```text
docs/manual-usuario.md
```

## URLs locales

```text
Frontend: http://127.0.0.1:5173
Backend:  http://127.0.0.1:8000/docs
```

El usuario inicial de plataforma se crea en la base de datos mediante migraciones. Despues del primer ingreso, cambia su clave desde el perfil.

## Levantar todo con Docker

Abre Docker Desktop y ejecuta desde la raiz:

```bash
docker compose up -d --build
```

Servicios:

```text
frontend: http://127.0.0.1:5173
backend:  http://127.0.0.1:8000/docs
postgres: localhost:5432
```

Apagar:

```bash
docker compose down
```

Los datos de Postgres quedan en el volumen `postgres_data` y los adjuntos en `backend_attachments`.

## Levantar backend por separado

Backend con SQLite:

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="sqlite"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Backend con Postgres local:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Para Postgres local, revisa `backend/.env` y crea la BD indicada en `DATABASE_URL`.

## Levantar frontend por separado

```bash
cd frontend
npm install
npm run dev
```

El frontend lee `frontend/.env`:

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

## Configurar Google en el backend

Edita `backend/.env`:

```text
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback
GOOGLE_PUBSUB_TOPIC=projects/tu-proyecto/topics/tu-topico
OPENAI_API_KEY=tu-openai-api-key
OPENAI_MODEL=gpt-5-mini
```

En Google Cloud Console debes habilitar Gmail API, configurar OAuth consent screen y agregar el redirect URI anterior al OAuth Client tipo Web application.

Importante: el flujo OAuth base ya existe:

```text
GET /google/oauth/start
GET /google/oauth/callback
```

El frontend tiene un boton "Conectar Google". La vinculacion manual con `POST /google-connections` queda disponible como modo desarrollo.

V1 completada para automatizacion Gmail:

- conectar varias cuentas
- sincronizar correos recientes
- descargar adjuntos
- registrar `users.watch`
- recibir Pub/Sub
- consultar Gmail history
- aplicar reglas basicas
- crear reglas desde texto con IA
- ver eventos internos

Queda como V2 procesar contenido de adjuntos con OCR/IA y mover procesamiento pesado a workers.

## Pub/Sub con ngrok

Si expones el backend con ngrok, configura la suscripcion push de Pub/Sub con:

```text
https://TU_SUBDOMINIO_NGROK/gmail/pubsub
```

Ejemplo de desarrollo:

```text
https://cc17-152-202-96-51.ngrok-free.app/gmail/pubsub
```

Verifica que el tunel responda:

```text
https://cc17-152-202-96-51.ngrok-free.app/health
```

Despues, desde el frontend, usa el boton de campana en cada cuenta conectada para registrar `users.watch`.

## Validacion

Backend:

```powershell
$env:DATABASE_URL="sqlite"
$env:PYTHONPATH="D:\Users\User\Desktop\desarrollos\email-assitance\backend"
.\backend\.venv\Scripts\python.exe -m compileall .\backend\app
```

Frontend:

```bash
cd frontend
npm run build
```
