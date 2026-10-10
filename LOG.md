# LOG — Bitácora de Experimentos y Sondas (Reto 2)
> **Formato de la rúbrica oficial:** Registro sistemático de probes, hipótesis y decisiones.

---

## 1. Registro de Sondas y Experimentos

La fuente de evidencia base son los 20 casos públicos de `frontier-reto-2/pruebas/ejemplos.jsonl`
(citados como `ej:#N`). Los probes propios contra el oráculo están **pendientes**: las filas
`por ejecutar` aún no son evidencia propia. Cada línea de `experimentos.jsonl` citará aquí su `id`.

| # | Probe (Petición enviada) | Razón / Objetivo | Resultado (Status + Body) | Hipótesis afectada | Decisión técnica tomada |
|---|---|---|---|---|---|
| B-01 | Reproducir `ejemplos.jsonl` #1–#20 tras `POST /__reset` | Fijar baseline de paridad | 20/20 registrados (ver `SPEC.md`) | El dominio es bancario y `m="CMD;args;control"` | Modelar PING·ALTA·CONSULTA·DEPOSITO·TRANSFER·ANULA |
| B-02 | `ej:#2` (`ALTA;Lucia;83`) vs `ej:#3` (`ALTA;Lucia;82`) | Aislar el campo `control` | `400 E202` vs `201 Created` | El control es un valor de verificación del mensaje | Pendiente: determinar el algoritmo del control |
| B-03 | `ej:#12` (`SALDOS;AC-0001;38`) | Probar comando desconocido | `400 E301 "comando desconocido "` | El comando se compara case-insensitive | Replicar el mensaje literal (espacio final) |
| P-01 | `GET /health` | Confirmar status y cuerpo exactos del original | *por ejecutar* | *H-01* | *por decidir* |
| P-02 | `POST /__reset` (con token y sin token) | Confirmar comportamiento estricto de seguridad | *por ejecutar* | *H-04* | *por decidir* |

---

## 2. Hipótesis vigentes

- **H-01:** La API responde a métodos estándar (GET, POST) en rutas de dominio (`/health`, `/__reset`, `/msg`).
- **H-02:** El comportamiento es una máquina de estados determinista por token (saldos y contadores `AC-*`/`OP-*`), reiniciable con `__reset`.
- **H-03:** El campo `control` es un valor de verificación determinista sobre el resto del mensaje; su algoritmo es desconocido. Evidencia: `ej:#2` vs `ej:#3`.
- **H-04:** `POST /__reset` sin token válido debe comportarse como el original y no revelar el mecanismo (pendiente de probar).
