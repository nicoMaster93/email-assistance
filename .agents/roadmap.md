# Roadmap Tecnico

## V1 Completada

- OAuth real de Google.
- Cifrado AES-GCM del `refresh_token`.
- Multiples cuentas Google por organizacion.
- Sincronizacion manual de correos recientes.
- Descarga local de adjuntos de Gmail.
- Registro de `users.watch` para Gmail.
- Webhook Pub/Sub.
- Sincronizacion por Gmail History.
- Reglas basicas por remitente, asunto y presencia de adjuntos.
- Reglas asociadas explicitamente a cuentas.
- Sincronizacion filtrada: solo entran correos que cumplen reglas asociadas.
- Borrador de reglas desde texto con OpenAI.
- Eventos internos para seguimiento.
- Vista frontend de cuentas, correos, adjuntos, reglas y eventos.
- Docker Compose con frontend, backend y Postgres.
- Healthcheck de Postgres y backend.
- Migraciones versionadas para cambios de base de datos.
- Seguimiento de respuestas por regla, por cuenta y manual por correo.
- Evaluacion periodica de seguimientos con horario laboral basico.

## V2 Recomendada

- Reemplazar token HMAC casero por JWT formal o sesiones.
- Mover `APP_SECRET` a gestor de secretos.
- Migrar cifrado de refresh tokens a KMS o Vault.
- Fortalecer el runner de migraciones o migrar a Alembic si el proyecto crece en equipo.
- Agregar workers y cola solo cuando el procesamiento de adjuntos sea pesado.
- Procesar adjuntos con OCR, extraccion de texto o IA.
- Crear acciones de reglas: clasificar, extraer, exportar y notificar.
- Agregar pantalla de configuracion de usuarios/roles.
- Agregar pruebas automatizadas unitarias y e2e.
