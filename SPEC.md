# SPEC — Especificación del servicio (Caja Negra)

> **Versión:** 0.2.0 (corregida con evidencia directa)
> **Estado:** documento vivo de ingeniería inversa
> **Fuente de evidencia `ej:#N`:** `frontier-reto-2/pruebas/ejemplos.jsonl`, línea `N`
> (20 requests grabados en orden sobre la versión del servicio de la mañana).
> Los `id` de `experimentos.jsonl` se añadirán como segunda fuente cuando exista.

> **Advertencia:** el servicio puede cambiar durante el día. Todo lo marcado como
> `confirmado`/`probable` proviene de la versión de la mañana y debe re-verificarse
> contra la versión vigente a las 20:00.

---

## 0. Transporte y contrato (base del brief)

| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| E-00 | Interfaz HTTP. Negocio en `POST /msg` con cuerpo JSON `{"m": "<comando>"}`. | brief (`frontier-reto-2/README.md:18`) | confirmado |
| E-01 | Autenticación `Authorization: Bearer <token>`; el estado es por token y está aislado entre tokens. | brief (`README.md:12-14,129`) | confirmado |
| E-02 | `GET /health` responde `200` cuando el servicio está listo. Cuerpo exacto del original: por determinar. | brief (`README.md:43`) | confirmado |
| E-03 | `POST /__reset` devuelve el estado del token al inicial. Cuerpo exacto del original: por determinar. | brief (`README.md:44`) | confirmado |
| E-04 | Cualquier otra ruta responde igual que el original, incluidas rutas inexistentes. | brief (`README.md:45`) | confirmado |

## 1. Entrada

Formato del mensaje: `m = "COMANDO;arg1;arg2;...;control"`, campos separados por `;`.

| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| EN-01 | El comando y los argumentos viajan en un único string `m` separado por `;`. | ej:1-20 | confirmado |
| EN-02 | El **último** campo es un número de "control" (integridad). | ej:1,3,17 | confirmado |
| EN-03 | El nombre del comando es **case-insensitive** (`CONSULta` ≡ `CONSULTA`). | ej:11 | confirmado |
| EN-04 | La aridad (número de campos) es fija por comando; una aridad distinta se rechaza. | ej:20 | confirmado |
| EN-05 | El cuerpo es JSON con el campo `m` como string; otros campos no observados. | brief (`README.md:18`) | probable |
| EN-06 | Límite de tamaño del payload, `Content-Type` obligatorio y UTF-8 estricto: **no probado**, se asume un comportamiento por defecto. | — | supuesto |

## 2. Integridad (validación del control)

| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| IN-01 | El control debe ser un entero en formato decimal. Si no lo es → `400` `E201` `"control mal formado"`. | ej:17 (`5X`) | confirmado |
| IN-02 | Si es numérico pero no coincide con el esperado → `400` `E202` `"control inválido"`. | ej:2 (`83`) vs ej:3 (`82`) | confirmado |
| IN-03 | El control esperado es una función determinista del resto del mensaje (dos mensajes iguales en comando/args con control distinto dan distinto resultado). | ej:2,3 | confirmado |
| IN-04 | **Algoritmo del control: no determinado.** Valores válidos observados en el rango 3–87. | ej:1,3-19 | supuesto |
| IN-05 | La validación de control ocurre **antes** de aplicar el efecto de negocio (un control inválido no crea/modifica nada). | ej:2 (no crea cuenta) → ej:3 (`AC-0001`) | probable |
| IN-06 | Orden relativo control (`E20x`) vs aridad (`E302`): no distinguible con los ejemplos. | ej:20 (control válido), ej:2 (aridad válida) | supuesto |

## 3. Comandos

### PING
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-PING-1 | `PING;<control>` → `200` `{"pong":true}`. | ej:1 | confirmado |

### ALTA
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-ALTA-1 | `ALTA;<nombre>;<control>` → `201` `{"cuentaId":"AC-000N"}`. | ej:3,4 | confirmado |
| C-ALTA-2 | Los IDs de cuenta son secuenciales desde `AC-0001`, con 4 dígitos y ceros a la izquierda. | ej:3,4 | confirmado |
| C-ALTA-3 | Un intento fallido (control/aridad) **no** consume ID de cuenta. | ej:2 falla → ej:3 `AC-0001`, ej:4 `AC-0002` | probable |
| C-ALTA-4 | Aridad distinta de `<nombre>`+control → `400` `E302` `"aridad inválida"`. | ej:20 | confirmado |

### CONSULTA
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-CONS-1 | `CONSULTA;<cuentaId>;<control>` → `200` `{"cuenta_id":"AC-XXXX","saldo":N}`. | ej:5,8,11,19 | confirmado |
| C-CONS-2 | Cuenta inexistente → `404` `E401` `"cuenta inexistente"`. | ej:15 | confirmado |
| C-CONS-3 | El saldo de una cuenta recién creada es `0`. | ej:5 | confirmado |

### DEPOSITO
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-DEP-1 | `DEPOSITO;<cuentaId>;<monto>;<control>` → `200` `{"status":"recieved","operacionId":"OP-000N"}`. | ej:6,18 | confirmado |
| C-DEP-2 | El monto se **suma** al saldo de la cuenta. | ej:18 (700) → ej:19 (saldo 40700) | confirmado |
| C-DEP-3 | El literal `"recieved"` (error ortográfico del original) forma parte de la respuesta y debe replicarse exacto. | ej:6,18 | confirmado |
| C-DEP-4 | Los IDs de operación son secuenciales desde `OP-0001`, 4 dígitos. | ej:6,7,10,18 | confirmado |

