# SYSTEM DESIGN — Reemplazo Autónomo de Caja Negra
> **Evento:** FRONTIER Bogotá 2026 — Reto 2
> **Entrega:** Hito 12:00 (System Design & Arquitectura)
> **Stack:** Node.js (ESM nativo, zero-dependency)
> **Vista navegable:** [`DESIGN_DOC.html`](DESIGN_DOC.html) · **Diagramas:** [`architecture.mmd`](architecture.mmd) · **Decisiones:** [`docs/decisions/`](docs/decisions/README.md)

> Este documento sigue una estructura inspirada en **arc42** y **MADR 4.0**.
> El HTML es la capa de presentación (doble audiencia) y este Markdown la fuente.

---

## 1. Objetivo y restricciones (arc42 §1–2)

### 1.1 Objetivo
Construir un reemplazo autónomo, determinista y disponible por internet para un
servicio legado de 10 años sin código ni documentación. Debe replicar con
exactitud status HTTP, cuerpos, estados y modos de fallo, **sin llamar al
original en runtime**.

### 1.2 Inputs / Outputs
- **Input:** `POST /msg` con `{"m":"CMD;arg;...;ctrl"}` + `Authorization: Bearer`.
- **Output:** status HTTP exacto + cuerpo exacto (JSON o texto).
- **Control:** `GET /health`, `POST /__reset`.

### 1.3 Restricciones explícitas
- Prohibido llamar al original o a otro reemplazo (set = 0 si ocurre).
- 5 s por paso; 10 req/s y 8.000 req/día por token.
- Repo público sin material privado del organizador.
- Fuzzers y scripts propios: permitidos y esperados.

### 1.4 Restricciones implícitas
- Un solo proceso ⇒ estado por instancia.
- El servicio puede cambiar durante el día (incidente 15:30).
- Sin token o con token ajeno ⇒ comportarse como el original.

---

## 2. Contexto y scope (arc42 §3)

### 2.1 Supuestos
- Comportamiento modelable como una máquina de estados determinista.
- Comandos con argumentos posicionales separados por `;`.
- El último campo valida la integridad del mensaje.
- Estado efímero: `POST /__reset` lo vuelve a cero.

### 2.2 Edge cases
Cuerpo vacío/no-JSON · command case-insensitive · aridad inválida (E302) ·
control mal formado (E201) · control inválido (E202) · cuenta inexistente (E401) ·
límite excedido (E506) · saldo insuficiente (E507) · operación ya anulada ·
rutas inexistentes · payload grande · codificación inválida.
*(Los límites exactos de tamaño y la política UTF-8 no están probados: ver S1.)*

### 2.3 Failure modes
Overfitting a los 20 ejemplos · orden de validación erróneo · estado compartido
sin reset · schema change por el incidente · latencia > 5 s.

### 2.4 Out-of-scope y por qué
- Persistencia duradera: el contrato exige reset instantáneo, no durabilidad.
- Proxy al original: prohibido por regla.
- UI en el runtime: no aporta al puntaje de paridad.

---

## 3. Estrategia de solución y arquitectura (arc42 §4–7)

El sistema se divide en dos subsistemas: el **Harness de Descubrimiento**
(offline) y el **Servidor Reemplazo / Entrypoint** (online). Los diagramas C4
completos están en [`architecture.mmd`](architecture.mmd) y renderizados en el HTML.

### 3.1 Componentes del servidor
1. **Router HTTP:** despacha `/health`, `/__reset` y `/msg`; el resto delega al
   *fallback* que replica al original. Valida método y ruta. Los límites de
   payload y la política UTF-8 están **por confirmar** (supuesto S1).
2. **Controles de evaluación:** `/health` (200 sin estado) y `/__reset`
   (exige `Bearer <TEAM_TOKEN>`; con token inválido delega a `/*`).
3. **Motor de dominio (`replica.mjs`):** estados y reglas descubiertas.
4. **Almacén en memoria:** cuentas, saldos y operaciones con snapshot de reset.

### 3.2 Vista de despliegue
Proceso único Node.js expuesto por HTTPS. **Un proceso = un estado**; con
múltiples instancias cada una tendría su propio estado (limitación conocida).

---

## 4. Decisiones y trade-offs (MADR)

Resumen; el detalle está en [`docs/decisions/`](docs/decisions/README.md) y en el HTML.

