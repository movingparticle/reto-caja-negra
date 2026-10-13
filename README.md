```text
movingparticle@caja-negra:~$ cat ./SYSTEM_DESIGN.txt

      .~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~~.
    /                                                                           \
  /                                                                               \
 /                                                                                 \
 +---------------------------------------------------------------------------------+
 |                                                                                 |
 |   ██████╗  ██╗       █████╗   ██████╗ ██╗  ██╗    ██████╗   ██████╗  ██╗  ██╗   |
 |   ██╔══██╗ ██║      ██╔══██╗ ██╔════╝ ██║ ██╔╝    ██╔══██╗ ██╔═══██╗ ╚██╗██╔╝   |
 |   ██████╔╝ ██║      ███████║ ██║      █████╔╝     ██████╔╝ ██║   ██║  ╚███╔╝    |
 |   ██╔══██╗ ██║      ██╔══██║ ██║      ██╔═██╗     ██╔══██╗ ██║   ██║  ██╔██╗    |
 |   ██████╔╝ ███████╗ ██║  ██║ ╚██████╗ ██║  ██╗    ██████╔╝ ╚██████╔╝ ██╔╝ ██╗   |
 |   ╚═════╝  ╚══════╝ ╚═╝  ╚═╝  ╚═════╝ ╚═╝  ╚═╝    ╚═════╝   ╚═════╝  ╚═╝  ╚═╝   |
 +---------------------------------------------------------------------------------+
 FRONTIER Bogota 2026 · Reto 2 · hito 12:00
 INPUT --> CAJA --> OUTPUT
```

<p align="center">
  <a href="https://movingparticle.github.io/reto-caja-negra/demo.html" target="_blank" rel="noopener noreferrer"><img alt="Demo interactiva" src="https://img.shields.io/badge/demo-consola%20en%20vivo-00f0ff?style=for-the-badge"></a>
  &nbsp;
  <a href="https://movingparticle.github.io/reto-caja-negra/" target="_blank" rel="noopener noreferrer"><img alt="Abrir design doc" src="https://img.shields.io/badge/design%20doc-abrir%20p%C3%A1gina-39ff14?style=for-the-badge&logo=githubpages&logoColor=07110a"></a>
  &nbsp;
  <a href="https://movingparticle.github.io/reto-caja-negra/architecture.html" target="_blank" rel="noopener noreferrer"><img alt="Arquitectura" src="https://img.shields.io/badge/arquitectura-C4-ffb000?style=for-the-badge"></a>
  &nbsp;
  <a href="https://movingparticle.github.io/reto-caja-negra/en/" target="_blank" rel="noopener noreferrer"><img alt="English" src="https://img.shields.io/badge/EN-english-7ee7ff?style=for-the-badge"></a>
</p>

# Reto 2 · La Caja Negra — Reemplazo autónomo

Reemplazo determinista y **autónomo** de un servicio bancario heredado (10 años en
producción, sin código ni documentación) para **FRONTIER Bogotá 2026**. Reproduce con
paridad exacta el protocolo, los estados, los códigos HTTP y los mensajes de error del
original, incluidos sus errores tipográficos históricos.

- **Demo interactiva (consola en vivo):** <a href="https://movingparticle.github.io/reto-caja-negra/demo.html" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/demo.html</a> (o ruta limpia: <a href="https://movingparticle.github.io/reto-caja-negra/demo/" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/demo/</a>)
- **Design doc (página navegable):** <a href="https://movingparticle.github.io/reto-caja-negra/" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/</a>
- **Arquitectura C4:** <a href="https://movingparticle.github.io/reto-caja-negra/architecture.html" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/architecture.html</a>
- **Bitácora de sondas (LOG):** <a href="https://movingparticle.github.io/reto-caja-negra/LOG.html" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/LOG.html</a>
- **English version:** <a href="https://movingparticle.github.io/reto-caja-negra/en/" target="_blank" rel="noopener noreferrer">https://movingparticle.github.io/reto-caja-negra/en/</a>
- **Entrypoint de producción (Cloudflare Workers):**
  <a href="https://caja-negra-reemplazo.parsec-ai-labs.workers.dev" target="_blank" rel="noopener noreferrer">https://caja-negra-reemplazo.parsec-ai-labs.workers.dev</a> *(Actualmente apagado post-hackathon)*

