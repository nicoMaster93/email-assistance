# Reference — Responsive Mobile UX (Email Assistance)

## Archivos clave

- `frontend/src/styles.css` — breakpoints y layouts
- `frontend/src/App.tsx` — shell, tabs, modales, tablas
- Temas: `html[data-theme="..."]` y variables `--color-*`

## Breakpoints actuales (orientativos)

El CSS del proyecto es mayormente desktop-first. Extiende estos bloques:

```css
@media (max-width: 1180px) { /* lg */ }
@media (max-width: 900px)  { /* md */ }
@media (max-width: 860px)  { /* md-ish / whatsapp modal */ }
@media (max-width: 640px)  { /* sm */ }
```

Al agregar reglas nuevas, prefiere engancharte a `900px` y `640px` para no
multiplicar breakpoints.

## Patrones CSS recomendados

### Modal ancho sin pelear con `.modal`

```css
.modal {
  max-width: 520px;
}

.modal.business-hours-modal {
  max-width: min(980px, calc(100vw - 32px));
  width: min(980px, calc(100vw - 32px));
}

@media (max-width: 900px) {
  .modal.business-hours-modal {
    max-width: calc(100vw - 24px);
    width: calc(100vw - 24px);
  }
}
```

### Tabla → evita romper el viewport

```css
.table-wrap {
  overflow-x: auto;
  -webkit-overflow-scrolling: touch;
  max-width: 100%;
}

.accounts-table {
  min-width: 640px; /* solo si usas scroll contenido */
}
```

### Stack de acciones en movil

```css
@media (max-width: 640px) {
  .modal-actions {
    flex-direction: column-reverse;
  }

  .modal-actions button,
  .toolbar-actions button {
    width: 100%;
  }

  .row-actions {
    flex-wrap: wrap;
  }
}
```

### Grid de settings

```css
.business-hours-settings {
  grid-template-columns: minmax(220px, 1.6fr) repeat(2, minmax(130px, 0.9fr)) minmax(110px, 0.7fr);
}

@media (max-width: 900px) {
  .business-hours-settings {
    grid-template-columns: repeat(2, minmax(0, 1fr));
  }
}

@media (max-width: 640px) {
  .business-hours-settings {
    grid-template-columns: 1fr;
  }
}
```

### Inputs que no desbordan

```css
input,
select,
textarea {
  max-width: 100%;
  min-width: 0;
  box-sizing: border-box;
}
```

## Pantallas criticas a cubrir

| Pantalla | Riesgos movil |
|----------|----------------|
| Login | ok compacto; cuidar password toggle |
| Panel master (roots + AI usage) | tabs + tablas + metricas |
| Selector de organizaciones | cards + alertas (no `1fr` que estire mensajes) |
| Workspace topbar | email + botones se desbordan |
| Cuentas (tabla) | muchas acciones por fila |
| Correos (lista + detalle) | split forzado |
| Modales (horario, WhatsApp, API, reglas) | ancho y formularios densos |
| Seguimientos / eventos | filtros + tablas |

## Checklist rapida por PR

- [ ] 390px: sin scroll X en `body`
- [ ] 768px: tabs y topbar usables
- [ ] Modal horario/WhatsApp/API: guardar visible
- [ ] Icon buttons usables con dedo
- [ ] Desktop sin regresion evidente
