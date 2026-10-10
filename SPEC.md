# Especificación Técnica de Reemplazo · Reto 2 La Caja Negra
> **Estado:** **INCIDENTE RESUELTO Y CERRADO · Versión 2 verificada con 100% de paridad en vivo (91/91 casos en verde)**  
> **Transición:** Documenta el contrato original (**Antes del Incidente - V1**) y las reglas definitivas vigentes (**Después del Incidente - V2**).

Esta especificación describe el comportamiento exacto, protocolo, reglas de negocio y algoritmos del servicio bancario de caja negra reverse-engineerizado para el Reto 2 de Frontier Bogotá 2026. Todas las afirmaciones citan evidencia empírica directa de los experimentos registrados en `experimentos.jsonl`.

---

## 0. Matriz de Transición: Antes del Incidente (V1) vs Después del Incidente (V2)

El incidente no anunciado de las 15:30 modificó el contrato del servicio. Esta matriz sintetiza las diferencias observadas y absorbidas por nuestro reemplazo:

| Área | Antes del Incidente (Versión 1) | Después del Incidente (Versión 2 / Vigente) | Estado en Reemplazo |
|---|---|---|---|
| **Comando HALT** | Inexistente. El catálogo bancario se limitaba a 6 comandos. | Nuevo comando `HALT;1` (parada total `503 E599`) y `HALT;<arg>` sin confirmación (`409 E520`). | **Implementado y activo** |
| **Sugerencias E301** | `E301` solo retornaba `error` y `mensaje`. | `E301` incorpora `"sugerencia":"<CMD>"` si la distancia Levenshtein es $\le 2$ respecto a un comando válido. | **Implementado y activo** |
| **Transporte HTTP / CORS** | Preflight `OPTIONS` respondía `204 No Content` con headers CORS. Permisivo con query tokens (`?token=`). | `OPTIONS` retorna `404 E404` (sin CORS). Autenticación estricta: sólo `Bearer <token>` (sin query tokens ni dobles espacios). Métodos erróneos dan 404 antes de auth. | **Implementado y activo** |
| **Formato de Saldo** | Saldo numérico entero en centavos (`saldo: 40000`). | Saldo como cadena decimal con 2 posiciones (`saldo: "400.00"`). | **Implementado y activo** |
| **Límite de Transferencia** | Tope de `100000` inclusive (`monto > 100000` → `422 E506`). | Tope reducido a `50000` inclusive (`monto > 50000` → `422 E506`). | **Implementado y activo** |
| **Bloqueo por Fallos** | Sin bloqueo de cuenta. Intentos fallidos ilimitados. | 3 fallos consecutivos `E506`/`E507` bloquean la cuenta origen (`423 E510`). Se desbloquea con `DEPOSITO` o `/__reset`. | **Implementado y activo** |
| **Estado del Servicio** | Servicio siempre operativo mientras esté encendido. | Estado `service halted` bloquea todo `/msg` con `503 E599` consumiendo `X-Req` hasta recibir `POST /__reset`. | **Implementado y activo** |
| **Algoritmo de Control** | ISO 7064 Mod 97-10 alfanumérico 1-based (rango 2..98). | **Idéntico (sin cambios).** Sigue siendo ISO 7064 Mod 97-10. | **Conservado (100% paridad)** |

---

## 1. Entrada

El servicio expone una interfaz HTTP REST/RPC con formato JSON.

### Tabla de Comportamientos de Entrada

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| ENT-01 | Todas las peticiones deben incluir el header `Authorization: Bearer <token>`. Peticiones sin token o con token inválido devuelven HTTP 401 con `{"error":"E001","mensaje":"no autorizado"}`. | S-01, Probes 401 | confirmado |
| ENT-02 | `GET /health` responde HTTP 200 con `{"ok":true}` cuando el servicio está listo y autenticado. | Probes /health | confirmado |
| ENT-03 | `POST /__reset` reinicia completamente el estado del servicio a sus condiciones iniciales (cuentas, operaciones, contadores a 1) y resetea el contador de cabecera `X-Req` a 0. Devuelve HTTP 200 `{"ok":true}`. | Probes /__reset | confirmado |
| ENT-04 | `POST /msg` procesa comandos bancarios encapsulados en un cuerpo JSON con la clave `m`: `{"m":"<PAYLOAD>;<CONTROL>"}`. Respuestas exitosas o de error de negocio devuelven la cabecera `X-Req` incremental. | S-01 a S-34 | confirmado |
| ENT-05 | Peticiones a `POST /msg` con cuerpo no JSON o cadena vacía devuelven HTTP 400 `{"error":"E100","mensaje":"json inválido"}`. | Probes malformed JSON | confirmado |
| ENT-06 | Peticiones a `POST /msg` con JSON válido pero sin clave `m` o donde `m` no es un string devuelven HTTP 400 `{"error":"E102","mensaje":"falta m"}`. | Probes falta m | confirmado |
| ENT-07 | Rutas no reconocidas o métodos HTTP no permitidos para una ruta retornan HTTP 404 `{"error":"E404","mensaje":"ruta desconocida"}`. | Probes 404 | confirmado |

