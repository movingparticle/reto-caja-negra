# Technical Defense & Architecture Debrief · Reto 2

Documento de preparación para la defensa técnica ante el panel de jueces evaluadores.

---

## 1. Key Architectural Decisions

### Decisión 1: Deducción Analítica del Algoritmo de Integridad (ISO 7064 Mod 97-10)
- **Qué:** Implementación analítica exacta del algoritmo de control bancario utilizando aritmética modular sobre BigInt.
- **Por qué:** Evita cualquier heurística opaca o aproximación estadística. El análisis de diferencias en las potencias de base 10 ($10^0$ en `AC-0001` vs `AC-0002` y $10^4$ en transferencias de $120.000$ vs $100.000$) demostró que la función de control es estrictamente $(98 - (N \times 100)) \pmod{97}$ con codificación alfanumérica 1-based.
- **Alternativa descartada:** Lookup tables o interpolación polinómica. Se descartaron porque fallarían catastróficamente en la batería oculta con nuevos nombres o cuentas.
- **Trade-off:** Requiere precisión matemática sobre strings de longitud arbitraria, resuelto limpiamente con `BigInt` nativo.

### Decisión 2: Node.js Nativo ESM sin Dependencias Externas
- **Qué:** Servidor HTTP construido con `node:http` estándar.
- **Por qué:** Arranque inmediato (<15 ms), consumo mínimo de memoria (<25 MB), reproducibilidad total en cualquier máquina o contenedor sin riesgo de fallos en `npm install`.
- **Alternativa descartada:** Frameworks como Express o NestJS. Agregan sobrecarga innecesaria y superficie de ataque sin aportar valor al contrato estricto del reto.

### Decisión 4: Blindaje Adversarial y Detección de Límites Físicos (Stress Testing)
- **Qué:** Batería sistemática de pruebas de fuzzing y asalto contra el oráculo en vivo manteniendo consumo mínimo de cuota (<1% del límite diario).
- **Por qué:** Permitió descubrir 4 comportamientos invisibles en la especificación inicial:
  1. El código de error oculto `E101` con HTTP 413 ante cargas $> 8.192$ bytes.
  2. El caso límite del dígito de control 97 en ISO 7064 Mod 97-10 (que no colapsa a 0).
  3. La prohibición de ceros a la izquierda en montos (`0100` $\to$ `E303`) y el tope estricto de 10 dígitos.
  4. La prioridad de enrutamiento 404 sobre el middleware de autenticación 401.

---

## 2. Failure Modes & Mitigaciones

| Modo de Fallo | Causa Raíz Potencial | Mitigación Implementada |
|---|---|---|
| Desbordamiento de enteros en payload grande | Nombres o montos muy extensos en el mensaje | Uso de `BigInt` con cálculo incremental de residuo módulo 97 por carácter para evitar números gigantes en memoria. |
| Inyección de DoS por payloads masivos | Cargas mayores a 8 KiB enviadas para saturar buffers | Inspección temprana de buffer en el Worker; rechazo con HTTP 413 `E101 cuerpo demasiado grande` si excede 8.192 bytes. |
| Malformación de entrada JSON | Payload con JSON truncado o tipos no string | Try-catch defensivo con respuestas estandarizadas 400 `E100` y `E102`. |
| Estado remanente entre secuencias | Llamadas concurrentes o fallo en reset | `POST /__reset` reinicia todas las estructuras de datos y contadores a 1 en el Durable Object. |
| Inyección de comandos por delimitadores | Nombres con punto y coma (ej. `ALTA;Robert'); DROP TABLE...`) | El validador detecta aridad estricta y rechaza con `E302`. |
| Reversión con saldo insuficiente previo | Anulación de transferencias cuyos fondos ya fueron gastados | Motor permite saldo negativo consistente y bloquea subsecuentes transferencias con `E507`. |
| Caso borde modular en control (valor 97) | Módulo outer redundante convirtiendo 97 en 0 | Eliminación de `% 97` exterior: el rango canónico es estrictamente $[2, 98]$. |

---

## 3. Preparación para Preguntas Clave del Jurado

### "¿Cómo saben que esto generalizará a casos que no estaban en los 20 ejemplos?"
> "Porque no hicimos overfitting sobre las salidas observadas. Aislamos la regla matemática de control mediante pruebas diferenciales sobre las variables de entrada: el cambio de 1 unidad en la posición de unidades alteró el resultado exactamente en $-3 \equiv 94 \pmod{97}$, lo que prueba una base decimal ponderada con multiplicador $100 \equiv 3 \pmod{97}$ y residuo mod 97 (la norma bancaria internacional ISO 7064 Mod 97-10). La aridad, validación y límites fueron formalizados en una máquina de estados determinista verificada con pruebas adversariales exhaustivas."

### "¿Qué es lo más frágil de la solución si escalara a 10x o producción real?"
> "El estado en memoria local de un único proceso. Para escalabilidad horizontal requeriríamos persistencia en PostgreSQL con transacciones seriabilizadas para prevenir condiciones de carrera entre transferencias concurrentes."
