---
status: accepted
date: 2026-10-10
decision-makers: Equipo Frontier
---

# Estado en memoria con reset atómico

## Contexto y planteamiento del problema

El arnés del juez llama a `POST /__reset` antes de cada uno de los 100 tests.
El reemplazo debe volver a estado cero de forma instantánea y aislada.

## Drivers de decisión

* Aislamiento total entre tests.
* Latencia de reset mínima.
* Simplicidad de despliegue.

## Opciones consideradas

* (A) Persistencia en SQLite o Redis.
* (B) Almacén en RAM con snapshot para reset.

## Resultado de la decisión

Elegimos **(B) memoria + snapshot**, porque el reset ocurre en &lt; 1 ms sin I/O
de disco y el despliegue no depende de servicios externos.

### Consecuencias

* Positivo, porque el reset es instantáneo y el despliegue es trivial.
* Negativo, porque el estado no sobrevive a un reinicio forzado del proceso.

### Confirmación

Test de contrato: reset con token válido ⇒ `200`; sin token o token ajeno ⇒
comportamiento idéntico al original.

## Pros y contras de las opciones

### SQLite/Redis

* Positivo, porque sobrevive a reinicios.
* Negativo, porque añade I/O y dependencias.

### Memoria con snapshot

* Positivo, porque es rápido, simple y determinista.
* Negativo, porque pierde estado al reiniciar.

## Más información

Usaríamos SQLite/Redis si el evaluador probara escenarios de crash-recovery.
