# LOG — Bitácora de Sondas, Hipótesis y Decisiones (Reto 2)
> **Evento:** FRONTIER Bogotá 2026 · Reto 2 — La Caja Negra
> **Vista navegable:** [`LOG.html`](LOG.html) · **Especificación:** [`SPEC.md`](SPEC.md) · **Datos crudos:** [`experimentos.jsonl`](experimentos.jsonl)
> **Estado:** 40/40 registros capturados · cada fila cita su `id` en `experimentos.jsonl`

```text
movingparticle@caja-negra:~$ cat ./LOG.txt
[ ok ] 40 registros · 3 grupos · 2 fuentes (baseline público + probing en vivo)
[ ok ] columnas rúbrica: # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión
[ ok ] ninguna fila "por ejecutar": todo lo afirmado tiene evidencia citada
```

---

## 0. Cómo leer este log

Cada línea de `experimentos.jsonl` es un probe real contra el oráculo. Este log los
reproduce **en el orden en que se ejecutaron** y los agrupa por origen:

| Grupo | ids | Fuente | Pregunta que responde |
|---|---|---|---|
| **A · Baseline** | 1–20 | `pruebas/ejemplos.jsonl` (público, mañana) | ¿Cuál es el contrato mínimo observable? |
| **B · Probes en vivo** | 21–34 | probing guiado por hipótesis | ¿Cuáles son los bordes y la precedencia real? |
| **C · Adversarial fuzz** | 35–40 | fuzzing dirigido a límites | ¿Dónde se rompe el modelo y dónde está el tope? |

Convenciones:

- `#N` = `id:N` en `experimentos.jsonl`.
- **Hipótesis antes** = lo que creíamos antes del probe (con su etiqueta `H-0x` cuando aplica).
- **Hipótesis después** = el estado del modelo tras observar el resultado (`confirmada`, `falsada` o `ampliada`).
- **Decisión** = el cambio de código o de regla que se derivó del resultado observado.
- El control de integridad se denota `Q` (byte de control).

---

## 1. Evolución de hipótesis — H-01 → H-04

La investigación no empezó por la fórmula del control: empezó por el dominio. Cada
hipótesis se mantuvo hasta que un probe la **falsó** o la **confirmó**.

| ID | Hipótesis | Estado | Evidencia (ids) | Cómo murió / se confirmó |
|---|---|---|---|---|
| **H-01** | El dominio es bancario y los mensajes son posicionales `CMD;arg;…;Q` con 6 verbos (`PING`,`ALTA`,`CONSULTA`,`DEPOSITO`,`TRANSFER`,`ANULA`). | **confirmada** | #1, #3–#8, #13, #34 | #34 (`RETIRO`) falsó la existencia de verbos extra: el set se cierra en 6. |
| **H-02** | El último campo `Q` es un valor de verificación determinista que se valida **antes** de ejecutar el comando (`E201`/`E202`). | **confirmada** | #2, #17, #20, #29, #30, #31 | #2 y #17 prueban que la validación de `Q` precede a todo efecto; #29/#30 (falta control / segmento vacío) cierran el parser. |
| **H-03** | El algoritmo de `Q` es **ISO 7064 Mod 97-10 alfanumérico 1-based**: `A=1…Z=26` sin padding, `CD = 98 − (N·100) mod 97`, rango `2..98`. | **confirmada** | #3–#6, #10, #39 (+ 16/16 ejemplos) | #31 descarta el padding de ceros; #39 confirma que `(rem·3) mod 97 == 1 ⇒ Q=97`, no `0`. |
| **H-04** | La validación sigue un orden determinista con precedencia **E303 > E304 > E401 > E506 > E507**. | **confirmada** | #26, #27, #28, #9, #16 | #26 (E303>E304), #27 (E304>E506) y #28 (E401>E506) fijan el orden; #16 cierra con E507. |

### Hipótesis rivales descartadas

