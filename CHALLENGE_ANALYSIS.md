# Reto 2: La Caja Negra — Challenge Analysis & System Design

## 1. Problem Understanding
Reconstruir mediante ingeniería inversa una réplica exacta de un servicio bancario en producción de 10 años de antigüedad que procesa mensajes por HTTP, manteniendo estricta paridad en casos exitosos, códigos de estado, estructura de respuesta, mensajes de error literales y bugs históricos.

## 2. Constraints & Invariants
- **Autenticación**: `Authorization: Bearer <token>` requerida en todos los endpoints. Retorna 401 `E001` sin autorización.
- **Rutas estándar**: `GET /health`, `POST /__reset`, `POST /msg`. Cualquier otra ruta retorna 404 `E404`.
- **Integridad de mensaje**: Protocolo con código de control delimitado por punto y coma `;`. Si el control no es numérico retorna 400 `E201`. Si no coincide con el algoritmo, retorna 400 `E202`.
- **Tiempo de respuesta**: Menor a 5 segundos por paso.
- **Sin llamadas externas**: El reemplazo debe ser autónomo y no reenviar tráfico al oráculo.

## 3. Reverse-Engineered Mechanism (The Checksum)
A través de análisis diferencial en pares de secuencias de prueba (`AC-0001` vs `AC-0002` vs `AC-0009` y montos de transferencias), se demostró matemáticamente que el servicio utiliza **ISO 7064 Mod 97-10 Alfanumérico 1-based**:
- Mapeo: $A=1, B=2, \dots, I=9, J=10, \dots, Z=26$.
- Dígitos: $0..9$. Caracteres no alfanuméricos ignorados.
- Fórmula de control: $CD = (98 - (N \times 100)) \pmod{97} \equiv (98 - (N \pmod{97} \times 3)) \pmod{97}$.
- Precisión: 16 de 16 ejemplos empíricos verificados con 100% de coincidencia exacta.

## 4. Business Logic Inferred
- **`PING`**: Sin argumentos. Retorna 200 `{"pong":true}`.
- **`ALTA`**: 1 argumento (nombre). Genera `AC-0001`, `AC-0002` secuencialmente con saldo inicial 0.
- **`CONSULTA`**: 1 argumento (cuenta). Retorna saldo. 404 `E401` si no existe.
- **`DEPOSITO`**: 2 argumentos (cuenta, monto). Acredita saldo y genera `OP-XXXX`. Retorna `{"status":"recieved","operacionId":"OP-XXXX"}`.
- **`TRANSFER`**: 3 argumentos (origen, destino, monto).
  - Límite máximo: 100.000. Si supera, retorna 422 `E506`.
  - Saldo suficiente: si $saldo < monto$, retorna 422 `E507`.
  - Cuentas existentes: 404 `E401`.
- **`ANULA`**: 1 argumento (operacionId). Revierte transferencias/depósitos. Si ya fue anulada, retorna 200 `{"ok":false,"motivo":"ya anulada"}`.

## 5. Architecture Options & Trade-offs

| Opción | Ventajas | Desventajas | Decisión |
|---|---|---|---|
| **A. Node.js ESM nativo (node:http)** | Cero dependencias externas, arranque instantáneo (<10ms), ejecución no bloqueante, precisión entera con BigInt nativo. | Estado en memoria de proceso único. | **ELEGIDA (10/10)** |
| **B. Python FastAPI / Flask** | Rápido desarrollo inicial. | Requiere dependencias externas (`pip`), mayor latencia de inicio, mayor complejidad en despliegue simple. | Descartada |
| **C. LLM dinámico como proxy** | Adaptable a variaciones semánticas. | Latencia impredecible (>1-2s), alto riesgo de alucinación en aritmética o hashes, no determinista. | Descartada |

## 6. Test Matrix & Hidden-Test Hypotheses

| ID | Hipótesis / Caso Adversarial | Resultado Esperado | Prioridad |
|---|---|---|---|
| T-01 | Transferencia de exactamente 100.000 | 200 OK | P0 |
| T-02 | Transferencia de 100.001 | 422 `E506` | P0 |
| T-03 | Saldo exacto debitado a 0 | 200 OK | P0 |
| T-04 | Saldo insuficiente por 1 unidad | 422 `E507` | P0 |
| T-05 | Aridad incorrecta (0, 2 o más args según comando) | 400 `E302` | P0 |
| T-06 | Control con letras o caracteres extraños | 400 `E201` | P0 |
| T-07 | Nombre de comando en minúsculas o mixto (`pInG`, `AlTa`) | 200 / 201 OK | P0 |
| T-08 | Re-anulación de operación ya anulada | 200 `ok: false, motivo: "ya anulada"` | P0 |
| T-09 | Reinicio de estado con `POST /__reset` | 200 OK, reset de contadores | P0 |
| T-10 | Carga HTTP mayor a 8.192 bytes (8 KiB) | 413 `E101` (`cuerpo demasiado grande`) | P0 |
| T-11 | Monto con ceros iniciales (`0100`) o flotante (`10.5`) | 400 `E303` (`monto inválido`) | P0 |
| T-12 | Monto con 11 dígitos decimales (`10000000000`) | 400 `E303` (`monto inválido`) | P0 |
| T-13 | Monto con 10 dígitos decimales (`9999999999`) | 200 OK (`status: recieved`) | P0 |
| T-14 | Cálculo de control donde $(rem \times 3) \equiv 1$ produce 97 (no 0) | 200 OK (Control válido en ISO 7064) | P0 |
| T-15 | Ruta no mapeada (ej. `GET /unmapped`) sin autenticación | 404 `E404` (`ruta desconocida`) | P0 |
