# LOG — Bitácora de Sondas, Hipótesis y Decisiones (Reto 2)
> **Evento:** FRONTIER Bogotá 2026 · Reto 2 — La Caja Negra  
> **Vista navegable:** [`LOG.html`](LOG.html) · **Especificación:** [`SPEC.md`](SPEC.md) · **Incidente:** [`INCIDENT.md`](INCIDENT.md) · **Datos crudos:** [`experimentos.jsonl`](experimentos.jsonl)  
> **Estado:** **44/44 registros capturados · INCIDENTE RESUELTO Y CERRADO (POST-INCIDENTE V2 VERIFICADO AL 100%)**

```text
movingparticle@caja-negra:~$ cat ./LOG.txt
[ ok ] 44 registros · 4 grupos · 2 versiones (V1 Baseline + V2 Post-Incidente)
[ ok ] columnas rúbrica: # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión
[ ok ] INCIDENTE 15:30 RESUELTO: 91/91 casos en verde contra oráculo en producción (0 divergencias)
```

---

## 0. Comparativa: Antes del Incidente (V1) vs Después del Incidente (V2)

El incidente no anunciado de las 15:30 transformó el servicio de la Versión 1 a la Versión 2. A continuación se resume la transición de comportamiento observada y adaptada:

| Dimensión | Antes del Incidente (Versión 1) | Después del Incidente (Versión 2 / Post-Incidente) | Evidencia |
|---|---|---|---|
| **Comando de Parada** | No existía `HALT`. Todos los comandos eran transaccionales a nivel cuenta/operación. | Se introduce `HALT;1` (parada destructiva que retorna `503 E599 "service halted"` persistente) y `HALT;<arg>` sin confirmación (`409 E520`). | Probes #42, #43 |
| **Sugerencias de Error** | `E301` solo retornaba `{"error":"E301","mensaje":"comando desconocido "}`. | `E301` incluye `"sugerencia":"<CMD>"` si el comando está a distancia Levenshtein $\le 2$ de un comando válido. | Probe #41 |
| **Transporte HTTP / CORS** | Preflight `OPTIONS` respondía `204 No Content` con headers CORS. Permisivo con query tokens (`?token=`). | `OPTIONS` responde `404 E404`. No hay soporte CORS. Autenticación estricta: sólo `Bearer <token>` (sin query tokens ni dobles espacios). | Probe #44 |
| **Formato de Saldo** | `CONSULTA` retornaba saldo como entero en centavos (`saldo: 40000`). | `CONSULTA` retorna saldo como string decimal con 2 posiciones (`saldo: "400.00"`). | INC-03 |
| **Límite Transferencia** | Tope de `100000` inclusive. | Tope reducido a `50000` inclusive (`50001` → `422 E506`). | INC-05 |
| **Bloqueo de Cuentas** | Cuentas nunca se bloqueaban por transferencias fallidas. | 3 fallos consecutivos por `E506`/`E507` bloquean la cuenta origen (`423 E510`). Se desbloquea con `DEPOSITO` o `/__reset`. | INC-07, INC-09 |
| **Estado del Servicio** | Servicio siempre disponible en `/msg`. | Estado `halted` bloquea todo `/msg` con `503 E599` consumiendo `X-Req` hasta `POST /__reset`. | Probe #43 |

---

## 1. Cómo leer este log

Cada línea de `experimentos.jsonl` es un probe real contra el oráculo. Este log los
reproduce **en el orden en que se ejecutaron** y los agrupa por fase:

| Grupo | IDs | Fase / Versión | Pregunta que responde |
|---|---|---|---|
| **A · Baseline** | 1–20 | Antes del incidente (V1) | ¿Cuál es el contrato mínimo observable inicial? |
| **B · Probes en vivo** | 21–34 | Antes del incidente (V1) | ¿Cuáles son los bordes y la precedencia real? |
| **C · Adversarial fuzz** | 35–40 | Antes del incidente (V1) | ¿Dónde se rompe el modelo y dónde está el tope inicial? |
| **D · Incidente 15:30** | 41–44 | **Después del incidente (V2)** | **¿Qué cambió en V2 y cómo responde la nueva arquitectura?** |

