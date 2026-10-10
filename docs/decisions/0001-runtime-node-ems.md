---
status: accepted
date: 2026-10-10
decision-makers: Equipo Frontier
---

# Runtime Node.js ESM sin dependencias externas

## Contexto y planteamiento del problema

El reemplazo debe ser reproducible y ejecutable sin explicación adicional en
cualquier entorno de evaluación. Un árbol de dependencias externo introduce
riesgo de drift de versiones y de fallos de instalación.

## Drivers de decisión

* Reproducibilidad idéntica en cualquier host.
* Superficie de ataque y de fallo reducidas.
* Tiempo de arranque bajo.

## Opciones consideradas

* (A) Fastify/Express + TypeScript + validación con Zod/Joi.
* (B) Node.js nativo ESM (`node:http`, `node:test`), cero dependencias de npm.

## Resultado de la decisión

Elegimos **(B) Node.js nativo ESM**, porque elimina el riesgo del árbol de
dependencias y garantiza un despliegue idéntico y rápido.

### Consecuencias

* Positivo, porque el arranque es &lt; 50 ms y no hay versiones que resolver.
* Negativo, porque el routing y la validación se implementan a mano.

### Confirmación

Clean-room run: `npm ci && npm test && npm start` en un entorno limpio.

## Pros y contras de las opciones

### Fastify/Express + TypeScript

* Positivo, porque aporta abstracciones de routing y tipado.
* Negativo, porque agrega dependencias y tiempo de instalación.

### Node.js nativo ESM

* Positivo, porque es portable, determinista y sin instalación.
* Negativo, porque exige escribir utilidades básicas.

## Más información

Cambiaríamos a Fastify si se requiriera &gt; 25.000 req/s con serialización
dinámica compleja.
