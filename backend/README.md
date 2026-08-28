# Email Assistance Backend

Backend V1 en FastAPI basado en `proyect.md`.

Incluye:

- Autenticacion con roles de plataforma.
- Login con token Bearer.
- Organizacion demo.
- Vinculacion simulada de varias cuentas Google por organizacion.
- Almacenamiento local de adjuntos en `backend/storage/attachments`.
- SQLite para desarrollo rapido.
- Postgres cuando se define `DATABASE_URL`.
- Inicio de OAuth real de Google y callback.
- Renovacion de access token con `refresh_token`.
- Sincronizacion manual de correos recientes.
- Descarga local de adjuntos detectados durante la sincronizacion.
- Registro de monitor Gmail `users.watch`.
- Webhook Pub/Sub y sincronizacion por Gmail History.
- Reglas basicas y eventos internos.
- Reglas asociadas a cuentas que filtran que correos se guardan.
- Borrador de reglas desde texto usando OpenAI.

## Requisitos

- Python 3.12 o superior.
- Opcional: Postgres local si quieres correr con la misma BD de Docker.

## Variables de entorno

Archivo: `backend/.env`

```text
APP_SECRET=change-this-dev-secret-before-production
FRONTEND_ORIGIN=http://localhost:5173
CORS_ORIGINS=http://localhost:5173
DATABASE_URL=postgresql://email_assistance:email_assistance@localhost:5432/email_assistance
GOOGLE_CLIENT_ID=
GOOGLE_CLIENT_SECRET=
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback
GOOGLE_PUBSUB_TOPIC=
OPENAI_API_KEY=
OPENAI_MODEL=gpt-5.4-mini
WHATSAPP_NUMBER_ASSISTANT=
WHATSAPP_SEND_TEXT_URL=
WHATSAPP_SEND_TEXT_TOKEN=
WHATSAPP_SEND_SESSION=email-assistance
NAGER_DATE_BASE_URL=https://date.nager.at/api/v4/Holidays
```

Para desarrollo sin Postgres, sobrescribe `DATABASE_URL` con:

```powershell
$env:DATABASE_URL="sqlite"
```

## Ejecutar backend por separado con SQLite

```powershell
cd backend
python -m venv .venv
.\.venv\Scripts\activate
pip install -r requirements.txt
$env:DATABASE_URL="sqlite"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

API docs:

```text
http://127.0.0.1:8000/docs
```

## Ejecutar backend por separado con Postgres local

1. Crea una base de datos Postgres:

```sql
CREATE USER email_assistance WITH PASSWORD 'email_assistance';
CREATE DATABASE email_assistance OWNER email_assistance;
```

2. Verifica `backend/.env`:

```text
DATABASE_URL=postgresql://email_assistance:email_assistance@localhost:5432/email_assistance
```

3. Ejecuta:

```powershell
cd backend
.\.venv\Scripts\activate
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Las tablas se crean automaticamente al iniciar.

## Configurar credenciales de Google

En Google Cloud Console:

1. Crea o selecciona un proyecto.
2. Habilita Gmail API.
3. Configura OAuth consent screen.
4. Crea credenciales OAuth Client ID tipo Web application.
5. Agrega este redirect URI para desarrollo:

```text
http://127.0.0.1:8000/google/oauth/callback
```

6. Copia valores al archivo `backend/.env`:

```text
GOOGLE_CLIENT_ID=tu-client-id.apps.googleusercontent.com
GOOGLE_CLIENT_SECRET=tu-client-secret
GOOGLE_REDIRECT_URI=http://127.0.0.1:8000/google/oauth/callback
GOOGLE_PUBSUB_TOPIC=projects/tu-proyecto/topics/tu-topico
```

Estado actual: ya existen estos endpoints OAuth base:

- `GET /google/oauth/start`: requiere Bearer token y devuelve `authorization_url`.
- `GET /google/oauth/callback`: recibe `code` y `state`, intercambia tokens con Google, lee el perfil Gmail y crea/actualiza `google_connections`.

El `refresh_token` se guarda cifrado con AES-GCM usando `APP_SECRET` como base de llave de desarrollo.