Convenciones:
- `#N` = `id:N` en `experimentos.jsonl`.
- **Hipótesis antes** = lo que creíamos antes del probe (con su etiqueta `H-0x` cuando aplica).
- **Hipótesis después** = el estado del modelo tras observar el resultado (`confirmada`, `falsada` o `ampliada`).
- **Decisión** = el cambio de código o de regla que se derivó del resultado observado.

---

## 2. Evolución de hipótesis generales

| ID | Hipótesis | Estado | Evidencia (IDs) | Cómo murió / se confirmó |
|---|---|---|---|---|
| **H-01** | El dominio es bancario y los mensajes son posicionales `CMD;arg;…;Q` con 6 verbos iniciales. | **ampliada en V2** | #1, #3–#8, #13, #34, #42 | En V1 se limitaba a 6 verbos; en V2 se incorporó `HALT` (#42, #43). |
| **H-02** | El último campo `Q` es un valor de verificación determinista que se valida **antes** de ejecutar el comando (`E201`/`E202`). | **confirmada** | #2, #17, #20, #29, #30, #31 | Precede a todo efecto de negocio; se mantiene idéntico en V1 y V2. |
| **H-03** | El algoritmo de `Q` es **ISO 7064 Mod 97-10 alfanumérico 1-based**: `A=1…Z=26` sin padding, `CD = 98 − (N·100) mod 97`, rango `2..98`. | **confirmada** | #3–#6, #10, #39 (+ 16/16 ejemplos) | Algoritmo invariable en V2. |
| **H-04** | La validación sigue un orden determinista con precedencia **E303 > E304 > E401 > E506 > E507**. | **ampliada en V2** | #26, #27, #28, #9, #16, INC-11 | En V2, el bloqueo `E510` se intercala: `E303 > E304 > E401 > E510 > E506 > E507`. |
| **H-05** | En V2, comandos con typos cercanos ofrecen sugerencia (`Levenshtein <= 2`). | **confirmada (V2)** | #41, probe_suggestion | Comandos cercanos devuelven `"sugerencia": "<CMD>"`. |
| **H-06** | En V2, `HALT;1` conmuta a estado persistente de parada (`503 E599`). | **confirmada (V2)** | #42, #43, probe_halt_state | Parada total hasta recepción de `/__reset`. |

---

## 3. Grupo A · Baseline (Antes del Incidente) — registros 1–20

