---
name: responsive-mobile-ux
description: >
  Audita y adapta Email Assistance (y paneles SaaS similares) para que toda la
  aplicacion sea responsive y usable en moviles. Usa cuando el usuario pida
  mobile, responsive, celular, tablet, viewport, touch, hamburger, o cuando
  una pantalla se vea rota, angosta, con scroll horizontal o poco usable en
  pantallas pequenas.
---

# Responsive Mobile UX

Tu rol es el de un UX/UI Senior enfocado en **productividad movil** para
aplicaciones administrativas SaaS (Email Assistance: cuentas, reglas, correos,
modales, tabs, tablas).

Objetivo: la app debe ser **usable con el dedo** en telefono, no solo
“encogerse”. Prioriza lectura, acciones principales y cero scroll horizontal.

Nunca empieces modificando codigo. Primero diagnostica.

---

## Flujo obligatorio

### 1. Diagnosticar

Antes de tocar CSS/JSX:

1. Identifica la pantalla/flujo afectado (login, org picker, master, workspace,
   inbox, modales).
2. Revisa breakpoints existentes en `frontend/src/styles.css`.
3. Detecta:
   - scroll horizontal
   - tablas que no caben
   - botones/iconos < 44px de area tactil
   - grids fijos de muchas columnas
   - modales con `max-width` anulado por especificidad
   - toolbars/topbars que se desbordan
   - texto truncado critico (horas, emails, acciones)
4. Resume en 3–6 bullets: problema → impacto → propuesta.

### 2. Definir breakpoints (proyecto)

Usar estos anchos de forma consistente:

| Token | Ancho | Uso |
|-------|-------|-----|
| `sm` | `≤640px` | Telefono |
| `md` | `≤900px` | Tablet / landscape chico |
| `lg` | `≤1180px` | Laptop estrecho |

Reglas:

- Mobile-first cuando agregues CSS nuevo; si el archivo es desktop-first,
  extiende los `@media` existentes sin duplicar caos.
- En `sm`: una columna, acciones apiladas, tablas convertidas o scrolleables
  con intención.
- En `md`: 2 columnas solo si aportan; modales casi full-width.

### 3. Patrones de adaptacion

#### Layout shell

- `topbar` / `session`: en movil, wrap; email puede truncarse; acciones en fila
  con `gap` y `flex-wrap`.
- `summary-grid` / metricas: 2 cols en `md`, 1 col en `sm`.
- `content-tabs` / `work-tabs`: scroll horizontal con snap suave **o** wrap;
  nunca cortar tabs fuera de pantalla sin acceso.
- `master-layout` / `mail-layout` / paneles split: apilar en columna unica
  debajo de `md`.

#### Tablas (`accounts-table`, eventos, AI usage)

Elegir UNA estrategia por tabla (no mezclar mal):

1. **Card stack (preferida en movil)** — cada fila → tarjeta con labels.
2. **Scroll horizontal contenido** — wrapper `.table-wrap` con
   `overflow-x: auto`, sin romper el viewport de la pagina.
3. **Columnas ocultas** — esconder secundarias; dejar identidad + estado +
   acciones.

Prioridad de columnas visibles en movil: identidad → estado/capabilities →
acciones.

#### Modales

- Ancho: `width/max-width: calc(100vw - 24px)` en `sm`/`md`.
- Evitar que `.modal { max-width: 520px }` gane por orden CSS: usar
  `.modal.nombre-modal` **despues** de `.modal`.
- Formularios densos (horarios, APIs, WhatsApp): settings en 1–2 columnas;
  listas/tablas internas sin overflow de pagina.
- Footer de acciones sticky o al final, botones full-width en `sm`
  (`flex-direction: column-reverse`).

#### Formularios y controles

- Inputs/`select`/`time`: `width: 100%`, `min-width: 0`, `box-sizing: border-box`.
- Area tactil minima ~44×44px para icon-buttons (padding o `min-height`).
- Password toggle y icon-buttons no deben solaparse con el texto.
- Checkboxes + labels: hit area amplia; no depender de texto diminuto.

#### Listas de correos / master-detail

- En movil: lista a pantalla completa; detalle como panel debajo o vista
  enfocada (no dos columnas forzadas).
- Evitar `max-height` de desktop que deje el detalle inutil en telefono.

### 4. Implementar

Orden de cambios:

1. Estructura JSX solo si el layout lo exige (p. ej. labels de tarjeta movil).
2. CSS en `frontend/src/styles.css` (y temas `data-theme` si aplica).
3. No inventar frameworks nuevos; reutilizar clases del proyecto
   (`panel`, `modal`, `table-wrap`, `row-actions`, `filters-bar`).
4. Mantener dark/light themes: cualquier fondo/borde nuevo debe tener
   equivalente en `.app-shell` / `.modal` con variables.

Checklist de implementacion:

```text
- [ ] Sin scroll horizontal en body a 390px y 768px
- [ ] Accion primaria visible sin zoom
- [ ] Modales usables (guardar/cancelar alcanzables)
- [ ] Tabs/navegacion alcanzables
- [ ] Tablas: cards o scroll contenido
- [ ] Touch targets OK
- [ ] No rompe desktop ≥1180px
```

### 5. Verificar

Validar mentalmente (o en browser) anchos:

- `390×844` (telefono)
- `768×1024` (tablet)
- `1280×800` (desktop)

Rebuild frontend Docker si el proyecto corre en contenedor:

```bash
docker compose up -d --build frontend
```

---

## Anti-patrones (prohibido)

- Solo reducir `font-size` para “que quepa”.
- `overflow: hidden` en el viewport para esconder el desborde.
- Grids con `repeat(5+)` sin breakpoint.
- Modales fijos a 520px cuando el contenido es tabla ancha.
- Dependencias nuevas (UI kits) sin pedirlo el usuario.
- Duplicar pantallas “mobile-only” separadas si un layout adaptativo basta.
- Ignorar especificidad CSS (orden de reglas `.modal` vs variantes).

---

## Coordinacion con otras skills

- Si el problema es densidad/jerarquia de dashboard (no solo viewport),
  combina con `dashboard-ux`.
- Esta skill manda cuando el criterio es **movil / responsive / touch**.

---

## Salida esperada al usuario

1. Diagnostico breve (que se rompia).
2. Cambios hechos (pantallas/archivos).
3. Como verificar en telefono o DevTools.

Detalle de breakpoints y ejemplos de CSS: [reference.md](reference.md).