> ⚠ **Aclaración sobre la demo en vivo:** El entrypoint backend (`caja-negra-reemplazo.parsec-ai-labs.workers.dev`) se encuentra actualmente **apagado / fuera de línea** al haber culminado el hackathon. Por este motivo, al ejecutar la batería de pruebas en la demo interactiva web (`demo.html`), las peticiones reportarán `FAIL` por falta de conexión al worker (`NET_ERR`). Todo el código fuente, la máquina de estados determinista y los tests locales (`npm test`, 34/34 aprobados) se encuentran 100% funcionales y reproducibles en local.

> El reemplazo **no llama** al servicio original ni a otro reemplazo: es 100% autónomo.

---

## 1. Qué resuelve

Un servicio sin código fuente recibe mensajes por HTTP en `POST /msg`. Solo se observa
`INPUT → CAJA → OUTPUT`. El trabajo consiste en **inferir la regla** (no memorizar ejemplos)
y reimplementarla, generalizando a casos no vistos.

**Hallazgos clave (ver `SPEC.md` y `CHALLENGE_ANALYSIS.md`):**

- El campo de control es un **ISO 7064 Mod 97-10 alfanumérico 1-based**
  (`CD = (98 − (N·100)) mod 97`). Verificado en 16/16 ejemplos. Implementado en
  `src/checksum.mjs`.
- Comandos: `PING`, `ALTA`, `CONSULTA`, `DEPOSITO`, `TRANSFER`, `ANULA`, `HALT` (case-insensitive).
  `HALT;1` es destructivo (`503 E599`); `HALT;<otro>` pide confirmación (`409 E520`).
- 20 códigos de error exactos (`E0xx`–`E5xx`) con mensajes literales (incluye el espacio
  final de `"comando desconocido "`, el typo `"recieved"` y `"sugerencia"` opcional en `E301`).
- Precedencia de validación determinada (p. ej. `E303` > `E304` > `E401` > `E506` > `E507`).
- **Incidente (15:30):** el saldo se devuelve como cadena decimal (`"1.00"`), el límite de
  `TRANSFER` es `50000` y 3 fallos `E506`/`E507` de la cuenta origen la bloquean
  (`423 E510`). Ver [`INCIDENT.md`](INCIDENT.md) y `SPEC.md` §8.

---

## 2. Contrato del entrypoint

| Método | Ruta        | Cabecera requerida        | Comportamiento |
| ------ | ----------- | ------------------------- | -------------- |
| `GET`  | `/health`   | `Authorization: Bearer <token>` | `200 {"ok":true}` cuando está listo |
| `POST` | `/__reset`  | `Authorization: Bearer <token>` | Reinicia el estado a cero |
| `POST` | `/msg`      | `Authorization: Bearer <token>` | Cuerpo JSON `{"m":"CMD;arg;...;control"}` |
| `*`    | `/*`        | —                         | `404 {"error":"E404","mensaje":"ruta desconocida"}` |

- Cuerpo de `/msg` limitado a **8 KiB** (mayor → `413 E101`).
- Estado **único global** garantizado con **Cloudflare Durable Objects** (un solo proceso
  lógico, tal como lo asume el arnés de evaluación).
- Autenticación **timing-safe** (comparación byte a byte en tiempo constante).

---

## 3. Inicio rápido (local)

Requisitos: **Node.js ≥ 20** (sin dependencias npm).

```bash
# Servidor local en http://0.0.0.0:3000
npm start

# Batería de tests (paridad + adversariales + worker)
npm test
```

Variables de entorno opcionales: `PORT`, `TEAM_TOKEN`.

---

## 4. Despliegue (Cloudflare Workers)

Configuración nativa con Durable Objects en `wrangler.toml`:

```bash
npx wrangler deploy
```

---

## 5. Estructura del repositorio

