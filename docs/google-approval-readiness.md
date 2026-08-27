# Google Approval Readiness

Este documento resume la preparacion de Email Assistance para verificacion OAuth de Google y revision de scopes de Gmail.

## URLs publicas requeridas

Configurar estas rutas en el dominio HTTPS verificado:

```text
/                  Homepage publica
/privacy-policy    Politica de privacidad
/terms-of-service  Terminos de servicio
/data-deletion     Proceso de eliminacion de datos
/login             Acceso privado al portal
```

La homepage debe estar disponible sin autenticacion y enlazar de forma visible a privacidad, terminos y eliminacion de datos.

## Scope solicitado

```text
https://www.googleapis.com/auth/gmail.readonly
```

Este scope es restringido. Se usa para leer mensajes y adjuntos autorizados por el usuario, sincronizar solo correos que cumplen reglas de negocio, mostrar contexto operativo, guardar adjuntos relevantes, generar eventos y dar seguimiento a respuestas importantes.

## Justificacion sugerida para Google Cloud

```text
Email Assistance solicita el scope https://www.googleapis.com/auth/gmail.readonly para que el usuario pueda conectar cuentas Gmail y sincronizar unicamente los correos que cumplen reglas configuradas por el o por su organizacion. La aplicacion necesita leer asunto, remitente, destinatarios, cuerpo del mensaje y adjuntos para determinar si un correo corresponde a una regla de negocio, por ejemplo facturas, tickets de mesa de ayuda, solicitudes criticas o correos que requieren seguimiento.

Scopes mas limitados como https://www.googleapis.com/auth/gmail.metadata no son suficientes porque no permiten acceder al cuerpo del correo ni a los adjuntos. Sin ese acceso, la aplicacion no puede validar reglas basadas en contenido, detectar documentos adjuntos, mostrar contexto operativo ni activar seguimientos o notificaciones al usuario.

Los datos de Gmail se usan exclusivamente para funcionalidades visibles al usuario: sincronizacion filtrada, visualizacion de correos relevantes, gestion de adjuntos, notificaciones configuradas y seguimiento de respuestas. No se venden, no se usan para publicidad y no se usan para entrenar modelos generales o fundacionales.
```

## Eliminacion tecnica de datos

Al desconectar una cuenta Gmail desde el portal se ejecuta:

```text
DELETE /google-connections/{connection_id}/google-data
```

Este proceso:

- Revoca el refresh token de Google cuando es posible.
- Borra tokens almacenados localmente.
- Elimina correos sincronizados.
- Elimina adjuntos registrados y archivos locales.
- Elimina seguimientos, eventos y relaciones asociadas por cascada.

Eliminar una organizacion tambien elimina los registros asociados por cascada y limpia la carpeta local de adjuntos de esa organizacion.

## Configuracion productiva minima

```text
FRONTEND_ORIGIN=https://app.tu-dominio.com
CORS_ORIGINS=https://app.tu-dominio.com
GOOGLE_REDIRECT_URI=https://api.tu-dominio.com/google/oauth/callback
```

En Google Cloud:

- Verificar el dominio en Google Search Console.
- Configurar homepage, politica de privacidad y terminos de servicio.
- Configurar Authorized JavaScript origins con HTTPS.
- Configurar Authorized redirect URIs con HTTPS.
- Declarar el scope `gmail.readonly`.
- Adjuntar video demo del flujo OAuth y uso real.

## Video demo

El video debe mostrar:

- Inicio desde la homepage publica.
- Login al portal.
- Accion de vincular cuenta Google.
- Pantalla OAuth de Google con barra de direccion visible y `client_id`.
- Consentimiento del usuario.
- Retorno al portal.
- Sincronizacion de correo y adjuntos de prueba.
- Visualizacion de regla aplicada, correo procesado y eliminacion/desconexion de datos.