V1 implementada:

- registrar `users.watch` de Gmail
- webhook/consumer de Pub/Sub
- sincronizar Gmail history
- descargar adjuntos reales desde Gmail
- registrar eventos internos
- aplicar reglas basicas
- crear borradores de reglas con OpenAI
- asociar numeros WhatsApp a cuentas por codigo de verificacion
- responder mensajes entrantes de WhatsApp desde el backend
- activar notificaciones WhatsApp por regla y por cuenta
- activar seguimiento de respuesta por regla
- evaluar seguimientos pendientes y vencidos por cron
- seguimiento manual por correo y automatico por cuenta
- migraciones versionadas en `backend/app/migrations`

## Configurar WhatsApp

`WHATSAPP_NUMBER_ASSISTANT` es el numero del asistente al que el usuario escribe desde WhatsApp Web.

Para que el backend pueda responder en la misma conversacion, configura:

```text
WHATSAPP_SEND_TEXT_URL=https://tu-servidor-whatsapp/api/sendText
WHATSAPP_SEND_TEXT_TOKEN=
WHATSAPP_SEND_SESSION=email-assistance
```

`WHATSAPP_SEND_TEXT_TOKEN` es opcional. Si tu API no usa Bearer token, dejalo vacio.

El webhook que debe llamar tu proveedor de WhatsApp es:

```text
POST https://tu-backend-publico/whatsapp/webhook
```

El backend acepta el payload completo del proveedor y guarda solo metadatos utiles: numero origen, numero alterno, nombre, id del mensaje, sesion, cuerpo, timestamp y datos de respuesta. Si el numero esta pendiente y el mensaje trae el codigo, se asocia la cuenta. Si el numero ya esta conectado, el asistente responde limitado al contexto de reglas con notificaciones WhatsApp activas. Si el numero es desconocido, se bloquea el flujo y se responde en la conversacion.

## Seguimiento de respuestas

El modulo de seguimientos complementa las reglas existentes. Una regla puede:

- sincronizar correos importantes
- notificar por WhatsApp cuando entra un correo
- crear seguimiento de respuesta para medir si la cuenta conectada respondio el hilo

La respuesta valida para V1 es:

```text
mismo gmail_thread_id
+
mensaje posterior al correo inicial
+
remitente igual a la cuenta Gmail conectada
```

Endpoints principales:

```text
PATCH /automation/rules/{rule_id}/followup
PATCH /google-connections/{connection_id}/followup
GET /followups
GET /followups/summary
POST /followups
POST /followups/evaluate
```

El cron del contenedor ejecuta:

```text
*/10 * * * * python -m app.jobs.evaluate_followups
```

Este job revisa seguimientos `pending` y `overdue`, consulta el hilo en Gmail, marca respuestas y envia WhatsApp cuando un seguimiento vencido tiene esa opcion activada en la regla.

## Migraciones

Todo cambio de base de datos debe vivir en una migracion versionada:

```text
backend/app/migrations
```

El runner se registra en:

```text
backend/app/migrations/runner.py
```

Al iniciar, `init_db()` ejecuta las migraciones pendientes. El usuario super root inicial se crea o promueve en la base de datos desde la migracion `0010_seed_super_root_user`.

Para validar con SQLite:

```powershell
cd backend
$env:DATABASE_URL="sqlite"
.\.venv\Scripts\python.exe -c "from app.db import init_db; init_db(); print('ok')"
```

Regla de trabajo: no agregar tablas, columnas o indices nuevos directamente en routers, jobs o helpers. Primero crear migracion y registrarla en `MIGRATIONS`.

Pendiente V2:

- procesar/extraer contenido de adjuntos
- colas/workers para procesamiento pesado
- OCR/IA y exportaciones

Scopes iniciales recomendados para la V1:

```text
https://www.googleapis.com/auth/gmail.readonly
```

El endpoint `GET /google/oauth/start` ya usa:

```text
access_type=offline
prompt=consent
```

## Usuario super root

El usuario super root administra usuarios root. No trabaja dentro de una organizacion.