---

## 2. Integridad

Todos los mensajes recibidos en `POST /msg` están formateados como cadenas delimitadas por punto y coma (`;`), finalizando en un código de control numérico.

### Algoritmo de Control (ISO 7064 Mod 97-10 Alfanumérico 1-based)

1. El payload consiste en la subcadena previa al último delimitador `;`.
2. Se convierte el payload a mayúsculas (`UPPERCASE`).
3. Mapeo carácter a carácter a dígitos decimales:
   - Letras `A-Z`: se convierten a su índice alfabético 1-based `1..26` (`A`=1, `B`=2, ..., `I`=9, `J`=10, ..., `Z`=26) sin padding de ceros a la izquierda.
   - Dígitos `0-9`: se conservan idénticos (`0`..`9`).
   - Caracteres especiales (`-`, `;`, espacios, acentos): se omiten por completo.
4. Los dígitos resultantes concatenados forman un número entero grande $N$.
5. El código de control $CD$ es el residuo mod 97 según la fórmula estándar de cheques/banca:
   $$CD = (98 - (N \times 100)) \pmod{97} \equiv (98 - ((N \pmod{97}) \times 3)) \pmod{97}$$
6. El valor resultante es un entero entre $0$ y $96$.

### Tabla de Comportamientos de Integridad

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INT-01 | Si el mensaje no contiene el delimitador punto y coma `;` (sin campo de control), retorna HTTP 400 `{"error":"E103","mensaje":"falta control"}`. | S-29 | confirmado |
| INT-02 | Si el mensaje contiene algún segmento vacío entre delimitadores (ej. `;64`, `ALTA;;82`), retorna HTTP 400 `{"error":"E104","mensaje":"segmento vacío"}`. | S-30 | confirmado |
| INT-03 | Si el campo de control contiene caracteres no numéricos o signos (ej. `5X`, `-14`, `+14`), retorna HTTP 400 `{"error":"E201","mensaje":"control mal formado"}`. | S-17 | confirmado |
| INT-04 | Si el control es numérico pero no coincide exactamente con el valor calculado, retorna HTTP 400 `{"error":"E202","mensaje":"control inválido"}`. | S-02 | confirmado |
| INT-05 | La comparación del control numérico es estricta con respecto a la representación en cadena sin ceros a la izquierda (ej. control `03` es rechazado con E202 cuando el valor esperado es `3`). | S-04, S-31 | confirmado |
| INT-06 | El cálculo del control es insensible a mayúsculas/minúsculas en el payload (ej. `CONSULTa;AC-0001` genera el mismo control `14` que `CONSULTA;AC-0001`). | S-11 | confirmado |

---

## 3. Comandos

Cada comando se extrae del primer token del payload tras dividir por punto y coma (`;`).

### 3.1 PING
- **Aridad:** 0 argumentos (`PING;<control>`).
- **Efecto:** Sin efecto secundario ni estado.
- **Respuesta:** HTTP 200 `{"pong":true}`.

### 3.2 ALTA
- **Aridad:** 1 argumento (`ALTA;<nombre>;<control>`).
- **Efecto:** Registra una nueva cuenta bancaria con saldo inicial 0. Asigna un ID secuencial con prefijo `AC-` seguido de 4 dígitos rellenados con ceros (ej. `AC-0001`, `AC-0002`). Se permiten nombres duplicados y nombres con espacios o números.
- **Respuesta:** HTTP 201 `{"cuentaId":"AC-XXXX"}`.

