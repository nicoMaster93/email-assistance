# Arquitectura Actual

## Backend

Ruta principal: `backend/app`.

Modulos:

- `main.py`: crea la app FastAPI, CORS, startup e incluye routers.
- `config.py`: lee `.env` y define rutas/variables.
- `db.py`: conexion SQLite/Postgres, schema inicial y seed del usuario demo.
- `security.py`: hash de password y token Bearer HMAC simple.
- `dependencies.py`: obtiene usuario actual desde `Authorization: Bearer`.
- `routers/auth.py`: login.
- `routers/google_connections.py`: CRUD basico de cuentas conectadas.
- `routers/google_oauth.py`: inicio/callback OAuth de Google, intercambio de tokens y upsert de conexion.
- `routers/gmail.py`: renovacion de token, sincronizacion manual, descarga de adjuntos, `users.watch`, Pub/Sub, Gmail History y listado de correos.
- `routers/attachments.py`: carga/listado de adjuntos locales.
- `routers/automation.py`: reglas asociadas a cuentas, eventos y borrador de reglas con IA.
- `google_client.py`: helper HTTP para OAuth refresh y Gmail API.
- `openai_client.py`: helper HTTP para generar reglas estructuradas desde texto.
- `schemas.py`: modelos Pydantic.

## Base de Datos

Tablas actuales:

- `users`
- `organizations`
- `organization_members`
- `google_connections`
- `email_messages`
- `email_attachments`
- `automation_rules`
- `rule_connections`
- `system_events`

El modelo importante es:

```text
user -> organization_members -> organization -> google_connections
```

Una cuenta Google pertenece a la organizacion, no directamente a una sesion. Esto permite varias cuentas y prepara el proyecto para multiusuario.

## Frontend

Ruta principal: `frontend/src`.

Modulos:

- `App.tsx`: UI principal, login, listado y vinculacion.
- `services/api.ts`: cliente HTTP del backend.
- `styles.css`: estilos iniciales.
- `vite-env.d.ts`: tipos de Vite.

La UI es deliberadamente simple: una pantalla de login y un panel de cuentas vinculadas.

## Docker

`docker-compose.yml` define:

- `db`: Postgres 17.
- `backend`: FastAPI en puerto `8000`.
- `frontend`: Vite en puerto `5173`.

Volumenes:

- `postgres_data`: datos de Postgres.
- `backend_attachments`: adjuntos locales del backend.

## Variables Importantes

Backend:

```text
APP_SECRET
FRONTEND_ORIGIN
DATABASE_URL
DEMO_USER_EMAIL
DEMO_USER_PASSWORD
DEMO_ORGANIZATION_NAME
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
GOOGLE_PUBSUB_TOPIC
```

Frontend:

```text
VITE_API_BASE_URL
```

## Google OAuth

Estado: base implementada.

Variables preparadas:

```text
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
GOOGLE_PUBSUB_TOPIC
```

Endpoints actuales:

- `GET /google/oauth/start`
- `GET /google/oauth/callback`

El callback intercambia `code` por tokens, lee `users/me/profile` de Gmail y guarda/actualiza `google_connections`.

Pendiente V2:

- procesamiento/extraccion de adjuntos guardados
