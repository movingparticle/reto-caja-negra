---
status: accepted
date: 2026-10-10
decision-makers: Equipo Frontier
---

# Adapter de normalización para tolerar el incidente

## Contexto y planteamiento del problema

El servicio original puede cambiar de comportamiento durante el día (incidente
de las 15:30). La reacción correcta no es reescribir todo, sino aislar el
cambio y conservar lo que ya funcionaba.

## Drivers de decisión

* Blast radius mínimo.
* Regresión garantizada.
* Diagnóstico antes de parchear.

## Opciones consideradas

* (A) Reescribir el motor ante el cambio observado.
* (B) Aislar un adapter de normalización de la respuesta / formato.

## Resultado de la decisión

Elegimos **(B)**, porque el cambio se contiene en un único punto y el resto del
sistema permanece intacto.

### Consecuencias

* Positivo, porque el patch es mínimo, testeable y reversibles.
* Negativo, porque agrega una capa de indirección a mantener.

### Confirmación

Test de regresión congelado antes del cambio + test específico del nuevo caso.

## Pros y contras de las opciones

### Reescribir el motor

* Positivo, porque asume el cambio de forma directa.
* Negativo, porque aumenta el blast radius y el riesgo de regresión.

### Adapter de normalización

* Positivo, porque acota el cambio y preserva lo anterior.
* Negativo, porque añade indirección.

## Más información

Si el cambio invalidara el modelo de dominio completo, reconsideraríamos (A).