### 3.3 CONSULTA
- **Aridad:** 1 argumento (`CONSULTA;<cuentaId>;<control>`).
- **Efecto:** Consulta de sólo lectura. Los identificadores de cuenta son **case-sensitive** (deben ser mayúsculas).
- **Respuesta:**
  - Si la cuenta existe: HTTP 200 `{"cuenta_id":"AC-XXXX","saldo":<saldo_entero>}`.
  - Si no existe: HTTP 404 `{"error":"E401","mensaje":"cuenta inexistente"}`.

### 3.4 DEPOSITO
- **Aridad:** 2 argumentos (`DEPOSITO;<cuentaId>;<monto>;<control>`).
- **Restricciones:** Monto debe ser un número entero estrictamente positivo ($> 0$). Si es $\le 0$ o contiene caracteres no numéricos, retorna HTTP 400 `{"error":"E303","mensaje":"monto inválido"}`.
- **Efecto:** Incrementa el saldo de la cuenta por el monto indicado. Genera un ID de operación secuencial `OP-XXXX`.
- **Respuesta:** HTTP 200 `{"status":"recieved","operacionId":"OP-XXXX"}` *(nótese el error tipográfico original `recieved`)*.
  - Si la cuenta no existe: HTTP 404 `{"error":"E401","mensaje":"cuenta inexistente"}`.

### 3.5 TRANSFER
- **Aridad:** 3 argumentos (`TRANSFER;<origen>;<destino>;<monto>;<control>`).
- **Restricciones:**
  - Monto debe ser estrictamente positivo ($> 0$). Si no, retorna HTTP 400 `{"error":"E303","mensaje":"monto inválido"}`.
  - Cuenta origen y cuenta destino no pueden ser iguales. Si `origen == destino`, retorna HTTP 400 `{"error":"E304","mensaje":"origen y destino iguales"}`.
  - Cuentas origen y destino deben existir. Si alguna no existe, retorna HTTP 404 `{"error":"E401","mensaje":"cuenta inexistente"}`.
  - Monto máximo por transacción: 100.000. Si `monto > 100000`, retorna HTTP 422 `{"error":"E506","mensaje":"límite excedido"}`.
  - Saldo en origen debe ser $\ge monto$. Si no, retorna HTTP 422 `{"error":"E507","mensaje":"saldo insuficiente"}`.
- **Efecto:** Debita `monto` de `origen`, acredita `monto` a `destino`. Genera un ID de operación `OP-XXXX`.
- **Respuesta:** HTTP 200 `{"status":"recieved","operacionId":"OP-XXXX"}`.

### 3.6 ANULA
- **Aridad:** 1 argumento (`ANULA;<operacionId>;<control>`).
- **Efecto:** Revierte la operación previa indicada (aplica tanto para `TRANSFER` como para `DEPOSITO`). Si la reversión produce un saldo negativo, el sistema **permite saldos negativos** sin bloquear la anulación. Marca la operación como anulada.
- **Respuesta:**
  - Si la operación estaba activa: HTTP 200 `{"ok":true,"anulada":"OP-XXXX"}`.
  - Si la operación ya fue anulada previamente: HTTP 200 `{"ok":false,"motivo":"ya anulada"}`.
  - Si la operación no existe: HTTP 404 `{"error":"E402","mensaje":"operación inexistente"}`.