> `pruebas/ejemplos.jsonl` ejecutado tras `POST /__reset`. Fija la paridad observable en V1.

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #1 | `PING;64` | Comando sin argumentos, sin estado | `200 {"pong":true}` | `PING` responde `pong` independiente del estado | confirmada | Implementar `PING → {pong:true}` (aridad 0) |
| #2 | `ALTA;Lucia;83` | Aislar el campo de control | `400 E202 "control inválido"` | control erróneo ⇒ `E202` (H-02) | H-02 confirmada: se valida antes de ejecutar | Validar `Q` antes de cualquier efecto |
| #3 | `ALTA;Lucia;82` | Creación y numeración de cuentas | `201 {"cuentaId":"AC-0001"}` | `ALTA` crea cuenta secuencial (H-01) | H-01 confirmada; saldo inicial 0 | Contador `AC-` desde 1 con padding 4 |
| #4 | `ALTA;Mateo;3` | Secuencia y control de 1 dígito | `201 {"cuentaId":"AC-0002"}` | el contador avanza; `Q` de 1 dígito es válido | confirmada; sin relleno de ceros | Aceptar `Q` sin padding; incrementar secuencia |
| #5 | `CONSULTA;AC-0001;14` | Saldo de cuenta recién creada | `200 {"cuenta_id":"AC-0001","saldo":0}` | `CONSULTA` devuelve `cuenta_id` + saldo | confirmada | `CONSULTA` de solo lectura (en V1 entero) |
| #6 | `DEPOSITO;AC-0001;250000;86` | Acreditación y `operacionId` | `200 {"status":"recieved","operacionId":"OP-0001"}` | `DEPOSITO` acredita y genera `OP-` | confirmada; typo `recieved` | Replicar `recieved` literal; contador `OP-` |
| #7 | `TRANSFER;AC-0001;AC-0002;40000;86` | Movimiento entre cuentas | `200 {"status":"recieved","operacionId":"OP-0002"}` | `TRANSFER` debita origen y acredita destino | confirmada | Implementar débito/crédito + `OP-` |
| #8 | `CONSULTA;AC-0002;11` | Destino refleja fondos | `200 {"cuenta_id":"AC-0002","saldo":40000}` | saldo acumulativo | confirmada | Estado persistente entre requests |
| #9 | `TRANSFER;AC-0001;AC-0002;120000;55` | Tope de transferencia en V1 | `422 E506 "límite excedido"` | existe tope, se evalúa antes del saldo | confirmada: supera tope ⇒ E506 | Tope inicial 100000 → `422 E506` |
| #10 | `TRANSFER;AC-0001;AC-0002;100000;12` | Borde del tope V1 | `200 {"operacionId":"OP-0003"}` | el límite es inclusivo | confirmada | Comparación `monto > 100000` en V1 |
| #11 | `CONSULTa;AC-0001;14` | Sensibilidad a mayúsculas del comando | `200 {"saldo":110000}` | comando case-insensitive | confirmada; mismo `Q`=14 | Normalizar comando a mayúsculas |
| #12 | `SALDOS;AC-0001;38` | Comando inexistente | `400 E301 "comando desconocido "` | comando desconocido ⇒ `E301` | confirmada; espacio final literal | Replicar mensaje exacto (espacio final) |
| #13 | `ANULA;OP-0003;66` | Reversión de operación | `200 {"ok":true,"anulada":"OP-0003"}` | `ANULA` revierte la operación previa | confirmada | Implementar reversión de saldos |
| #14 | `ANULA;OP-0003;66` | Idempotencia de `ANULA` | `200 {"ok":false,"motivo":"ya anulada"}` | repetir no falla con 4xx | confirmada | Marcar `anulada`; 2ª vez `ok:false` |
| #15 | `CONSULTA;AC-0009;87` | Cuenta inexistente | `404 E401 "cuenta inexistente"` | cuenta no registrada ⇒ `E401` | confirmada | `CONSULTA` inexistente → `404 E401` |
| #16 | `TRANSFER;AC-0002;AC-0001;50000;23` | Fondos insuficientes | `422 E507 "saldo insuficiente"` | `saldo < monto` ⇒ `E507` (tras anular OP-0003) | confirmada | Comprobar saldo → `422 E507` |
| #17 | `DEPOSITO;AC-0002;700;5X` | Control no numérico | `400 E201 "control mal formado"` | `Q` no numérico ⇒ `E201` antes del algoritmo | confirmada | Validar formato de `Q` primero |
| #18 | `DEPOSITO;AC-0002;700;35` | Control correcto | `200 {"operacionId":"OP-0004"}` | `Q` numérico válido se ejecuta | confirmada | Acreditar saldo; emitir `OP-` |
| #19 | `CONSULTA;AC-0002;11` | Nuevo saldo tras depósito | `200 {"saldo":40700}` | saldo refleja el último depósito | confirmada | Estado acumulativo (40700) |
| #20 | `ALTA;Lucia;Gomez;11` | Aridad incorrecta | `400 E302 "aridad inválida"` | nº de args ≠ aridad ⇒ `E302` (tras control) | confirmada | Validar aridad después del control |

---

