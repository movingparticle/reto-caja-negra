# DESIGN_SYSTEM.md — Documentación visual de `DESIGN_DOC.html`

> Documenta el diseño de la página de System Design (Reto 2 — Caja Negra, FRONTIER Bogotá 2026).
> Enfoque: terminal retro-futurista, ASCII, tipografía grande y UX directa.

---

## 1. Concepto

El reto trata de **observar un sistema opaco y hablar con él**. La metáfora de la interfaz
es una **terminal que se conecta a la caja negra**: el documento entero se presenta como la
sesión de shell de un ingeniero que inspecciona el servicio.

Tres principios:

1. **Todo se ve como evidencia.** Nada es "bonito por decorar"; lo visual imita lo que el
   sistema hace (prompts, retornos, barras de estado, mapas en caracteres).
2. **Lectura rápida + profundidad.** Cada sección abre con un bloque simple y baja a tablas
   técnicas sin cambiar de página.
3. **Una sola fuente, cero build.** Un único HTML autocontenido (solo Mermaid por CDN).

---

## 2. Paleta

| Token | Valor | Uso |
|---|---|---|
| `--bg` | `#070908` | Fondo terminal |
| `--panel` | `#0e1411` | Cajas y tarjetas |
| `--ink` | `#d7f5c8` | Texto principal (verde claro) |
| `--dim` | `#7d9a78` | Texto secundario |
| `--green` | `#39ff14` | Acento primario, fósforo, "OK" |
| `--amber` | `#ffb000` | Acento secundario, advertencia |
| `--cyan` | `#7ee7ff` | Enlaces e info |
| `--red` | `#ff5c57` | Errores y prioridad P0 |
| `--line` | `#1e3a28` | Bordes y separadores |

**Regla:** el verde es lo "vivo/confirmado", el ámbar lo "probable/pendiente", el rojo lo
"roto/crítico", el cian lo "enlace/informativo". El color siempre significa algo.

### Tema alterno ámbar
`body[data-theme="amber"]` redefine los tokens (fósforo ámbar sobre sepia). Se activa con el
botón `theme --amber` y no toca el resto del layout.

---

## 3. Tipografía

| Rol | Fuente | Detalle |
|---|---|---|
| Texto y datos | **IBM Plex Mono** | Monoespaciada, legible a 14.5 px |
| Títulos e impacto | **VT323** | Display pixel/terminal, tamaños hasta 4.2 rem |
| ASCII | IBM Plex Mono | Espaciado fijo, requerido para alinear bloques |

Los `h2` usan VT323 en mayúsculas con `line-height: .9` para el look "rótulo de terminal".
El monoespaciado es obligatorio: sostiene el banner, el mapa de arquitectura y las barras.

---

## 4. Estructura y navegación

- **Barra superior sticky** con:
  - "window chrome" (tres puntos rojo/amarillo/verde) para el frame de terminal;
  - prompt `movingparticle@caja-negra:~/reto-2/DESIGN_DOC`;
  - reloj en vivo (`HH:MM:SS`);
  - botón de tema.
- **Barra de comandos** secundaria: cada sección es un comando (`$ resumen`, `$ datos`…) que
  ancla a su bloque. Son enlaces reales, navegables con teclado.
- **Atajos `1`–`8`**: saltan a cada sección (con scroll suave).
- **Skip link** para accesibilidad.

Secciones: `resumen · datos · problema · arquitectura · decisiones · adr · tests · hipotesis · defensa`.

---

## 5. Bloques de contenido

