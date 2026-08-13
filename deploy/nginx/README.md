# Nginx — Email Assistance

## Cuantos dominios necesitas

Necesitas **2 subdominios** (o 2 dominios). La base de datos no se expone.

| Rol | Ejemplo provisional | Apunta a |
|---|---|---|
| Frontend (UI) | `email-assistance.xiarex.io` | nginx → `:5173` |
| Backend (API) | `email-assistance-apis.xiarex.io` | nginx → `:8001` |
| Postgres | no dominio publico | solo red Docker |

Un solo dominio con path (`/api`) es posible, pero complica CORS, OAuth de Google y el `FRONTEND_ORIGIN`. Con 2 es el mismo patron que geocarga/siacomex en este server.

## Activar (HTTP, sin SSL)

```bash
sudo cp deploy/nginx/email-assistance.conf /etc/nginx/sites-available/email-assistance.xiarex.io
sudo cp deploy/nginx/email-assistance-apis.conf /etc/nginx/sites-available/email-assistance-apis.xiarex.io
sudo ln -sf /etc/nginx/sites-available/email-assistance.xiarex.io /etc/nginx/sites-enabled/
sudo ln -sf /etc/nginx/sites-available/email-assistance-apis.xiarex.io /etc/nginx/sites-enabled/
sudo nginx -t && sudo systemctl reload nginx
```

## Cuando tengas DNS

1. Crea registros A (o CNAME) hacia la IP del server (`159.89.89.5`).
2. Emite certificados:

```bash
sudo certbot --nginx -d email-assistance.xiarex.io -d email-assistance-apis.xiarex.io
```

3. Actualiza `backend/.env`:

```env
FRONTEND_ORIGIN=https://email-assistance.xiarex.io
GOOGLE_REDIRECT_URI=https://email-assistance-apis.xiarex.io/google/oauth/callback
```

4. Actualiza `frontend/.env`:

```env
VITE_API_BASE_URL=https://email-assistance-apis.xiarex.io
```

5. Recrea contenedores para tomar env:

```bash
docker compose up -d --force-recreate backend frontend
```

6. En Google Cloud Console, agrega el redirect URI de HTTPS al OAuth client.

## Si usas otro dominio

Cambia `server_name` en ambos `.conf`, vuelve a copiar a `sites-available`, y ajusta los `.env` con el mismo host.