## 4. Grupo B · Probes en vivo (Antes del Incidente) — registros 21–34

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #21 | `ANULA;OP-9999;62` | Operación inexistente | `404 E402 "operación inexistente"` | operación desconocida ⇒ `E402` | confirmada | Añadir `E402` al catálogo |
| #22 | `TRANSFER;AC-0001;AC-0001;500;49` | Origen = destino | `400 E304 "origen y destino iguales"` | origen≠destino es regla dura | confirmada | Comparación de IDs → `E304` |
| #23 | `ANULA;OP-0001;46` | Revertir un `DEPOSITO` | `200 {"ok":true,"anulada":"OP-0001"}` | `ANULA` aplica a depósitos y transferencias | confirmada | Reversión genérica (no solo `TRANSFER`) |
| #24 | `DEPOSITO;AC-0001;0;49` | Monto cero | `400 E303 "monto inválido"` | monto estrictamente positivo | confirmada: `0` ⇒ `E303` | Validar `monto > 0` |
| #25 | `DEPOSITO;AC-0001;abc;47` | Monto no numérico | `400 E303 "monto inválido"` | monto no numérico ⇒ `E303` | confirmada | Validar formato entero |
| #26 | `TRANSFER;AC-0001;AC-0001;0;94` | Monto inválido **+** cuentas iguales | `400 E303 "monto inválido"` | ¿qué error gana? | resuelta: **E303 > E304** | Orden de validación: monto antes de igualdad |
| #27 | `TRANSFER;AC-0001;AC-0001;150000;80` | Cuentas iguales **+** límite | `400 E304 "origen y destino iguales"` | ¿gana el límite? | resuelta: **E304 > E506** | Igualdad antes de límite |
| #28 | `TRANSFER;AC-9999;AC-8888;150000;22` | Cuenta inexistente **+** límite | `404 E401 "cuenta inexistente"` | ¿gana el límite? | resuelta: **E401 > E506** | Existencia antes de límite |
| #29 | `PING` (sin `;`) | Falta el campo de control | `400 E103 "falta control"` | mensaje sin delimitador ⇒ `E103` | confirmada | Parser exige `;` antes de validar `Q` |
| #30 | `;64` | Segmento vacío | `400 E104 "segmento vacío"` | segmento nulo ⇒ `E104` | confirmada | Rechazar cualquier segmento vacío |
| #31 | `ALTA;Mateo;03` | Ceros a la izquierda | `400 E202 "control inválido"` | `03` podría igualar a `3` | **falsada**: comparación estricta de string | No normalizar ceros; rechazar `03` |
| #32 | `CONSULTA;ac-0001;14` | IDs de cuenta en minúsculas | `404 E401 "cuenta inexistente"` | ¿el case-insensitive aplica a IDs? | **falsada**: solo el comando es case-insensitive | Normalizar comando, **no** los IDs de cuenta |
| #33 | `ANULA;OP-0001;46` | Revertir con saldo resultante negativo | `200 {"ok":true,"anulada":"OP-0001"}` | la anulación podría bloquear negativos | **falsada**: se permite saldo negativo | No bloquear anulación por saldo |
| #34 | `RETIRO;AC-0001;71` | Verbos bancarios alternativos | `400 E301 "comando desconocido "` | podría existir `RETIRO`/otros | confirmada la negación: set = 6 comandos en V1 | No implementar verbos extra en V1 |

---

## 5. Grupo C · Adversarial fuzz (Antes del Incidente) — registros 35–40

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #35 | `PING;[8193 bytes];10` | Exceder el cuerpo HTTP | `413 E101 "cuerpo demasiado grande"` | hay tope de cuerpo ⇒ error estable | confirmada: umbral exacto **8.192 B** | Límite 8 KiB → `413 E101` |
| #36 | `DEPOSITO;AC-0001;0100;79` | Ceros a la izquierda en monto | `400 E303 "monto inválido"` | monto con `0` inicial ⇒ `E303` | confirmada | Monto `^[1-9]\d{0,9}$` |
| #37 | `DEPOSITO;AC-0001;10000000000;22` | Monto de 11 dígitos | `400 E303 "monto inválido"` | existe tope de dígitos | confirmada: máx **10 dígitos** | Validar longitud del monto |
| #38 | `DEPOSITO;AC-0001;9999999999;62` | Monto de 10 dígitos | `200 {"operacionId":"OP-0009"}` | 10 dígitos admitidos sin overflow | confirmada | Enteros seguros hasta 10 dígitos |
| #39 | `DEPOSITO;AC-0002;2147483647;97` | `Q`=97 en ISO 7064 | `200 {"operacionId":"OP-0006"}` | `Q` puede valer 97 | confirmada: rango `2..98`; `(rem·3) mod 97 == 1 ⇒ 97`, **no** `0` | Implementar fórmula exacta mod 97 |
| #40 | ruta no mapeada (`{}`) | Ruta/método fuera del contrato | `404 E404 "ruta desconocida"` | el router responde antes de auth | confirmada | Despachar `E404` previo al middleware |