| ID | Decisión | Descartado | Trade-off |
|---|---|---|---|
| ADR-0001 | Node.js ESM sin dependencias | Fastify/Express + TS | +determinismo, −abstracciones |
| ADR-0002 | Probing guiado por hipótesis | Fuzzing aleatorio masivo | +precisión, −velocidad sintáctica |
| ADR-0003 | Estado en memoria + reset atómico | SQLite/Redis | +velocidad, −durabilidad |
| ADR-0004 | Adapter de normalización | Reescritura del motor | +blast radius mínimo, +indirección |

---

## 5. Plan de medición y verificación

### 5.1 Baseline y métricas
- **Baseline:** reproducir los 20 ejemplos tras `/__reset` ⇒ 20/20 de paridad.
- **Métricas:** paridad funcional (status + body), latencia por paso < 5 s,
  reset < 1 ms, casos adversariales superados.

### 5.2 Criterios de éxito
100% en ejemplos conocidos · 0 regresiones tras el incidente · reset idempotente
y aislado · contrato de entrypoint válido.

### 5.3 Matriz de pruebas

| Test | Qué intenta romper | Resultado esperado | Prioridad |
|---|---|---|---|
| Happy path | Flujo PING→ALTA→DEPOSITO→CONSULTA | Status y saldos exactos | P0 |
| Secuencia vacía | Sin mensajes / `/msg` vacío | Mismo error que el original | P0 |
| Comando desconocido | `SALDOS;...` | 400 E301 (case-insensitive) | P0 |
| Aridad inválida | `;` de más o de menos | 400 E302 | P0 |
| Control mal formado | Control no numérico | 400 E201 / E202 | P0 |
| Cuenta inexistente | `CONSULTA;AC-9999` | 404 E401 | P0 |
| Límite excedido | Transferencia sobre umbral | 422 E506 | P1 |
| Saldo insuficiente | Transferir más que el saldo | 422 E507 | P1 |
| Anulación doble | `ANULA` sobre operación anulada | `{ok:false,motivo:"ya anulada"}` | P1 |
| Rutas inexistentes | GET en `/msg`, ruta desconocida | Mismo 404/405 | P1 |
| Payload grande | Payload grande / codificación inválida | Rechazo con código exacto | P1 |
| Reset adversarial | `/__reset` sin token | Comportamiento del original | P0 |
| Regresión del incidente | Caso que cambió a las 15:30 | Adaptado sin romper lo anterior | P0 |

---

## 6. Hipótesis de tests ocultos y confianza

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| C1 | `PING` responde `{pong:true}` sin estado | #1 | confirmado |
| C2 | Comando case-insensitive | #11 (`CONSULTa`) | confirmado |
| C3 | `ALTA` crea cuenta y devuelve `AC-####` incremental | #3, #4 | confirmado |
| C4 | El control se valida antes de actuar | #2, #17 | probable |
| C5 | `DEPOSITO` acredita y devuelve `operacionId` | #6, #18, #19 | confirmado |
| C6 | `TRANSFER` mueve saldo entre cuentas | #7, #8 | confirmado |
| C7 | Límite de transferencia (E506) y saldo (E507) | #9, #16 | confirmado |
| C8 | `ANULA` es idempotente | #13, #14 | confirmado |
| C9 | Comando desconocido ⇒ 400 E301 | #12 | confirmado |
| C10 | Aridad fuera de rango ⇒ 400 E302 | #20 | confirmado |
| H1 | El control es un checksum del payload | #2, #17 | probable |
| H2 | Orden: forma → control → recurso → negocio | #15 vs #9 | probable |
| H3 | IDs por proceso, reinician con reset | #3, #6 | probable |
| S1 | Payload grande / codificación inválida ⇒ error estable | contrato | supuesto |
| S2 | Ruta inexistente ⇒ mismo 404 | contrato | supuesto |

**Anti-overfitting:** por cada regla confirmada se generan probes donde dos
hipótesis rivales predicen resultados distintos; se elige el de mayor ganancia.

---

## 7. Plan de implementación y preguntas abiertas

**P0:** servidor + contrato (`/health`, `/__reset`, `/msg`, `/*`) · motor + store · fuzzer.
**P1:** batería adversarial · incidente 15:30 (detectar → aislar → patch → regresión).
**P2:** README reproducible + video 2 min.

**Preguntas abiertas:** algoritmo del control · umbral del E506 · atomicidad por
mensaje · cambio exacto del incidente · cuerpo del rate-limit.

---

## 8. Riesgos y deuda técnica (arc42 §11)
- Inferencia del control y del orden de validación (mayor riesgo de correctness).
- Estado no compartido entre instancias.
- Dependencia del descubrimiento del oráculo durante la fase offline.
