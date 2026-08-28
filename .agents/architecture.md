# Arquitectura Actual

## Backend

Ruta principal: `backend/app`.

Modulos:

- `main.py`: crea la app FastAPI, CORS, startup e incluye routers.
- `config.py`: lee `.env` y define rutas/variables.
- `db.py`: conexion SQLite/Postgres y compatibilidad de schema base.
- `migrations/`: migraciones versionadas aplicadas al iniciar el backend.
- `security.py`: hash de password y token Bearer HMAC simple.
- `dependencies.py`: obtiene usuario actual desde `Authorization: Bearer`.
- `routers/auth.py`: login.
- `routers/google_connections.py`: CRUD de cuentas conectadas, usuarios de cuenta, WhatsApp y seguimiento por cuenta.
- `routers/google_oauth.py`: inicio/callback OAuth de Google, intercambio de tokens y upsert de conexion.
- `routers/gmail.py`: renovacion de token, sincronizacion manual, descarga de adjuntos, `users.watch`, Pub/Sub, Gmail History y listado de correos.
- `routers/attachments.py`: carga/listado de adjuntos locales.
- `routers/automation.py`: reglas asociadas a cuentas, eventos, integraciones API, seguimiento y borrador de reglas con IA.
- `google_client.py`: helper HTTP para OAuth refresh y Gmail API.
- `openai_client.py`: helper HTTP para generar reglas estructuradas desde texto.
- `schemas.py`: modelos Pydantic.

## Base de Datos

Los cambios de esquema se manejan con migraciones versionadas en:

```text
backend/app/migrations
```

`backend/app/migrations/runner.py` aplica las migraciones pendientes y registra versiones en `schema_migrations`.
No se deben introducir cambios nuevos de BD fuera de este mecanismo.

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
- `email_followups`
- `organization_holidays`
- `rule_api_connections`

El modelo importante es:

```text
super_root -> root users
root user -> organization_members -> organization -> google_connections
account_user -> google_connection asignada
```

Una cuenta Google pertenece a la organizacion y puede tener un usuario de cuenta asociado. El super root no trabaja dentro de organizaciones; solo crea roots. Cada root administra un espacio aislado y no ve datos de otros roots.

## Frontend

Ruta principal: `frontend/src`.

Modulos:

- `App.tsx`: UI principal, login, pagina publica/legal, seleccion de organizaciones, cuentas, reglas, eventos, seguimientos y temas.
- `services/api.ts`: cliente HTTP del backend.
- `styles.css`: estilos de la aplicacion con paletas de tema.
- `vite-env.d.ts`: tipos de Vite.

La UI esta organizada por roles. Super root ve el panel master; root ve organizaciones y administracion completa; account_user ve solo su cuenta, correos, adjuntos y reglas en lectura.

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
GOOGLE_CLIENT_ID
GOOGLE_CLIENT_SECRET
GOOGLE_REDIRECT_URI
GOOGLE_PUBSUB_TOPIC
NAGER_DATE_BASE_URL
OPENAI_API_KEY
WHATSAPP_NUMBER_ASSISTANT
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
