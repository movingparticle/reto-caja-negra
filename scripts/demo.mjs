// scripts/demo.mjs — Guion ejecutable del video de 2 minutos (Reto 2 · Caja Negra)
//
// Uso:
//   node scripts/demo.mjs
//   BASE=http://localhost:3000 TOKEN=mi_token node scripts/demo.mjs
//
// Por defecto ataca el entrypoint de producción y usa el token del equipo.
// Cada línea imprime: STATUS  <m>  <cuerpo exacto>  — listo para mostrar en vivo.

import { calculateControl } from "../src/checksum.mjs";

const BASE = process.env.BASE || "https://caja-negra-reemplazo.parsec-ai-labs.workers.dev";
const TOKEN = process.env.TOKEN || process.env.TEAM_TOKEN || "ftr_904403fa4633e37c63c98b305a14ccbd";

const headers = { Authorization: `Bearer ${TOKEN}`, "Content-Type": "application/json" };

const line = (s) => process.stdout.write(s + "\n");
const rule = (t) => line(`\n> ${t}\n` + "-".repeat(64));

async function send(payload) {
  const m = `${payload};${calculateControl(payload)}`;
  const res = await fetch(`${BASE}/msg`, { method: "POST", headers, body: JSON.stringify({ m }) });
  const body = await res.text();
  line(`${String(res.status).padEnd(4)} ${m.padEnd(36)} ${body}`);
}

async function main() {
  line(`entrypoint -> ${BASE}`);
  rule("reset (el arnés lo llama antes de cada test)");
  const reset = await fetch(`${BASE}/__reset`, { method: "POST", headers });
  line(`${reset.status} POST /__reset`);

  rule("health");
  const health = await fetch(`${BASE}/health`, { headers });
  line(`${health.status} GET  /health        ${await health.text()}`);

  rule("flujo de negocio real");
  for (const p of [
    "PING",
    "ALTA;Demo",
    "ALTA;Otro",
    "DEPOSITO;AC-0001;500",
    "CONSULTA;AC-0001",
    "TRANSFER;AC-0001;AC-0002;200",
    "CONSULTA;AC-0002",
    "ANULA;OP-0002",
    "ANULA;OP-0002",
  ]) await send(p);

  rule("bordes y errores exactos");
  await send("TRANSFER;AC-0001;AC-0002;120000"); // E506 límite
  await send("SALDOS;AC-0001");                 // E301 comando desconocido
  const bad = await fetch(`${BASE}/msg`, {
    method: "POST",
    headers,
    body: JSON.stringify({ m: "ALTA;X;99" }),   // control inválido
  });
  line(`${String(bad.status).padEnd(4)} ${"ALTA;X;99".padEnd(36)} ${await bad.text()}`);

  rule("fin — paridad status + body, errores incluidos");
}

main().catch((err) => {
  line(`error: ${err.message}`);
  process.exit(1);
});
