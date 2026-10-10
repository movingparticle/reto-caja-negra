---
status: accepted
date: 2026-10-10
decision-makers: Equipo Frontier
---

# Probing guiado por hipótesis (active learning)

## Contexto y planteamiento del problema

El presupuesto de consultas al servicio original es limitado (10 req/s,
8.000/día). Un fuzzer ciego desperdicia ese presupuesto y no modela la
semántica de estados ni el orden de validación.

## Drivers de decisión

* Máxima ganancia de información por probe.
* Trazabilidad exigida por la rúbrica (SPEC + LOG).
* Evitar overfitting a los ejemplos conocidos.

## Opciones consideradas

* (A) Fuzzing aleatorio/genético masivo.
* (B) Probes discriminativos guiados por hipótesis.

## Resultado de la decisión

Elegimos **(B) active learning**, porque cada probe intenta separar hipótesis
rivales y queda registrado con su predicción antes/después.

### Consecuencias

* Positivo, porque produce evidencia citable y una SPEC defendible.
* Negativo, porque es más lento para descubrir edge cases sintácticos puros.

### Confirmación

Cada línea del `LOG.md` cita hipótesis afectada y decisión tomada.

## Pros y contras de las opciones

### Fuzzing aleatorio masivo

* Positivo, porque cubre rápido variaciones sintácticas.
* Negativo, porque no discrimina entre hipótesis ni documenta el porqué.

### Probes guiados por hipótesis

* Positivo, porque maximiza información y trazabilidad.
* Negativo, porque requiere diseñar cada probe.

## Más información

Añadiríamos mutadores aleatorios si aparecieran campos de texto libre o
estructuras anidadas profundas.