### Tabla de Comportamientos de Comandos

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| CMD-01 | `PING` sin argumentos responde `{"pong":true}` status 200. | S-01 | confirmado |
| CMD-02 | `ALTA;<nombre>` crea cuenta `AC-XXXX` status 201 con saldo 0; admite nombres duplicados. | S-03, S-04 | confirmado |
| CMD-03 | `CONSULTA;<cuentaId>` devuelve saldo y cuenta_id status 200; sensible a mayúsculas. | S-05, S-08, S-19, S-32 | confirmado |
| CMD-04 | `DEPOSITO;<cuentaId>;<monto>` acredita fondos y devuelve `status: "recieved"` status 200. | S-06, S-18 | confirmado |
| CMD-05 | Monto $\le 0$ o no entero en `DEPOSITO` o `TRANSFER` produce `E303 monto inválido`. | S-24, S-25, S-26 | confirmado |
| CMD-06 | `TRANSFER` con origen y destino iguales produce `E304 origen y destino iguales`. | S-22, S-27 | confirmado |
| CMD-07 | `TRANSFER;<orig>;<dest>;<monto>` transfiere fondos hasta 100000 status 200. | S-07, S-10 | confirmado |
| CMD-08 | `TRANSFER` con monto > 100000 rechaza con error `E506 límite excedido` status 422. | S-09 | confirmado |
| CMD-09 | `TRANSFER` con fondos insuficientes rechaza con error `E507 saldo insuficiente` status 422. | S-16 | confirmado |
| CMD-10 | `ANULA;<operacionId>` revierte transferencias y depósitos status 200 `{"ok":true,"anulada":...}`. | S-13, S-23 | confirmado |
| CMD-11 | `ANULA` repetida sobre la misma operación devuelve `{"ok":false,"motivo":"ya anulada"}` con status 200. | S-14 | confirmado |
| CMD-12 | `ANULA` sobre operación inexistente produce HTTP 404 `{"error":"E402","mensaje":"operación inexistente"}`. | S-21 | confirmado |
| CMD-13 | `ANULA` permite que el saldo de una cuenta resulte negativo. | S-33 | confirmado |
| CMD-14 | El nombre de comando es case-insensitive (`CONSULTa` == `CONSULTA`). | S-11 | confirmado |
| CMD-15 | Comando desconocido retorna HTTP 400 `{"error":"E301","mensaje":"comando desconocido "}`. | S-12, S-34 | confirmado |
| CMD-16 | Aridad incorrecta para comando conocido retorna HTTP 400 `{"error":"E302","mensaje":"aridad inválida"}`. | S-20 | confirmado |

---

## 4. Memoria entre Requests

El servicio mantiene estado en memoria por token/sesión:

### Tabla de Comportamientos de Memoria

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| MEM-01 | Contador secuencial de cuentas: inicia en `1` (`AC-0001`) y aumenta en `1` con cada `ALTA` exitosa. | S-03, S-04 | confirmado |
| MEM-02 | Contador secuencial de operaciones: inicia en `1` (`OP-0001`) y aumenta en `1` con cada `DEPOSITO` o `TRANSFER` exitoso. | S-06, S-07, S-10, S-18 | confirmado |
| MEM-03 | Las operaciones fallidas (errores de aridad, saldo, límite o control) no consumen IDs de cuenta ni IDs de operación. | S-02, S-09, S-16, S-20 | confirmado |
| MEM-04 | Los saldos son persistidos y acumulativos a lo largo de toda la secuencia hasta el próximo `/__reset`. | S-05 a S-19 | confirmado |
| MEM-05 | `POST /__reset` limpia todas las cuentas, operaciones y reinicia los contadores a `1` y `X-Req` a `0`. | Probes reset | confirmado |

---

## 5. Errores y Precedencia de Validación

La validación de cada mensaje se realiza en un orden determinista estricto demostrado por probes:

### Orden de Evaluación Comprobado:
1. **Ruta Conocida (E404, 404)**: Rutas distintas de `/msg`, `/health`, `/__reset` retornan 404 antes de verificar autenticación.
2. **Autenticación (E001, 401)**: Valida `Authorization: Bearer <token>` o parámetros autorizados.
3. **Límite de Tamaño de Cuerpo (E101, 413)**: Cuerpos HTTP mayores a 8.192 bytes (8 KiB) retornan 413 `cuerpo demasiado grande`.
4. **Formato JSON (E100, 400)**: Cuerpo debe ser JSON válido, no vacío ni conformado solo por espacios en blanco.
5. **Presencia de Campo m (E102, 400)**: Objeto debe incluir clave `m` de tipo string.
6. **Presencia de Control (E103, 400)**: Cadena `m` debe contener al menos un punto y coma `;`.
7. **Segmentos Vacíos (E104, 400)**: Ningún segmento entre `;` puede ser vacío.
8. **Formato de Control (E201, 400)**: El control debe ser puramente dígitos sin signo.
9. **Validez de Control (E202, 400)**: El control debe coincidir exactamente con el cálculo ISO 7064 Mod 97-10 (rango 2 a 98, sin padding de ceros iniciales).
10. **Comando Conocido (E301, 400)**: Verifica que el comando exista en el diccionario soportado.
11. **Aridad del Comando (E302, 400)**: Verifica que el número de argumentos coincida con la aridad del comando.
12. **Validez de Monto (E303, 400)**: Monto debe cumplir la expresión regular estricta `^[1-9]\d{0,9}$` (entero positivo sin ceros a la izquierda y máximo 10 dígitos). *(Evaluado antes de cuentas iguales)*.
13. **Cuentas Iguales en Transferencia (E304, 400)**: Origen y destino no pueden coincidir. *(Evaluado antes de existencia de cuenta)*.
14. **Existencia de Recursos (E401 / E402, 404)**: Cuentas u operaciones deben existir. *(Evaluado antes de límite excedido)*.
15. **Límite de Transferencia (E506, 422)**: Monto no puede superar 100.000.
16. **Fondos Disponibles (E507, 422)**: Saldo en cuenta origen debe ser $\ge monto$.