| Componente | Descripción |
|---|---|
| `.banner` | Arte ASCII `BLACK BOX` en **video inverso**: letras negras sobre panel verde |
| `.box` / `.card` | Cajas de borde fino con encabezado en mayúsculas ámbar |
| `.metrics` | Números gigantes en VT323 (20, 13, 7, 6, 1) con glow |
| `.bars` | Barras de bloque (gradiente repetido que simula `█`), ordenadas |
| `.map` | Diagramas ASCII dentro de cajas (`pre`), con colores por clase |
| `.table-wrap` | Tablas densas con encabezado sticky y hover de fila |
| `.adr` | Tarjetas MADR con badge `ACEPTADA`, contexto/opciones/outcome/cons |
| `.conf`, `.prio` | Etiquetas de confianza y prioridad con color semántico |
| `.note` | Aviso con borde izquierdo ámbar |
| `.qa` | Pregunta/respuesta de defensa con prefijos `?` y `→` |

---

## 6. Elementos ASCII

1. **Banner** `BLACK BOX`: bloques Unicode `██╗` dibujando el nombre en **video inverso**
   (panel verde, letras negras), bajo una **tapa con forma de concha**: domo redondeado con
   borde ondulado `~` que se apoya sobre el cuerpo `+--+ | |` de la caja. Así la "caja negra"
   se lee literalmente como una caja oscura con su tapa de concha dentro del marco verde.
2. **Mapa de arquitectura**: pipeline `EVALUADOR → ENTRYPOINT → ORÁCULO` con caja
   `+---+` y conexión punteada marcada como "solo offline".
3. **Barras de terminal**: resumen `STATUS 200 ███████████`, ordenado por frecuencia.
4. **Prefijos de shell**: `movingparticle@caja-negra:~$`, `> ` en kickers, `$ ` en la nav.

Todo ASCII es **texto plano en `<pre>`**, así que se copia, se imprime y sobrevive sin JS.

---

## 7. Efecto CRT y detalles

- **Scanlines** globales con `repeating-linear-gradient` sobre `body::before` (muy sutil).
- **Cursor parpadeante** `.blink` junto al prompt del hero.
- **Glow** verde en banner, métricas y barra activa (`text-shadow` / `box-shadow`).
- **Arranque de métricas** y hover: transiciones cortas, sin ruido.

---

## 8. Diagramas Mermaid

Se renderizan con tema oscuro propio, alineado a la paleta:

```js
themeVariables: {
  darkMode: true, background: "#070908",
  primaryColor: "#102016", primaryTextColor: "#d7f5c8",
  primaryBorderColor: "#39ff14", lineColor: "#6b8f72",
  textColor: "#d7f5c8"
}
```

Los `classDef` usan los mismos tokens (persona=verde, sistema=cian, externo=ámbar) para que
el diagrama C4 no desentone con la página.

---

## 9. Accesibilidad y responsive

- HTML semántico (`header`, `nav`, `main`, `section`, `footer`, `table`).
- `aria-label` en el banner y la nav; skip link visible al enfocar.
- Foco visible con `outline` punteado verde.
- Grids que colapsan a una columna (`g3`, `g2`, `cons`, `metrics`) en móvil.
- Banner y barras reducen tamaño con `clamp()` / media queries.

---

## 10. Impresión / PDF

`@media print` oculta barra superior, scanlines y ayuda de teclas; fuerza fondo blanco y
texto negro para un PDF legible. El resto del layout se conserva.

---

## 11. Cómo se mantiene

- **Sin build.** Un solo archivo `DESIGN_DOC.html`.
- La única dependencia externa es **Mermaid 11 por CDN** (necesita internet para los C4);
  el resto del documento funciona offline.
- Cambiar el look del terminal = editar solo los **tokens en `:root`**. El tema ámbar lo
  demuestra: no se tocó ningún componente, solo variables.
- El contenido vive separado del estilo: actualizar datos o texto no afecta el diseño.

---

## 12. Archivos relacionados

| Archivo | Rol |
|---|---|
| `DESIGN_DOC.html` | Documento de diseño (esta interfaz) |
| `DESIGN_DOC.md` | Fuente oficial en Markdown (rúbrica) |
| `architecture.mmd` | Diagramas C4 en Mermaid |
| `docs/decisions/` | ADRs en formato MADR 4.0 |
