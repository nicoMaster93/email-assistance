# Email Assistance Frontend

Frontend inicial en React + TypeScript con Vite.

Incluye:

- Login contra el backend.
- Persistencia simple de sesion en `localStorage`.
- Selector de paleta visual en login, paginas publicas y panel privado.
- Gestion por roles: super root, root y usuario de cuenta.
- Seleccion y gestion de organizaciones para usuarios root.
- Listado de cuentas vinculadas.
- Flujo OAuth real de Google para vincular o re-vincular cuentas.
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

## Acceso inicial

```text
email: master@emailasistance.com
rol: super_root
```

Este usuario permite crear usuarios root. Cada root crea sus propias organizaciones y administra sus cuentas. La clave inicial se define en la migracion bootstrap y debe cambiarse desde el perfil despues del primer ingreso.

En el panel master se pueden crear, activar, inactivar y eliminar usuarios root. La eliminacion solicita confirmacion y borra en cascada las organizaciones y datos asociados del root.

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