```text
reto-caja-negra/
├── index.mjs                 # Entrypoint local (Node) -> src/server.mjs
├── src/
│   ├── checksum.mjs          # ISO 7064 Mod 97-10 (integridad)
│   ├── engine.mjs            # Máquina de estados y reglas de negocio
│   ├── suggest.mjs           # Sugerencia de comando (Levenshtein ≤ 2) para E301
│   ├── security.mjs          # Auth timing-safe, límites, saneo
│   ├── server.mjs            # Servidor HTTP local (node:http)
│   └── worker.mjs            # Cloudflare Worker + Durable Object (producción)
├── tests/                    # parity, engine, server, worker, adversarial, checksum
├── tools/                    # Arnés diferencial y sondas (ver §6)
├── pruebas/ejemplos.jsonl    # 20 casos públicos (versión mañana, histórica)
├── pruebas/ejemplos_post_incidente.jsonl  # 20 casos recapturados tras el incidente
├── experimentos.jsonl        # Log de probes reales (hipótesis -> resultado)
├── SPEC.md                   # Especificación deducida (comportamiento por ID)
├── INCIDENT.md               # Incidencia 15:30: cambio, detección, fix, regresión
├── LOG.md / LOG.html         # Bitácora de sondas: hipótesis antes/después y decisión
├── CHALLENGE_ANALYSIS.md     # Análisis del reto, opciones y matriz de tests
├── TECHNICAL_DEFENSE.md      # Defensa técnica (debrief)
├── DESIGN_DOC.md / .html     # Documento de System Design (hito 12:00)
├── architecture.html         # Diagrama de arquitectura (C4)
├── architecture.mmd          # Diagramas C4 en Mermaid
├── docs/decisions/           # ADRs (MADR 4.0)
├── wrangler.toml             # Config de Cloudflare Workers
└── src / tests / scripts
```

---

## 6. Cómo se verifica

```bash
npm test
```

Cubre, entre otros:

- **Paridad exacta** de los 20 ejemplos recapturados tras el incidente
  (`pruebas/ejemplos_post_incidente.jsonl`).
- **Integridad**: control válido, inválido (`E202`), mal formado (`E201`), faltante (`E103`),
  segmentos vacíos (`E104`), ceros iniciales, controles límite `2`/`98`.
- **Adversariales**: límite 50000, precedencia de errores, reversión de `ANULA`, aridad.
- **Incidente**: saldo decimal, `E510` (bloqueo tras 3 fallos, `intentos`, desbloqueo), `HALT`
  (`409 E520` / `503 E599`), sugerencia en `E301`, protocolo estricto (OPTIONS 404, sin query auth).
- **Worker**: hardening, autenticación multi-clave, límite 8 KiB.

### Arnés diferencial (oráculo vs reemplazo)

```bash
python tools/diff_battery.py --ignore-xreq          # compara contra el oráculo
python tools/diff_battery.py --replica http://127.0.0.1:3000
python tools/capture_fixture.py                     # recaptura el fixture post-incidente
python tools/probe_xreq.py                          # semántica de X-Req
```

`tools/diff_report.json` guarda la transcripción completa por caso.



---

## 7. Documentación

- [`DESIGN_DOC.md`](DESIGN_DOC.md) · [`DESIGN_DOC.html`](DESIGN_DOC.html) — System Design.
- [`SPEC.md`](SPEC.md) — comportamiento inferido con evidencia y nivel de confianza.
- [`LOG.md`](LOG.md) · [`LOG.html`](LOG.html) — bitácora de sondas (hipótesis antes/después, decisión).
- [`experimentos.jsonl`](experimentos.jsonl) — log de experimentos.
- [`docs/decisions/`](docs/decisions/README.md) — decisiones de arquitectura (MADR).
- [`INCIDENT.md`](INCIDENT.md) — registro del incidente.

---

## 8. Limitaciones conocidas

- Estado **por proceso**: el runtime local es de un solo proceso; en producción se garantiza
  un único estado global con un Durable Object con nombre fijo (`global-caja-negra`).
- `ANULA` revierte el efecto de la operación (transferencia o depósito) y **permite saldos
  negativos**, tal como se observó en el oráculo (ver `SPEC.md` §3.6 y §CMD-13).

## 9. Reglas respetadas

- Sin llamadas al original ni a otro reemplazo.
- Scripts y fuzzers propios (permitidos) — ver `scripts/`.
- Repo público sin material privado del organizador.
