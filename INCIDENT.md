# INCIDENT — Registro del Incidente (15:30)

> **Estado:** RESUELTO · **Detección:** diferencial automatizado · **Regresión:** `tests/parity.test.mjs`
> **Herramientas:** `tools/diff_battery.py`, `tools/probe_incident*.py`, `tools/capture_fixture.py`

---

## 1. What changed

El oráculo cambió su comportamiento en algún momento alrededor de las 15:30. Se observó
comparando la misma secuencia de peticiones contra el oráculo antes y después:

| # | Antes (mañana) | Después (incidente) |
|---|---|---|
| 1 | `CONSULTA` → `{"saldo": 100}` (entero en centavos) | `CONSULTA` → `{"saldo": "1.00"}` (cadena decimal) |
| 2 | `TRANSFER` permitía montos hasta `100000` | `TRANSFER` permite hasta `50000`; `50001` → `422 E506` |
| 3 | No existía bloqueo por fallos | Tras 3 fallos `E506`/`E507` del origen, el siguiente `TRANSFER` → `423 E510 "cuenta bloqueada"` con `intentos` incremental |
| 4 | `OPTIONS /msg` devolvía `204` (réplica) | El oráculo devuelve `404 E404` (no implementa CORS) |
| 5 | Se aceptaba token por `?token=`/`?key=` | El oráculo **rechaza** con `401 E001` (solo `Authorization: Bearer`) |
| 6 | `Bearer  <token>` (doble espacio) se aceptaba | El oráculo rechaza con `401` |

Durante el mismo sondeo se descubrieron además **features completas que no estaban en el
SPEC de la mañana** (existencia previa no confirmada):

- Comando **`HALT`** (aridad 1): `HALT;<x>` → `409 E520` pidiendo confirmación;
  `HALT;1` → detiene el servicio (`503 E599 "service halted"`) hasta `POST /__reset`.
- Campo **`sugerencia`** en `E301` cuando el comando desconocido está a distancia
  Levenshtein ≤ 2 de un comando válido.
- Cabecera `X-Req` **no se resetea** con `__reset` y los contadores `AC-`/`OP-`/`X-Req`
  del oráculo son **globales** (compartidos entre participantes).

## 2. How we detected it

1. `tools/diff_battery.py` ejecuta la misma batería contra el oráculo y el reemplazo y
   reporta la primera divergencia por caso.
2. La primera corrida (`--ignore-xreq`) mostró divergencias de formato de saldo, límite y
   errores nuevos.
3. Se aisló cada comportamiento con sondas dedicadas (`tools/probe_incident*.py`).

## 3. Invalidated assumption

El SPEC de la mañana (`INC-01`) asumió saldos enteros y límite `100000`. Ambas suposiciones
quedaron invalidadas por el incidente.

## 4. Root cause

Cambio intencional del organizador en el servicio de producción (el "incidente de las 15:30"):

- Los montos siguen siendo enteros (centavos), pero la **representación** del saldo pasó a
  cadena decimal con 2 posiciones.
- El límite de transferencia se redujo a `50000`.
- Se añadió una **máquina de bloqueo por cuenta** ante fallos repetidos.

## 5. Affected component

- `src/engine.mjs`: `CONSULTA` (formato), `TRANSFER` (límite + contador de fallos + `E510`),
  comando `HALT`, `E301` con sugerencia.
- `src/worker.mjs` / `src/server.mjs`: enrutado por método+ruta (404 antes de auth),
  autenticación estricta (`Bearer`, sin query), gate del estado `halted`.

## 6. Fix

- `formatSaldo(cents)` → `"X.YY"` (con signo).
- `TRANSFER_LIMIT = 50000`; `MAX_FALLOS = 3`.
- Contador por cuenta origen (`fails`, `blocked`, `intentos`): 3 fallos `E506`/`E507`
  bloquean; siguiente `TRANSFER` → `423 E510 {intentos}`; un `DEPOSITO` exitoso (o `/__reset`)
  desbloquea y resetea.
- Precedencia: `E303 → E304 → E401 → E510 → E506 → E507`.
- `HALT`, `E520`, `E599`, sugerencia en `E301` y strictness de protocolo.

## 7. Regression test

- `tests/parity.test.mjs`: formato decimal, límite 50000, `E510` (bloqueo/intentos),
  precedencia, desbloqueo por depósito, `HALT`/`E520`/`E599`, sugerencia, protocolo.
- `pruebas/ejemplos_post_incidente.jsonl`: fixture de los 20 ejemplos públicos recapturado
  contra el oráculo actual; usado por `engine/server/worker.test.mjs`.

## 8. Trade-off

Se ganó paridad con el oráculo **actual**. Se sacrificó la paridad con el fixture de la
mañana (`pruebas/ejemplos.jsonl`), que se conserva como referencia histórica. Si la
evaluación usara las salidas de la mañana, habría que revertir estos cambios; se decidió
priorizar el comportamiento observado en vivo tras el incidente.

## 9. Final status

- `npm test`: **33/33** en verde.
- Diferencial oráculo vs reemplazo: **89/91** casos idénticos (los 2 restantes difieren solo
  en IDs absolutos `AC-`/`OP-` por el contador **global** del oráculo, no por lógica).
