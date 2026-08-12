# Manual de Usuario

Email Assistance es una aplicacion para centralizar cuentas Gmail, sincronizar solo los correos que cumplen reglas de negocio, revisar adjuntos, recibir avisos por WhatsApp y dar seguimiento a respuestas importantes.

## Roles

### Super root

Usuario administrador de plataforma.

Puede:

- Crear usuarios root.
- Ver el listado de usuarios root.
- Editar su propio perfil.

No trabaja dentro de una organizacion y no ve correos, reglas ni cuentas de los roots.

Acceso inicial:

```text
master@emailasistance.com
123
```

### Root

Usuario administrador de una o varias organizaciones.

Puede:

- Crear y seleccionar organizaciones.
- Crear cuentas Gmail y usuarios de cuenta.
- Vincular cuentas Gmail.
- Crear reglas.
- Sincronizar correos.
- Activar monitor Gmail.
- Configurar WhatsApp.
- Configurar seguimientos.
- Ver eventos, adjuntos y correos sincronizados.

Un root no puede ver organizaciones ni datos de otros roots.

### Usuario de cuenta

Usuario asociado a una sola cuenta Gmail.

Puede:

- Ver su cuenta asignada.
- Vincular o re-vincular Gmail.
- Sincronizar su cuenta.
- Ver correos sincronizados.
- Ver adjuntos.
- Ver reglas asociadas en modo lectura.
- Editar su perfil.

No puede:

- Crear organizaciones.
- Crear, editar o eliminar reglas.
- Configurar WhatsApp.
- Configurar monitor Gmail.
- Configurar seguimientos.
- Ver eventos administrativos.
- Ver otras cuentas.

## Inicio de sesion

1. Ingresa correo y contrasena.
2. Usa el icono de ojo para mostrar u ocultar la contrasena.
3. Presiona `Iniciar sesion`.

Si el token expira, la aplicacion redirige automaticamente al login.

## Panel master

Disponible solo para el super root.

Para crear un usuario root:

1. Ingresa nombre.
2. Ingresa correo.
3. Ingresa contrasena inicial.
4. Presiona `Crear root`.

El nuevo root podra iniciar sesion y crear sus propias organizaciones.

## Organizaciones

Disponible para usuarios root.

Al iniciar sesion:

- Si no tienes organizaciones, aparece `Agregar organizacion`.
- Si ya tienes organizaciones, se muestran como tarjetas.

Puedes:

- Crear una organizacion.
- Seleccionar una organizacion.
- Editar su nombre.
- Eliminarla con confirmacion.

Eliminar una organizacion borra sus cuentas, reglas, correos, adjuntos, seguimientos y eventos.

## Cuentas Gmail

Disponible para usuarios root.

Para crear una cuenta:

1. Presiona `Agregar`.
2. Ingresa `Nombre de la cuenta`.
3. Ingresa `Proposito`.
4. Ingresa el `Usuario` que tendra acceso a esa cuenta.
5. Ingresa una `Contrasena`.
6. Usa una de estas acciones:
   - `Vincular cuenta de Google`: crea el acceso y abre OAuth de Google.
   - `Crear acceso`: crea el usuario para que vincule Gmail despues.

El usuario de acceso puede ser diferente al correo Gmail real que se vincula.

Para editar una cuenta:

1. En el listado de cuentas, presiona el icono de lapiz.
2. Se abre el mismo formulario con datos precargados.
3. Cambia nombre, proposito o usuario de acceso.
4. La contrasena es opcional; si se deja vacia, se conserva.

El correo Gmail real no cambia desde este formulario. Cambia cuando el usuario autoriza Google.

## Vincular Gmail

Root:

- Puede vincular una cuenta al crearla.
- Puede editar una cuenta pendiente y usar `Guardar y vincular`.

Usuario de cuenta:

- Ve el boton `Vincular Gmail` si la cuenta esta pendiente.
- Ve `Re-vincular Gmail` si la cuenta ya esta conectada.

Al presionar el boton:

1. Se abre el flujo de Google.
2. El usuario autoriza permisos de Gmail.
3. La aplicacion vuelve al panel.
4. La cuenta queda conectada con el correo real de Gmail.

## Reglas

Las reglas definen que correos entran a la bandeja.

Un correo solo se guarda si cumple al menos una regla asociada a la cuenta. Si no cumple, se ignora y queda registrado como evento para root.

Root puede:

- Crear reglas.
- Asociarlas a una o varias cuentas.
- Editarlas.
- Eliminarlas.
- Configurar WhatsApp por regla.
- Configurar seguimiento por regla.

Usuario de cuenta puede:

- Ver la pestana `Reglas`.
- Revisar reglas asociadas a su cuenta.

No ve acciones de edicion.

## Crear reglas

En `Nueva regla`, el root puede crear reglas de dos formas:

### Crear con IA

Describe en texto que correos quieres capturar.

Ejemplo:

```text
Detectar nuevos casos de la mesa de ayuda del Portal de Xiarex, pueden o no venir con adjuntos.
```