| Rival | Predicción | Probe discriminante | Resultado | Veredicto |
|---|---|---|---|---|
| Control = Luhn / Módulo 10 | `Q` de 1–2 dígitos con paridad | #3 `ALTA;Lucia;82`, #5 `CONSULTA;AC-0001;14` | no reproduce la serie | **falsada** |
| Control = suma ponderada de caracteres | monótona por longitud | #11 `CONSULTa` (mismo `Q`=14) vs `CONSULTA` | coincide con ISO 7064, no con suma | **falsada** |
| Control = CRC/hash truncado | sin estructura módulo 97 | #39 `…2147483647;97` | `97` válido ⇒ residuo mod 97 | **falsada** |
| El control admite relleno `03` ≈ `3` | comparación numérica laxa | #31 `ALTA;Mateo;03` | `400 E202` | **falsada**: comparación estricta de string |
| `E506` se evalúa antes que la existencia de cuenta | límite primero | #28 `TRANSFER;AC-9999;AC-8888;150000` | `404 E401` | **falsada**: E401 > E506 |
| `E304` se evalúa antes que el monto | cuentas iguales primero | #26 `TRANSFER;AC-0001;AC-0001;0` | `400 E303` | **falsada**: E303 > E304 |

---

## 2. Grupo A · Baseline — registros 1–20

> `pruebas/ejemplos.jsonl` ejecutado tras `POST /__reset`. Fija la paridad observable.

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #1 | `PING;64` | Comando sin argumentos, sin estado | `200 {"pong":true}` | `PING` responde `pong` independiente del estado | confirmada | Implementar `PING → {pong:true}` (aridad 0) |
| #2 | `ALTA;Lucia;83` | Aislar el campo de control | `400 E202 "control inválido"` | control erróneo ⇒ `E202` (H-02) | H-02 confirmada: se valida antes de ejecutar | Validar `Q` antes de cualquier efecto |
| #3 | `ALTA;Lucia;82` | Creación y numeración de cuentas | `201 {"cuentaId":"AC-0001"}` | `ALTA` crea cuenta secuencial (H-01) | H-01 confirmada; saldo inicial 0 | Contador `AC-` desde 1 con padding 4 |
| #4 | `ALTA;Mateo;3` | Secuencia y control de 1 dígito | `201 {"cuentaId":"AC-0002"}` | el contador avanza; `Q` de 1 dígito es válido | confirmada; sin relleno de ceros | Aceptar `Q` sin padding; incrementar secuencia |
| #5 | `CONSULTA;AC-0001;14` | Saldo de cuenta recién creada | `200 {"cuenta_id":"AC-0001","saldo":0}` | `CONSULTA` devuelve `cuenta_id` + saldo numérico | confirmada | `CONSULTA` de solo lectura |
| #6 | `DEPOSITO;AC-0001;250000;86` | Acreditación y `operacionId` | `200 {"status":"recieved","operacionId":"OP-0001"}` | `DEPOSITO` acredita y genera `OP-` | confirmada; typo `recieved` | Replicar `recieved` literal; contador `OP-` |
| #7 | `TRANSFER;AC-0001;AC-0002;40000;86` | Movimiento entre cuentas | `200 {"status":"recieved","operacionId":"OP-0002"}` | `TRANSFER` debita origen y acredita destino | confirmada | Implementar débito/crédito + `OP-` |
| #8 | `CONSULTA;AC-0002;11` | Destino refleja fondos | `200 {"cuenta_id":"AC-0002","saldo":40000}` | saldo acumulativo | confirmada | Estado persistente entre requests |
| #9 | `TRANSFER;AC-0001;AC-0002;120000;55` | Tope de transferencia | `422 E506 "límite excedido"` | existe tope, se evalúa antes del saldo | confirmada: supera tope ⇒ E506 | Tope 100000 → `422 E506` |
| #10 | `TRANSFER;AC-0001;AC-0002;100000;12` | Borde del tope | `200 {"operacionId":"OP-0003"}` | el límite es inclusivo | confirmada | Comparación `monto > 100000` |
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

## 3. Grupo B · Probes en vivo — registros 21–34

> Probing guiado por hipótesis contra el oráculo. Aquí se descubren bordes, precedencia y el algoritmo de control.

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
| #34 | `RETIRO;AC-0001;71` | Verbos bancarios alternativos | `400 E301 "comando desconocido "` | podría existir `RETIRO`/otros | confirmada la negación: set = 6 comandos | No implementar verbos extra |