### TRANSFER
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-TRANS-1 | `TRANSFER;<origen>;<destino>;<monto>;<control>` → `200` `{"status":"recieved","operacionId":"OP-000N"}`. | ej:7,10 | confirmado |
| C-TRANS-2 | Descuenta el monto del origen y lo acredita en el destino de forma atómica. | ej:5-8,11 | confirmado |
| C-TRANS-3 | Monto por encima de un límite → `422` `E506` `"límite excedido"`. | ej:9 (`120000` falla, `100000` ok en ej:10) | probable (límite ≈ 100000) |
| C-TRANS-4 | Saldo insuficiente en origen → `422` `E507` `"saldo insuficiente"`. | ej:16 | confirmado |
| C-TRANS-5 | Una transferencia rechazada no consume ID de operación. | ej:9 falla → ej:10 `OP-0003` | probable |

### ANULA
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-ANULA-1 | `ANULA;<operacionId>;<control>` → `200` `{"ok":true,"anulada":"OP-000N"}` la primera vez. | ej:13 | confirmado |
| C-ANULA-2 | Repetir la anulación de la misma operación → `200` `{"ok":false,"motivo":"ya anulada"}`. | ej:14 | confirmado |
| C-ANULA-3 | Observed: anular una transferencia **no revierte** los saldos (el saldo del destino siguió incluyendo la transferencia anulada). | ej:13 + ej:19 (`AC-0002`=40700) | probable |
| C-ANULA-4 | No se crea un ID de operación nuevo por anular. | ej:13 (no altera la secuencia `OP-*`) | probable |

### Comando desconocido
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| C-UNK-1 | Comando no reconocido → `400` `E301` `"comando desconocido "` (con un espacio final dentro del mensaje). | ej:12 | confirmado |

## 4. Memoria entre requests

| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| M-01 | El servicio mantiene estado de saldos entre requests del mismo token. | ej:5 → ej:8,11,19 | confirmado |
| M-02 | Los contadores de IDs (`AC-*` y `OP-*`) persisten y son monotónicos. | ej:3,4,6,7,10,18 | confirmado |
| M-03 | `POST /__reset` reinicia todo el estado del token a su valor inicial. | brief (`README.md:44`) | confirmado |
| M-04 | El estado está aislado por token. | brief (`README.md:12-14`) | confirmado |
| M-05 | Las operaciones anuladas se recuerdan: un segundo `ANULA` de la misma operación no vuelve a anular. | ej:14 | confirmado |

## 5. Errores

Cuerpo estándar: `{"error":"Exxx","mensaje":"..."}`.

| ID | Código | Status | `mensaje` exacto | Evidencia | Confianza |
|----|--------|-------:|------------------|-----------|-----------|
| ERR-01 | E201 | 400 | `control mal formado` | ej:17 | confirmado |
| ERR-02 | E202 | 400 | `control inválido` | ej:2 | confirmado |
| ERR-03 | E301 | 400 | `comando desconocido ` (espacio final) | ej:12 | confirmado |
| ERR-04 | E302 | 400 | `aridad inválida` | ej:20 | confirmado |
| ERR-05 | E401 | 404 | `cuenta inexistente` | ej:15 | confirmado |
| ERR-06 | E506 | 422 | `límite excedido` | ej:9 | confirmado |
| ERR-07 | E507 | 422 | `saldo insuficiente` | ej:16 | confirmado |

**Orden de evaluación (parcial):**
| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| ORD-01 | El control se valida antes de ejecutar el comando (`E201`/`E202` ganan sobre el efecto). | ej:2,17 | probable |
| ORD-02 | `E301` (comando desconocido) ocurre con un control válido, así que el chequeo de comando es posterior al de control. | ej:12 | probable |
| ORD-03 | Relación completa entre `E201`/`E202`/`E301`/`E302` aún no determinada. | — | supuesto |

## 6. Cambios durante el día

| ID | Comportamiento | Evidencia | Confianza |
|----|----------------|-----------|-----------|
| D-01 | Los 20 ejemplos se grabaron sobre la versión de la mañana; el servicio puede cambiar (existe un incidente planificado ~15:30). | brief (`README.md:16,132`) | confirmado |
| D-02 | Cambio detectado hasta ahora respecto a la versión de la mañana: **ninguno registrado todavía**. | — | supuesto |

## 7. Riesgos

| ID | Riesgo | Por qué un cliente nuevo no debería heredarlo | Mitigación sugerida |
|----|--------|-----------------------------------------------|---------------------|
| R-01 | El campo `control` es un checksum opaco. | Un cliente no puede calcular valores válidos; ata al cliente al algoritmo interno. | Versionar el protocolo y reemplazar por un esquema público (p. ej. firma HMAC documentada). |
| R-02 | Literales con errores/espacios: `"recieved"`, `"comando desconocido "`. | Obliga a replicar errores tipográficos. | Corregir en una versión nueva manteniendo compatibilidad temporal. |
| R-03 | `ANULA` marca pero no revierte saldos. | Contradice la expectativa de reversión; riesgo financiero/lógico. | Documentar semántica real o implementar reversión explícita. |
| R-04 | Límites y rangos no confirmados (`E506`≈100000, aritmética de saldo). | Supuestos no probados pueden romper casos nuevos. | Probar límites exactos antes de fijar la réplica. |
| R-05 | Dependencia de la versión del servicio. | Un cambio de la mañana a la tarde invalida la réplica. | Congelar un baseline y re-ejecutar la suite tras cada cambio. |
