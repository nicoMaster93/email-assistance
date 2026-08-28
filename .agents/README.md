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
- Auth: token Bearer propio con roles `super_root`, `root` y `account_user`.
- Usuario bootstrap super root: `master@emailasistance.com`. Se crea en BD por migracion y su clave debe tratarse como credencial sensible.
- Google OAuth: endpoints base implementados en `backend/app/routers/google_oauth.py`.
- Vinculacion de cuentas: OAuth real disponible si hay credenciales; el root puede crear acceso de usuario de cuenta y vincular ahora o despues.
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
- Mantener aislamiento multi-tenant: super root solo administra roots; cada root solo ve sus organizaciones; account_user solo ve su cuenta.
- Filtrar siempre por `organization_id` en recursos multi-tenant.
- No guardar `refresh_token` en texto plano; actualmente se cifra con AES-GCM usando `APP_SECRET`.
- Todo cambio de base de datos debe implementarse como migracion versionada en `backend/app/migrations`.
- No agregar tablas, columnas o indices nuevos directamente en routers/jobs; crea una migracion y registrala en `backend/app/migrations/runner.py`.
- Evitar refactors grandes si no son necesarios para la tarea.
