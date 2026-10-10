#!/usr/bin/env node
// Busca offline hipótesis simples para el campo de control (último campo del mensaje).
// Uso: node scripts/checksum-search.mjs [ruta/ejemplos.jsonl]
// Supuesto H2: si la respuesta es 2xx/E4xx/E5xx, el control era válido.
// PING se excluye: hay indicios de que no valida el control.
import { readFileSync } from 'node:fs';
import { fileURLToPath } from 'node:url';
import { resolve } from 'node:path';

const B = (s) => [...Buffer.from(s)];
export const FAMILIES = {
  sum: (s) => B(s).reduce((a, b) => a + b, 0),
  sumUpper: (s) => B(s.toUpperCase()).reduce((a, b) => a + b, 0),
  sumLower: (s) => B(s.toLowerCase()).reduce((a, b) => a + b, 0),
  xor: (s) => B(s).reduce((a, b) => a ^ b, 0),
  xorUpper: (s) => B(s.toUpperCase()).reduce((a, b) => a ^ b, 0),
  weighted: (s) => B(s).reduce((a, b, i) => a + b * (i + 1), 0),
  weightedUpper: (s) => B(s.toUpperCase()).reduce((a, b, i) => a + b * (i + 1), 0),
  alphaPos: (s) => [...s.toUpperCase()].reduce((a, c) => a + (/[A-Z]/.test(c) ? c.charCodeAt(0) - 64 : /[0-9]/.test(c) ? +c : 0), 0),
  digits: (s) => [...s].reduce((a, c) => a + (/[0-9]/.test(c) ? +c : 0), 0),
  hash31Upper: (s) => B(s.toUpperCase()).reduce((a, b) => (a * 31 + b) >>> 0, 0),
  hash31: (s) => B(s).reduce((a, b) => (a * 31 + b) >>> 0, 0),
};

export function searchChecksums(rows, { maxMod = 1000, offsets = 3 } = {}) {
  const cmd = (x) => String(x.request?.m ?? '').split(';')[0].toUpperCase();
  const valid = rows.filter((x) => x.response && cmd(x) !== 'PING' && !['E201', 'E202', 'E301', 'E302'].includes(x.response.error));
  const bad = rows.filter((x) => x.response?.error === 'E202');
  let tested = 0;
  const matches = [];
  for (const [fn, f] of Object.entries(FAMILIES))
    for (const sep of ['', ';'])
      for (const scope of ['all', 'args', 'cmdUpper+args'])
        for (let mod = 2; mod <= maxMod; mod++)
          for (let k = 0; k < offsets; k++) {
            tested++;
            const calc = (m) => {
              const p = m.split(';');
              const ctrl = p.pop();
              const body = scope === 'all' ? p.join(';') : scope === 'args' ? p.slice(1).join(';') : [p[0].toUpperCase(), ...p.slice(1)].join(';');
              return [(f(body + sep) % mod) + k, ctrl];
            };
            const ok = valid.every((x) => { const [c, t] = calc(x.request.m); return String(c) === t; })
              && bad.every((x) => { const [c, t] = calc(x.request.m); return String(c) !== t; });
            if (ok) matches.push({ fn, sep, scope, mod, k });
          }
  return { tested, matches, nValid: valid.length, nBad: bad.length };
}

if (process.argv[1] && resolve(process.argv[1]) === fileURLToPath(import.meta.url)) {
  const p = process.argv[2] ?? resolve(fileURLToPath(import.meta.url), '../../../frontier-reto-2/pruebas/ejemplos.jsonl');
  const rows = readFileSync(p, 'utf8').split(/\r?\n/).filter(Boolean).map((l) => JSON.parse(l));
  const r = searchChecksums(rows);
  console.log(`hipótesis probadas: ${r.tested} · controles válidos: ${r.nValid} · inválidos: ${r.nBad} · coincidencias: ${r.matches.length}`);
  for (const m of r.matches.slice(0, 20)) console.log(m);
}
