# Guia Para Agentes

Este proyecto es una V1 de una suite para conectar varias cuentas de correo por usuario/organizacion y procesar adjuntos.

Lee primero:

1. `proyect.md`: idea original y arquitectura deseada.
2. `README.md`: ejecucion general del proyecto.
3. `backend/README.md`: detalles de API, BD y Google.
4. `frontend/README.md`: detalles del cliente React.
5. `.agents/architecture.md`: decisiones actuales.
6. `.agents/roadmap.md`: siguientes mejoras razonables.

## Estado Actual

- Backend: FastAPI.
- Frontend: React + TypeScript + Vite.
- BD: SQLite para desarrollo rapido o Postgres via `DATABASE_URL`.
- Docker Compose: `db`, `backend`, `frontend`.
- Auth: token Bearer propio, simple, para desarrollo.
- Usuario demo: `demo@example.com` / `Demo123!`.
- Google OAuth: endpoints base implementados en `backend/app/routers/google_oauth.py`.
- Vinculacion de cuentas: OAuth real disponible si hay credenciales; simulacion manual mediante `POST /google-connections` para desarrollo.
- Adjuntos: almacenamiento local dentro del backend, no MinIO.

## Comandos Frecuentes

Backend con SQLite:

```powershell
cd backend
.\.venv\Scripts\activate
$env:DATABASE_URL="sqlite"
uvicorn app.main:app --reload --host 127.0.0.1 --port 8000
```

Frontend:

```bash
cd frontend
npm run dev
```

Todo con Docker:

```bash
docker compose up -d --build
```

Validar backend:

```powershell
$env:DATABASE_URL="sqlite"
$env:PYTHONPATH="D:\Users\User\Desktop\desarrollos\email-assitance\backend"
.\backend\.venv\Scripts\python.exe -m compileall .\backend\app
```

Validar frontend:

```bash
cd frontend
npm run build
```

## Reglas de Trabajo

- Mantener la V1 simple.
- No introducir MinIO; los archivos viven en `backend/storage/attachments` o volumen Docker `backend_attachments`.
- No reemplazar la separacion usuario/organizacion/conexion.
- Filtrar siempre por `organization_id` en recursos multi-tenant.
- No guardar `refresh_token` en texto plano; actualmente se cifra con AES-GCM usando `APP_SECRET`.
- Evitar refactors grandes si no son necesarios para la tarea.
