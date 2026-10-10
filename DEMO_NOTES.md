# DEMO_NOTES.md — Guion del video de 2 minutos
> **FRONTIER Bogotá 2026 · Reto 2 · La Caja Negra** — reemplazo autónomo de un servicio legado.
> Principio rector: **SHOW > CLAIM.** No decimos que funciona: lo mostramos corriendo.

```text
entrypoint -> https://caja-negra-reemplazo.parsec-ai-labs.workers.dev
demo web   -> https://caja-negra-demo.pages.dev/ (o https://reto-caja-negra.pages.dev/demo.html)
repo       -> https://github.com/movingparticle/reto-caja-negra
duracion   -> <= 120 s (corte duro)
```

---

## 1. Reglas de la toma

- **≤ 2:00 exactos.** Si sobra, se corta la evidencia, no el problema.
- **No empezar con arquitectura.** Primero el problema, luego la solución, luego *esto corriendo*.
- **Cada número en pantalla sale de una corrida real** (ver §4 Evidencia).
- Un solo bloque de terminal + el test suite. Sin diapositivas.

---

## 2. Guion por tiempo

| t | Plano | Qué se dice (1 frase) | Qué se ve |
|---|---|---|---|
| 0:00–0:15 | Cámara / rótulo | "Un banco lleva 10 años con un servicio que nadie sabe cómo funciona. Solo vemos `INPUT → CAJA → OUTPUT`." | Título + banner `BLACK BOX` |
| 0:15–0:35 | Terminal | "Construimos un reemplazo que responde **igual**, errores incluidos, sin llamar nunca al original." | `DESIGN_DOC` abierto / diagrama C4 |
| 0:35–1:10 | Terminal **en vivo** | "Este es el reemplazo desplegado. Reinicio el estado y ejecuto un flujo bancario real." | `node scripts/demo.mjs` corriendo |
| 1:10–1:35 | Terminal | "Y aquí está la parte difícil: **errores exactos** — límite, comando desconocido, control inválido." | Salidas `E506`, `E301`, `E202` |
| 1:35–1:50 | Test suite | "Contra los 20 casos públicos: paridad **20/20**, y **11/11** tests en verde." | `npm test` |
| 1:50–2:00 | Rótulo | "Modelamos la regla, no los ejemplos. Por eso generaliza a casos que no vimos." | Cierre |

---

## 3. Comando exacto de la demo en vivo

```bash
# Desde reto-caja-negra/  (Node >= 20, sin dependencias)
node scripts/demo.mjs
```

Script: `scripts/demo.mjs` — reinicia, consulta `/health`, ejecuta el flujo
`PING → ALTA → ALTA → DEPOSITO → CONSULTA → TRANSFER → CONSULTA → ANULA ×2`,
y termina con los bordes (`E506`, `E301`, `E202`). Cada línea imprime
`STATUS <m> <cuerpo exacto>`, listo para el video.

> Para apuntar al servidor local: `BASE=http://localhost:3000 TOKEN=<token> node scripts/demo.mjs`

---

## 4. Evidencia real (capturada del entrypoint de producción)

```text
reset 200
200  PING;64                              {"pong":true}
201  ALTA;Demo;19                         {"cuentaId":"AC-0001"}
201  ALTA;Otro;90                         {"cuentaId":"AC-0002"}
200  DEPOSITO;AC-0001;500;46              {"status":"recieved","operacionId":"OP-0001"}
200  CONSULTA;AC-0001;14                  {"cuenta_id":"AC-0001","saldo":500}
200  TRANSFER;AC-0001;AC-0002;200;15      {"status":"recieved","operacionId":"OP-0002"}
200  CONSULTA;AC-0002;11                  {"cuenta_id":"AC-0002","saldo":200}
200  ANULA;OP-0002;69                     {"ok":true,"anulada":"OP-0002"}
200  ANULA;OP-0002;69                     {"ok":false,"motivo":"ya anulada"}
422  TRANSFER;AC-0001;AC-0002;120000;55   {"error":"E506","mensaje":"límite excedido"}
400  SALDOS;AC-0001;38                    {"error":"E301","mensaje":"comando desconocido "}
400  ALTA;X;99                            {"error":"E202","mensaje":"control inválido"}
```

Test suite (`npm test`):

```text
ℹ tests 11   ℹ pass 11   ℹ fail 0
✔ Replicates all 20 examples from pruebas/ejemplos.jsonl exactly
✔ Adversarial Test Suite: Probed Invariants & Exact Precedence
✔ Cloudflare Worker Hardening & Multi-Key Auth
```

Números que se pueden afirmar en cámara:

- **20/20** paridad de status y cuerpo en los ejemplos públicos.
- **11/11** tests en verde.
- **40** experimentos registrados (`experimentos.jsonl`).
- **17** códigos de error replicados (incluye el espacio final de `"comando desconocido "` y el typo `"recieved"`).
- Control = **ISO 7064 Mod 97-10**, verificado en 16/16.

---

## 5. Qué falló (honestidad)

- Al inicio asumimos mal el **orden de validación** de errores; hubo que gastar probes extra para fijar `E303 > E304 > E401 > E506 > E507`.
- El algoritmo del control se trató primero como hipótesis abierta; se confirmó como **ISO 7064 Mod 97-10** recién tras 16 casos + probes de borde.
- En el primer montaje la demo transfería a una cuenta que no existía (`E401`); se corrigió el flujo creando las dos cuentas antes del `TRANSFER`.

---

## 6. Limitaciones (decirlas, no esconderlas)

- **Estado único por diseño**: se garantiza un solo estado lógico con un Durable Object (`global-caja-negra`). A 10× con múltiples instancias, cada una tendría su RAM; el siguiente paso es estado compartido con *lease*.
- Sin **concurrencia transaccional** real; el dominio se modela como máquina de estados determinista.
- Se replica el comportamiento observado, **no** se arreglan los defectos del original (typo `recieved`, espacio final, saldos negativos en `ANULA`).

---

## 7. Final takeaway

> No memorizamos ejemplos: inferimos la regla. Por eso el reemplazo responde igual
> incluso a casos que nunca vimos — y falla igual donde el original falla.

---

## 8. Checklist antes de grabar

- [ ] Entrypoint responde (`/health` → 200).
- [ ] `node scripts/demo.mjs` corre sin editar nada.
- [ ] `npm test` → 11/11.
- [ ] Fuente de terminal grande y legible (monoespaciada).
- [ ] Cronómetro visible; corte a los 2:00.
- [ ] Subir a enlace público (YouTube *unlisted* / Loom / Drive con permiso de lectura).
- [ ] Pegar el enlace en el campo **VIDEO DE 2 MINUTOS** del hito 02.

---

## 9. Después del video

- [ ] Repo público con la solución (BLOQUE 1).
- [ ] `LOG.md` con los 40 experimentos reales (BLOQUE 2).
- [ ] `SPEC.md` actualizado subido.
- [ ] `INCIDENT.md` se llena cuando ocurra el incidente de las 15:30.