La IA se usa para razonar si un correo cumple la descripcion cuando se sincroniza o llega desde Pub/Sub.

### Formulario

Permite definir condiciones mas directas:

- Remitente contiene.
- Asunto contiene.
- Requiere adjuntos.

## Sincronizar correos

Root:

- Puede sincronizar desde el listado o desde la cuenta activa.

Usuario de cuenta:

- Puede sincronizar su propia cuenta.

La sincronizacion:

1. Consulta Gmail.
2. Evalua reglas activas asociadas a la cuenta.
3. Guarda solo correos que cumplen.
4. Guarda adjuntos encontrados.
5. Muestra los correos en `Correos recientes`.

Si la cuenta no tiene reglas activas asociadas, no se sincroniza.

## Monitor Gmail

Disponible para root.

El monitor registra `users.watch` de Gmail para recibir avisos por Pub/Sub cuando hay cambios.

Al activar:

1. Selecciona vigencia:
   - 1 semana.
   - 1 mes.
   - 3 meses.
   - 1 ano.
   - Personalizado.
2. El sistema registra el monitor en Google.
3. Un cron renueva automaticamente el watch antes de que expire en Google mientras la vigencia deseada siga activa.

Si el monitor esta activo, puede inactivarse.

## Pub/Sub y eventos

Cuando Gmail dispara Pub/Sub:

1. El backend recibe la notificacion.
2. Consulta Gmail History.
3. Procesa correos nuevos o eliminados.
4. Evalua reglas.
5. Guarda correos aceptados.
6. Registra eventos utiles.

La pestana `Eventos` es visible para root y permite revisar:

- Correos sincronizados.
- Correos descartados.
- Correos eliminados en Gmail.
- Errores importantes.
- Notificaciones enviadas.

## Correos recientes

Muestra los correos sincronizados para la cuenta seleccionada.

Puedes:

- Buscar por asunto, remitente o contenido.
- Filtrar por estado.
- Filtrar por adjuntos.
- Seleccionar un correo para ver detalle.

El detalle muestra:

- Asunto.
- Remitente.
- Cuenta.
- Fecha.
- Regla aplicada.
- Estado.
- Extracto del contenido.
- Adjuntos.

Solo root ve la accion `Dar seguimiento`.

## Adjuntos

Los adjuntos se guardan dentro del backend.

La pestana `Adjuntos` muestra:

- Nombre del archivo.
- Tamano.
- Estado de procesamiento.

Actualmente se listan y almacenan; la previsualizacion avanzada queda para una fase posterior.

## WhatsApp

Disponible para root.

Cada cuenta puede configurar un numero de WhatsApp.

Flujo:

1. Presiona `WhatsApp`.
2. Ingresa el numero.
3. Presiona `Abrir WhatsApp Web`.
4. Se abre un mensaje con codigo hacia el asistente.
5. Cuando el proveedor de WhatsApp llama el webhook, el backend valida el codigo.
6. El numero queda asociado a la cuenta.

Preferencias disponibles:

- Todos.
- Correo nuevo.
- Seguimiento vencido.
- Seguimiento por vencer.
- Contestados tarde.
- Respondidos.

Las notificaciones de correo nuevo tambien requieren que la regla tenga WhatsApp habilitado para esa cuenta.

## Seguimientos

Disponible para root.

Un seguimiento mide si un correo importante fue respondido desde la cuenta Gmail conectada.

Una respuesta valida es:

- Mismo hilo Gmail.
- Mensaje posterior al correo inicial.
- Remitente igual a la cuenta Gmail conectada.

Tipos:

- Seguimiento por regla.
- Seguimiento por cuenta.
- Seguimiento manual desde el detalle del correo.

Estados comunes:

- Pendiente.
- Vencido.
- Respondido.
- Respondido tarde.

## Horario habil

Disponible para root.

El horario habil define cuando corre el tiempo de seguimiento.

Puedes configurar:

- Zona horaria.
- Hora general de inicio y fin.
- Dias habiles.
- Horarios especificos por dia.
- Pais de festivos.

El campo `Pais de festivos` usa codigo ISO de 2 letras.

Ejemplos:

```text
CO
MX
US
```

Si no hay cache local de festivos para ese pais y ano, el backend consulta la API publica configurada y guarda la informacion en base de datos.

## Perfil de usuario

Todos los roles pueden editar su perfil desde el icono junto al correo del usuario.

Puedes cambiar:

- Nombre.
- Correo de acceso.
- Contrasena.

Si dejas la contrasena vacia, se conserva la actual.

## Buenas practicas

- Crea primero reglas antes de sincronizar.
- Usa nombres de cuenta orientados a negocio, como `Mesa de ayuda`, `Facturas` o `Compras`.
- Usa propositos claros para que otros usuarios entiendan la funcion de la cuenta.
- Activa WhatsApp solo en reglas realmente importantes.
- Revisa eventos cuando un correo esperado no aparece en bandeja.
- Configura horario habil antes de activar seguimientos.
