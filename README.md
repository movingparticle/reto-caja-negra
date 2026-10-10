# Frontier Bogotá 2026 — Reto 2: Caja Negra

Reemplazo autónomo, determinista y de alta fidelidad para el servicio de caja negra. Construido en Node.js nativo (ESM) sin dependencias externas, con pruebas automatizadas y soporte para el protocolo de evaluación oficial.

---

## 1. Contrato del Entrypoint

El servicio expone un servidor HTTP desplegado públicamente y accesible por internet:

| Método | Endpoint | Cabeceras requeridas | Comportamiento |
|---|---|---|---|
| `GET` | `/health` | Ninguna | Responde `200 OK` cuando el servicio está listo. Cuerpo exacto del original: por verificar. |
| `POST` | `/__reset` | `Authorization: Bearer <TEAM_TOKEN>` | Reinicia el estado del reemplazo al inicio antes de cada test. Cuerpo exacto del original: por verificar. |
| `POST` | `/msg` | `Authorization: Bearer <token>` | Endpoint de negocio. Cuerpo JSON `{"m":"COMANDO;arg;...;control"}`. Réplica exacta del original (ver `SPEC.md` §1–§3). |
| `*` | `/*` | Según servicio original | Acepta exactamente los mismos requests que el original, incluidas rutas inexistentes. |

> El formato de negocio es `m = "COMANDO;arg1;arg2;...;control"`, con comandos
> **case-insensitive** (`CONSULta` ≡ `CONSULTA`) y un campo `control` numérico de
> integridad. Evidencia y confianza por comportamiento en `SPEC.md`.

> **Nota de seguridad del contrato:**  
> Si se invoca `POST /__reset` sin el token del equipo o con un token distinto, el reemplazo responde exactamente como el servicio original frente a una ruta inexistente (sin revelar el endpoint interno de evaluación).

---

## 2. Inicio rápido y ejecución local

### Requisitos
- Node.js >= 20.0.0 (probado en v24.14.1)

### Variables de entorno
Configura las variables según tu entorno:
```bash
export PORT=3000
export TEAM_TOKEN="tu_token_aqui"
```

### Comandos
```bash
# Iniciar servidor
npm start

# Ejecutar batería de tests automatizados
npm test

# Ejecutar el arnés de fuzzing/probes
npm run fuzz
```

---

## 3. Estructura de documentos del proyecto

- [**DESIGN_DOC.md**](DESIGN_DOC.md): Documento de diseño de arquitectura, justificación de trade-offs y diagramas Mermaid (Entregable hito 12:00). Vista navegable: [DESIGN_DOC.html](DESIGN_DOC.html).
- [**architecture.mmd**](architecture.mmd): Diagramas C4 (contexto y contenedores/componentes).
- [**docs/decisions/**](docs/decisions/README.md): Registro de decisiones de arquitectura (ADR en formato MADR 4.0).
- [**SPEC.md**](SPEC.md): Especificación técnica deducida de la API, modelo de dominio, invariantes y reglas de negocio.
- [**LOG.md**](LOG.md): Bitácora de experimentos y sondas ejecutadas contra el servicio original (con hipótesis y decisiones).
- [**INCIDENT.md**](INCIDENT.md): Registro oficial del incidente inyectado a las 15:30 y protocolo de resolución sin regresiones.