---

## 6. Grupo D · Incidente 15:30 (Después del Incidente — Versión 2) — registros 41–44

> Sondas de resolución y aislamiento de los 3 cambios de la Versión 2.

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #41 | `ALTAX;A;85` | Comando tipográficamente cercano a `ALTA` | `400 E301 {"error":"E301","mensaje":"comando desconocido ","sugerencia":"ALTA"}` | `E301` solo tiene error y mensaje (V1) | **falsada en V2**: V2 añade auto-sugerencias Levenshtein $\le 2$ | Implementar `suggestCommand` en `src/suggest.mjs` y enlazar en `src/engine.mjs` |
| #42 | `HALT;AC-0001;85` | Comando `HALT` con argumento sin confirmar | `409 E520 {"error":"E520","mensaje":"operación destructiva: detiene el servicio; reenvía con confirmación"}` | `HALT` no existe en el catálogo bancario (V1) | **falsada en V2**: existe comando destructivo que exige confirmación | Manejar `HALT` con aridad 1 y `409 E520` si arg $\neq 1$ |
| #43 | `HALT;1;19` | Comando `HALT` confirmado con `"1"` | `503 E599 {"error":"E599","mensaje":"service halted"}` | El servicio nunca deja de procesar mensajes | **falsada en V2**: conmuta a estado detenido persistente | Activar `halted=true`; rechazar subsiguientes `/msg` con `503 E599` consumiendo `X-Req` hasta `POST /__reset` |
| #44 | `OPTIONS /msg` y query tokens | Verificación de transporte HTTP y CORS | `OPTIONS` → `404 E404`; `?token=...` → `401 E001` | `OPTIONS` responde 204 y query tokens autorizan (V1) | **falsada en V2**: V2 cerró CORS preflight y restringió auth estricta | Eliminar preflight CORS 204; rechazar tokens en query o con dobles espacios en header |

---

## 7. Decisiones derivadas de código (Arquitectura Final V2)

| Decisión | Componente | Evidencia |
|---|---|---|
| Algoritmo de sugerencias difusas Levenshtein $\le 2$ con orden determinista | `src/suggest.mjs` | Probe #41, `probe_suggestion.py` |
| Máquina de estados de parada de emergencia (`HALT;1` $\rightarrow$ 503 persistente) | `src/engine.mjs` | Probes #42, #43, `probe_halt_state.py` |
| Formato de saldos decimales (`"X.YY"`) y nuevo límite 50.000 | `src/engine.mjs` | INC-03, INC-05 |
| Bloqueo de cuenta origen `E510` tras 3 fallos consecutivos | `src/engine.mjs` | INC-07, INC-09 |
| Router estricto sin CORS y autenticación estricta `Bearer <token>` | `src/worker.mjs`, `src/server.mjs` | Probe #44, `diff_battery.py` |
| Reset global de negocio y limpieza del estado halted en `POST /__reset` | `src/engine.mjs`, `src/worker.mjs` | Probes #1, #43 |

```text
movingparticle@caja-negra:~$ ./probe --verify
44/44 registros citados · 20 baseline · 14 probes · 6 fuzz · 4 incidente V2 · 0 pendientes
Hypothesis H-01 → H-06 : ALL CONFIRMED & VERIFIED
differential battery   : 91/91 MATCHING · 0 DIVERGENCES
service status         : V2 PARITY 100% OPERATIONAL
```