---

## 4. Grupo C · Adversarial fuzz — registros 35–40

> Fuzzing dirigido a los bordes: tamaño de transporte, formato de monto y el caso `97`.

| # | Probe | Razón | Resultado | Hipótesis antes | Hipótesis después | Decisión |
|---|---|---|---|---|---|---|
| #35 | `PING;[8193 bytes];10` | Exceder el cuerpo HTTP | `413 E101 "cuerpo demasiado grande"` | hay tope de cuerpo ⇒ error estable | confirmada: umbral exacto **8.192 B** | Límite 8 KiB → `413 E101` |
| #36 | `DEPOSITO;AC-0001;0100;79` | Ceros a la izquierda en monto | `400 E303 "monto inválido"` | monto con `0` inicial ⇒ `E303` | confirmada | Monto `^[1-9]\d{0,9}$` |
| #37 | `DEPOSITO;AC-0001;10000000000;22` | Monto de 11 dígitos | `400 E303 "monto inválido"` | existe tope de dígitos | confirmada: máx **10 dígitos** | Validar longitud del monto |
| #38 | `DEPOSITO;AC-0001;9999999999;62` | Monto de 10 dígitos | `200 {"operacionId":"OP-0009"}` | 10 dígitos admitidos sin overflow | confirmada | Enteros seguros hasta 10 dígitos |
| #39 | `DEPOSITO;AC-0002;2147483647;97` | `Q`=97 en ISO 7064 | `200 {"operacionId":"OP-0006"}` | `Q` puede valer 97 | confirmada: rango `2..98`; `(rem·3) mod 97 == 1 ⇒ 97`, **no** `0` | Implementar la fórmula exacta, no `mod` ingenuo |
| #40 | ruta no mapeada (`{}`) | Ruta/método fuera del contrato | `404 E404 "ruta desconocida"` | el router responde antes de auth | confirmada | Despachar `E404` previo al middleware |

---

## 5. Decisiones derivadas (código)

| Decisión | Evidencia | Implementación |
|---|---|---|
| Control = **ISO 7064 Mod 97-10** (A=1…Z=26 sin padding; `CD = 98 − (N·100) mod 97`) | H-03 · #3–#6, #10, #39 | `src/checksum.mjs` |
| Orden de validación estricto `E303 > E304 > E401 > E506 > E507` | H-04 · #26, #27, #28, #9, #16 | `src/engine.mjs` (precedencia) |
| Monto `^[1-9]\d{0,9}$` (positivo, sin ceros iniciales, ≤ 10 dígitos) | #24, #25, #36, #37, #38 | `src/engine.mjs` |
| Transporte: cuerpo ≤ 8.192 B → `413 E101`; ruta desconocida → `404 E404` antes de auth | #35, #40 | `src/security.mjs`, `src/worker.mjs` |
| Comando case-insensitive; IDs de cuenta case-sensitive | #11, #32 | `src/engine.mjs` |
| `ANULA` genérica e idempotente; permite saldo negativo | #13, #14, #23, #33 | `src/engine.mjs` |
| Replicar literales con defectos históricos (`"recieved"`, `"comando desconocido "`) | #6, #12 | `src/engine.mjs` |

## 6. Límites de este log

- El baseline (#1–#20) es una **secuencia con estado**: los saldos citados dependen del orden. Reproducirlo exige `POST /__reset` primero.
- #35 se registra con un payload simbólico (`[8193 bytes]`); el experimento mide el **umbral**, no el contenido.
- El incidente de las 15:30 puede invalidar cualquiera de estas filas; el baseline congelado y su re-test están en [`INCIDENT.md`](INCIDENT.md).

```text
movingparticle@caja-negra:~$ ./probe --verify
40/40 registros citados · 20 baseline · 14 probes · 6 fuzz · 0 pendientes
Hypothesis H-01 → H-04 : CONFIRMED
checksum              : ISO 7064 Mod 97-10
precedence            : E303 > E304 > E401 > E506 > E507
```