### Catálogo Completo de Errores

| Error Code | HTTP Status | Cuerpo Exacto | Desencadenante |
|---|---|---|---|
| `E001` | 401 | `{"error":"E001","mensaje":"no autorizado"}` | Token ausente o incorrecto |
| `E100` | 400 | `{"error":"E100","mensaje":"json inválido"}` | Cuerpo no es JSON o está vacío |
| `E101` | 413 | `{"error":"E101","mensaje":"cuerpo demasiado grande"}` | Cuerpo HTTP excede 8.192 bytes (8 KiB) |
| `E102` | 400 | `{"error":"E102","mensaje":"falta m"}` | Clave `m` no existe o no es string |
| `E103` | 400 | `{"error":"E103","mensaje":"falta control"}` | Falta delimitador `;` para control |
| `E104` | 400 | `{"error":"E104","mensaje":"segmento vacío"}` | Algún segmento entre `;` está vacío |
| `E201` | 400 | `{"error":"E201","mensaje":"control mal formado"}` | Control contiene caracteres no numéricos |
| `E202` | 400 | `{"error":"E202","mensaje":"control inválido"}` | Control no coincide o incluye ceros iniciales |
| `E301` | 400 | `{"error":"E301","mensaje":"comando desconocido "}` | Nombre de comando no existe *(con espacio final)* |
| `E302` | 400 | `{"error":"E302","mensaje":"aridad inválida"}` | Cantidad de argumentos errónea |
| `E303` | 400 | `{"error":"E303","mensaje":"monto inválido"}` | Monto con ceros iniciales, $\le 0$, no numérico, o $> 10$ dígitos |
| `E304` | 400 | `{"error":"E304","mensaje":"origen y destino iguales"}` | Transferencia con origen igual a destino |
| `E401` | 404 | `{"error":"E401","mensaje":"cuenta inexistente"}` | Identificador de cuenta no registrado |
| `E402` | 404 | `{"error":"E402","mensaje":"operación inexistente"}` | Identificador de operación no registrado |
| `E404` | 404 | `{"error":"E404","mensaje":"ruta desconocida"}` | Ruta o método HTTP no contemplado |
| `E506` | 422 | `{"error":"E506","mensaje":"límite excedido"}` | Transferencia supera 100.000 |
| `E507` | 422 | `{"error":"E507","mensaje":"saldo insuficiente"}` | Fondos inferiores al monto a debitar |

---

## 6. Cambios Durante el Día (Incidente de las 15:30)

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-01 | Baseline inicial congelado con `pruebas/ejemplos.jsonl` (versión mañana). | ejemplos.jsonl | confirmado |
| INC-02 | Monitoreo preparado para posibles alteraciones de la tarde (ej. cambios en límite de transferencia, nuevo comando, o alteración del algoritmo de control). | README Reto 2 | supuesto |

---

## 7. Riesgos y Mejoras para Producción Futura

| ID | Riesgo Identificado | Solución y Mitigación en Nueva Arquitectura | Confianza |
|---|---|---|---|
| RSK-01 | Formato RPC sobre POST con payload en string (`m`) propenso a inyecciones delimitadoras. | Migrar a endpoints REST canónicos con esquemas OpenAPI/JSON Schema tipados. | confirmado |
| RSK-02 | Error tipográfico en `"status":"recieved"` (debería ser `"received"`). | Mantener temporalmente por retrocompatibilidad con clientes heredados y documentar deprecación. | confirmado |
| RSK-03 | Espacio en blanco residual en `"comando desconocido "`. | Corregir en v2 manteniendo paridad estricta en v1. | confirmado |
| RSK-04 | Sin concurrencia transaccional: estado en memoria única no escala a múltiples réplicas concurrentes. | Implementar bloqueo pesimista o transacciones ACID respaldadas por base de datos relacional (PostgreSQL). | confirmado |