El acceso inicial se crea o promueve desde migraciones para que el sistema no dependa de variables de entorno ni usuarios quemados en runtime.

```text
Correo: master@emailasistance.com
Rol: super_root
```

La clave inicial es una credencial sensible definida por la migracion bootstrap. Debe cambiarse desde el perfil despues del primer ingreso.

Cada usuario root puede crear sus propias organizaciones, cuentas, reglas y configuraciones. Un root no ve organizaciones ni datos creados por otros roots.

El super root puede crear, inactivar, activar y eliminar usuarios root. Los usuarios inactivos no pueden iniciar sesion ni usar tokens existentes. La eliminacion borra en cascada las organizaciones y datos asociados del root, incluyendo cuentas, reglas, correos, adjuntos, seguimientos, eventos e integraciones.

## Flujo rapido

Login:

```bash
curl -X POST http://127.0.0.1:8000/auth/login ^
  -H "Content-Type: application/json" ^
  -d "{\"email\":\"admin@tu-dominio.com\",\"password\":\"cambia-esta-clave\"}"
```

Vincular una cuenta:

```bash
curl -X POST http://127.0.0.1:8000/google-connections ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TU_TOKEN" ^
  -d "{\"email\":\"facturas@example.com\",\"scopes\":[\"gmail.readonly\"],\"refresh_token\":\"dev-refresh-token\"}"
```

Iniciar OAuth real:

```bash
curl http://127.0.0.1:8000/google/oauth/start ^
  -H "Authorization: Bearer TU_TOKEN"
```

La respuesta contiene:

```json
{
  "authorization_url": "https://accounts.google.com/o/oauth2/v2/auth?..."
}
```

Listar cuentas:

```bash
curl http://127.0.0.1:8000/google-connections ^
  -H "Authorization: Bearer TU_TOKEN"
```

Sincronizar correos recientes de una conexion:

```bash
curl -X POST "http://127.0.0.1:8000/gmail/connections/1/sync?max_results=10" ^
  -H "Authorization: Bearer TU_TOKEN"
```

La sincronizacion tambien descarga adjuntos encontrados y los registra en `email_attachments`.

Listar correos sincronizados:

```bash
curl http://127.0.0.1:8000/gmail/messages ^
  -H "Authorization: Bearer TU_TOKEN"
```

Crear borrador de regla con IA:

```bash
curl -X POST http://127.0.0.1:8000/automation/rules/draft-from-text ^
  -H "Content-Type: application/json" ^
  -H "Authorization: Bearer TU_TOKEN" ^
  -d "{\"text\":\"Detecta facturas con PDF adjunto\",\"connection_ids\":[1]}"
```

Importante: al sincronizar, solo se guardan correos que coinciden con reglas asociadas a esa cuenta. Si una cuenta no tiene reglas asociadas, los correos se ignoran y solo queda un evento tecnico.

Registrar monitor Gmail:

```bash
curl -X POST http://127.0.0.1:8000/gmail/connections/1/watch ^
  -H "Authorization: Bearer TU_TOKEN"
```

Webhook Pub/Sub:

```text
POST /gmail/pubsub
```

Para una suscripcion push de Pub/Sub usando ngrok:

```text
https://TU_SUBDOMINIO_NGROK/gmail/pubsub
```

Ejemplo:

```text
https://cc17-152-202-96-51.ngrok-free.app/gmail/pubsub
```

Sincronizar desde Gmail History:

```bash
curl -X POST http://127.0.0.1:8000/gmail/connections/1/history-sync ^
  -H "Authorization: Bearer TU_TOKEN"
```

Subir adjunto local:

```bash
curl -X POST http://127.0.0.1:8000/attachments/1 ^
  -H "Authorization: Bearer TU_TOKEN" ^
  -F "file=@factura.pdf"
```

## Docker solo backend

Con Postgres disponible:

```bash
cd backend
docker build -t email-assistance-backend .
docker run --rm -p 8000:8000 --env-file .env email-assistance-backend
```

Si corres este contenedor fuera de Compose, `DATABASE_URL` debe apuntar a un host accesible desde Docker, no necesariamente `localhost`.
