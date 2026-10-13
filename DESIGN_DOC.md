# SYSTEM DESIGN — Reemplazo Autónomo de Caja Negra
> **Evento:** FRONTIER Bogotá 2026 — Reto 2
> **Entrypoint público:** `https://caja-negra-reemplazo.parsec-ai-labs.workers.dev`
> **Demo interactiva (consola):** [`https://movingparticle.github.io/reto-caja-negra/demo.html`](https://movingparticle.github.io/reto-caja-negra/demo.html) (o [`demo.html`](demo.html)) · **Vista navegable:** [`DESIGN_DOC.html`](DESIGN_DOC.html) · **Arquitectura:** [`architecture.html`](architecture.html) · [`architecture.mmd`](architecture.mmd) · **Decisiones:** [`docs/decisions/`](docs/decisions/README.md)

---

## 1. Objetivo y restricciones (arc42 §1–2)

### 1.1 Objetivo
Reemplazo autónomo, determinista y disponible por internet de un servicio bancario de 10
años sin código ni documentación. Debe replicar con exactitud status HTTP, cuerpos, estados
y errores, **sin llamar al original en runtime**.

### 1.2 Inputs / Outputs
- **Input:** `POST /msg` con `{"m":"CMD;arg;...;control"}` + `Authorization: Bearer`.
- **Output:** status HTTP exacto + cuerpo exacto (`{"error","mensaje"}` en errores).
- **Control:** `GET /health` → `200 {"ok":true}`; `POST /__reset` → `200 {"ok":true}`.

### 1.3 Restricciones explícitas
- Prohibido llamar al original o a otro reemplazo.
- 5 s por paso; 10 req/s y 8.000 req/día por token.
- Repo público sin material privado del organizador.
- Scripts y fuzzers propios permitidos y esperados.

### 1.4 Restricciones implícitas
- Un estado lógico único para el arnés (resuelto con Durable Objects).
- El servicio puede cambiar durante el día (incidente 15:30).
- Sin token o token ajeno ⇒ comportarse como el original (`401 E001`).

---

## 2. Contexto y scope (arc42 §3)

### 2.1 Supuestos (resueltos tras el probing)
- **Máquina de estados determinista:** confirmado.
- **Argumentos posicionales separados por `;`:** confirmado.
- **Control = ISO 7064 Mod 97-10 alfanumérico 1-based:** confirmado (16/16 ejemplos).
- **Estado efímero reiniciable con `__reset`:** confirmado.

### 2.2 Edge cases cubiertos
Cuerpo no-JSON/`E100` · falta `m`/`E102` · falta `;`/`E103` · segmento vacío/`E104` ·
control mal formado/`E201` · control inválido/`E202` (incluye ceros iniciales) ·
comando desconocido/`E301` · aridad/`E302` · monto inválido/`E303` · origen=destino/`E304` ·
cuenta inexistente/`E401` · operación inexistente/`E402` · ruta/`E404` · límite/`E506` ·
saldo/`E507` · cuerpo > 8 KiB/`E101`.

### 2.3 Out-of-scope y por qué
- Persistencia duradera: el contrato pide reset instantáneo, no durabilidad.
- Proxy al original: la regla lo penaliza con 0.
- UI en el runtime: no aporta paridad.

---

## 3. Arquitectura (arc42 §4–7)

El sistema tiene **dos caras del mismo motor** (`src/engine.mjs`):

- **Producción — Cloudflare Worker** (`src/worker.mjs`) con **Durable Object**
  (`BankingDurableObject`) que garantiza **un único estado global** entre instancias.
- **Local — servidor Node** (`src/server.mjs`, `node:http`) para pruebas reproducibles.

```
Evaluador ── HTTPS + Bearer ──► Worker ──(ruta conocida + auth)──► Durable Object
                                                                    └─ BankingEngine
                                                                       ├─ checksum (ISO 7064)
                                                                       └─ estado (cuentas/ops)
Harness (offline) ── probes ──► Oráculo  ──► experimentos.jsonl / SPEC.md
```

### 3.1 Componentes
1. **`src/worker.mjs`** — entrypoint de producción: CORS, ruteo, auth timing-safe, límite
   de cuerpo, Durable Object. `X-Req` incremental por mensaje.
2. **`src/security.mjs`** — comparación de token en tiempo constante, multi-clave,
   headers de seguridad, saneo (bloqueo de `\0` y control chars), límite 8 KiB.
3. **`src/engine.mjs`** — máquina de estados: `accounts`, `operations`, secuencias
   `AC-*`/`OP-*`, validación de monto `^[1-9]\d{0,9}$`, precedencia de errores, reversión
   de `ANULA`.
4. **`src/checksum.mjs`** — algoritmo de control ISO 7064 Mod 97-10.
5. **`src/server.mjs`** — espejo local para tests end-to-end.

### 3.2 Vista de despliegue
Worker + Durable Object con nombre fijo `global-caja-negra` (un solo estado lógico).
Alternativa descartada por el arnés: múltiples instancias sin estado compartido.

---

## 4. Decisiones y trade-offs (MADR)

Detalle en [`docs/decisions/`](docs/decisions/README.md). Resumen:

| ID | Decisión | Descartado | Trade-off |
|---|---|---|---|
| ADR-0001 | Motor Node.js ESM sin dependencias | Fastify/Express + TS | +determinismo, −abstracciones |
| ADR-0002 | Probing guiado por hipótesis | Fuzzing aleatorio masivo | +precisión, −velocidad sintáctica |
| ADR-0003 | Estado en memoria único (Durable Object) | SQLite/Redis clásico | +reset < 1 ms y estado global, −durabilidad clásica |
| ADR-0004 | Adapter para el incidente | Reescribir el motor | +blast radius mínimo, −indirección |
| ADR-0005 | Checksum ISO 7064 Mod 97-10 | Búsqueda offline de 198.000 hipótesis | +paridad exacta, −horas de probing |

---

## 5. Plan de medición y resultados

### 5.1 Baseline y métricas
- **Baseline:** los 20 ejemplos públicos tras `/__reset` ⇒ **20/20 paridad exacta** (test).
- **Suite:** **11/11 tests** (paridad, integridad, adversariales, server, worker).
- **Latencia:** Cloudflare edge; < 5 s por paso (verificado en vivo).

### 5.2 Criterios de éxito
100% en ejemplos conocidos · 0 regresiones · reset aislado · contrato de entrypoint válido ·
comportamiento correcto en errores y precedencia.

### 5.3 Matriz de pruebas (resumen)

| Test | Qué intenta romper | Resultado esperado | Prioridad |
|---|---|---|---|
| Paridad 20/20 | Secuencia pública | Status + body exactos | P0 |
| Integridad | Control válido/inválido/mal formado/faltante/vacío | E201/E202/E103/E104 | P0 |
| Límite de transferencia | 100.000 vs 100.001 | 200 vs 422 E506 | P0 |
| Saldo | saldo = monto − 1 | 422 E507 | P0 |
| Precedencia | monto inválido + cuentas iguales | E303 > E304 > E401 > E506 > E507 | P0 |
| Reversión | `ANULA` con saldo resultante negativo | 200 ok, saldo negativo permitido | P0 |
| Anti-DoS | cuerpo > 8 KiB | 413 E101 | P0 |
| Auth | sin token / token ajeno | 401 E001 | P0 |
| Ruta | `GET /x` | 404 E404 | P0 |

---

## 6. Hipótesis resueltas (evidencia en `SPEC.md` / `experimentos.jsonl`)

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| C1 | `PING` → `{pong:true}` sin estado | ej:1 | confirmado |
| C2 | Comando case-insensitive | ej:11 (CONSULTa) | confirmado |
| C3 | `ALTA` → `AC-####` incremental, saldo 0 | ej:3,4 | confirmado |
| C4 | **Control = ISO 7064 Mod 97-10** | 16/16 ejemplos + probes | confirmado |
| C5 | `DEPOSITO` acredita y devuelve `OP-####` | ej:6,18,19 | confirmado |
| C6 | `TRANSFER` mueve saldo | ej:7,8 | confirmado |
| C7 | Tope 100.000 (`E506`) y saldo (`E507`) | ej:9,16 | confirmado |
| C8 | `ANULA` revierte y es idempotente | ej:13,14 + probes | confirmado |
| C9 | Precedencia de validación completa | probes S-24..S-33 | confirmado |
| C10 | Límites de transporte: 8 KiB, E100/E101/E102/E103/E104 | probes | confirmado |

**Anti-overfitting:** cada regla se falsó contra hipótesis rivales con probes discriminativos;
la fórmula del control se validó contra los 16 casos y bordes (`(rem·3)≡1 → 97`, no 0).

---

## 7. Riesgos y deuda técnica (arc42 §11)
- Estado por proceso: mitigado en producción con Durable Object.
- Concurrencia: la reimplementación no transacciona con bloqueo ACID (no requerido por el contrato).
- Dependencia de la versión del oráculo: baseline congelado + re-test tras cada cambio.
