# Email Assistance Frontend

Frontend inicial en React + TypeScript con Vite.

Incluye:

- Login contra el backend.
- Persistencia simple de sesion en `localStorage`.
- Listado de cuentas vinculadas.
- Formulario para vincular una cuenta de correo en modo desarrollo.
- Boton para iniciar OAuth real de Google.
- Boton para sincronizar correos recientes por cuenta.
- Bandeja simple de correos sincronizados, incluyendo cuenta origen.
- Registro de monitor Gmail por cuenta.
- Reglas basicas, adjuntos guardados y eventos recientes.
- Pestañas por cuenta y filtros por cuenta.
- Generacion de borrador de reglas con IA.
- Accion para desconectar cuentas.

## Requisitos

- Node.js 20 o superior.
- Backend corriendo en `http://127.0.0.1:8000` o la URL definida en `.env`.

## Variables de entorno

Archivo: `frontend/.env`

```text
VITE_API_BASE_URL=http://127.0.0.1:8000
```

Si el backend corre en otro host o puerto, cambia `VITE_API_BASE_URL`.

## Ejecutar por separado

```bash
cd frontend
npm install
npm run dev
```

URL:

```text
http://127.0.0.1:5173
```

## Compilar

```bash
cd frontend
npm run build
```

## Probar con el usuario demo

```text
email: demo@example.com
password: Demo123!
```

## Docker solo frontend

Con el backend ya disponible:

```bash
cd frontend
docker build -t email-assistance-frontend .
docker run --rm -p 5173:5173 --env-file .env email-assistance-frontend
```

## Nota de integracion

El frontend llama estos endpoints:

- `POST /auth/login`
- `GET /google-connections`
- `POST /google-connections`
- `DELETE /google-connections/{id}`
- `GET /google/oauth/start`
- `POST /gmail/connections/{id}/sync`
- `POST /gmail/connections/{id}/watch`
- `GET /gmail/messages`
- `GET /attachments`
- `GET /automation/rules`
- `POST /automation/rules`
- `POST /automation/rules/draft-from-text`
- `DELETE /automation/rules/{id}`
- `GET /automation/events`

Cuando el backend completa el callback de Google, redirige al frontend con uno de estos query params:

```text
?google_connected=correo@gmail.com
?google_error=mensaje
```
