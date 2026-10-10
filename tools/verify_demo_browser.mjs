import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';

const LIVE_URL = 'https://caja-negra-reemplazo.parsec-ai-labs.workers.dev';
const TEAM = 'ftr_904403fa4633e37c63c98b305a14ccbd';
const INVALID = 'invalid_token_99999999999999999';

function stableStr(v) {
  if (v === null || typeof v !== 'object') return JSON.stringify(v);
  if (Array.isArray(v)) return '[' + v.map(stableStr).join(',') + ']';
  return '{' + Object.keys(v).sort().map(k => JSON.stringify(k) + ':' + stableStr(v[k])).join(',') + '}';
}

async function runStep(s) {
  const headers = {};
  if (s.headers) {
    Object.assign(headers, s.headers);
  } else {
    const a = s.auth || 'team';
    const token = a === 'none' ? '' : (a === 'invalid' ? INVALID : TEAM);
    if (token) headers['Authorization'] = 'Bearer ' + token;
  }
  let body;
  if (s.raw !== undefined) body = s.raw;
  else if (s.body !== undefined) body = JSON.stringify(s.body);
  else if (s.m !== undefined) body = JSON.stringify({ m: s.m });
  if (body !== undefined && headers['Content-Type'] === undefined) headers['Content-Type'] = 'application/json';

  const opts = { method: s.method || 'POST', headers };
  if (body !== undefined) opts.body = body;
  try {
    const res = await fetch(LIVE_URL + s.path, opts);
    let parsed = {};
    try { parsed = await res.json(); } catch { parsed = await res.text(); }
    return { status: res.status, body: parsed, ok: true };
  } catch (err) {
    return { status: 0, body: { error: 'NET_ERR', message: err.message }, ok: false };
  }
}

const suite = JSON.parse(readFileSync(resolve('demo-suite.json'), 'utf-8'));
let fails = 0;
for (const t of suite) {
  await runStep({ method: 'POST', path: '/__reset', body: {} });
  for (let i = 0; i < t.steps.length; i++) {
    const s = t.steps[i];
    const res = await runStep(s);
    const ok = res.ok && res.status === s.expStatus && stableStr(res.body) === stableStr(s.expBody);
    if (!ok) {
      fails++;
      console.log(`FAIL ${t.id} paso ${i + 1}: got ${res.status} ${stableStr(res.body)} | exp ${s.expStatus} ${stableStr(s.expBody)}`);
      break;
    }
  }
}
console.log(`tests=${suite.length} fails=${fails}`);
process.exit(fails ? 1 : 0);