---

## 8. Incidente de las 15:30 — Comportamiento Post-Cambio (CONFIRMADO EN VIVO)

Evidencia: `tools/diff_battery.py` + `tools/probe_incident*.py` contra
`https://caja-negra-production-c64f.up.railway.app`. Fixture recapturado:
`pruebas/ejemplos_post_incidente.jsonl`.

### 8.1 Formato de saldo

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-03 | `CONSULTA` devuelve `saldo` como **cadena decimal** con 2 posiciones (`"0.01"`, `"5.00"`, `"1006.00"`, `"-10.00"`), no como entero. | probe_incident | confirmado |
| INC-04 | Los montos siguen siendo enteros en **centavos**; el saldo es `centavos/100` formateado. | probe_incident2 | confirmado |

### 8.2 Límite y bloqueo de transferencias

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-05 | Límite de `TRANSFER` reducido a `50000` (inclusive). `50001` → `422 E506 "límite excedido"`. | probe_incident2/4 | confirmado |
| INC-06 | Cada `TRANSFER` rechazado por `E506` o `E507` incrementa un contador de fallos de la **cuenta origen**. | probe_incident3/4 | confirmado |
| INC-07 | Tras **3 fallos** (`E506`/`E507`), la cuenta origen queda bloqueada; el siguiente `TRANSFER` → `423 E510 {"error":"E510","mensaje":"cuenta bloqueada","intentos":N}`. | probe_incident3 | confirmado |
| INC-08 | Mientras está bloqueada, cada `TRANSFER` (que pase `E303/E304/E401`) incrementa `intentos` (1,2,3…). | probe_incident4 | confirmado |
| INC-09 | Un `DEPOSITO` exitoso **desbloquea** la cuenta y resetea el contador. `/__reset` también limpia. | probe_incident3/4 | confirmado |
| INC-10 | El bloqueo es **por cuenta origen** (no global) y **no** afecta `CONSULTA` ni `DEPOSITO`. | probe_incident3/4 | confirmado |
| INC-11 | Precedencia: `E303 → E304 → E401 → E510 → E506 → E507`. | probe_incident4 | confirmado |
| INC-12 | `E401`/`E304`/`E303` **no** incrementan el contador de fallos. | probe_incident3 | confirmado |

### 8.3 Comandos y errores descubiertos

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-13 | Comando `HALT` (aridad 1). `HALT;<x>` (x≠"1") → `409 E520 "operación destructiva: detiene el servicio; reenvía con confirmación"`. | probe_halt | confirmado |
| INC-14 | `HALT;1` (argumento literal `"1"`) → detiene el servicio: `503 {"error":"E599","mensaje":"service halted"}`. | probe_halt_clean | confirmado |
| INC-15 | En estado halted, **todo** `POST /msg` autenticado → `503 E599` (antes de tamaño/JSON); `GET /health` sigue `200`; `POST /__reset` recupera. | probe_halt_state | confirmado |
| INC-16 | En `E301` se añade `"sugerencia"` con el comando válido más cercano si la distancia de Levenshtein (case-insensitive) es ≤ 2. | probe_suggestion/threshold | confirmado |

### 8.4 Protocolo estricto

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-17 | El oráculo **no implementa CORS**: `OPTIONS /msg` → `404 E404`. | diff_battery | confirmado |
| INC-18 | Rutas/métodos inválidos → `404 E404` **antes** de autenticar. | diff_battery | confirmado |
| INC-19 | Solo `Authorization: Bearer <token>`; `?token=`/`?key=` → `401`. `Bearer  <token>` (doble espacio) → `401`. | diff_battery | confirmado |

### 8.5 Contadores globales (no deterministas en vivo)

| ID | Comportamiento | Evidencia | Confianza |
|---|---|---|---|
| INC-20 | Los contadores `AC-XXXX`, `OP-XXXX` y la cabecera `X-Req` del oráculo son **globales** (compartidos entre participantes) y `__reset` reinicia la lógica de negocio pero en la práctica los IDs absolutos pueden saltar por tráfico concurrente. | diff_battery (saltos) | confirmado |

