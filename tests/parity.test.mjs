import test from 'node:test';
import assert from 'node:assert/strict';
import worker from '../src/worker.mjs';
import { BankingEngine } from '../src/engine.mjs';
import { calculateControl } from '../src/checksum.mjs';
import { suggestCommand, levenshtein } from '../src/suggest.mjs';

const env = {
  TEAM_TOKEN: 'test-team-token-fixture',
  TUTOR_KEY: 'tutor_secret_key_123',
};

const msg = (p) => `${p};${calculateControl(p)}`;

async function send(body, { method = 'POST', path = '/msg', token = env.TEAM_TOKEN } = {}) {
  const headers = {};
  if (token) headers.Authorization = `Bearer ${token}`;
  headers['Content-Type'] = 'application/json';
  const res = await worker.fetch(
    new Request(`https://caja-negra.worker${path}`, {
      method,
      headers,
      body: method === 'POST' ? JSON.stringify(body) : undefined,
    }),
    env
  );
  let json = null;
  try { json = await res.json(); } catch { /* no body */ }
  return { status: res.status, json, xreq: res.headers.get('x-req') };
}

const reset = () => worker.fetch(
  new Request('https://caja-negra.worker/__reset', {
    method: 'POST',
    headers: { Authorization: `Bearer ${env.TEAM_TOKEN}` },
  }),
  env
);

// ---------------------------------------------------------------------------
// P0-F: protocolo y auth (divergencias confirmadas contra el oráculo)
// ---------------------------------------------------------------------------

test('OPTIONS /msg devuelve 404 E404 (sin CORS)', async () => {
  const r = await send(null, { method: 'OPTIONS', token: null });
  assert.equal(r.status, 404);
  assert.deepEqual(r.json, { error: 'E404', mensaje: 'ruta desconocida' });
});

test('Preflight CORS real (OPTIONS con Access-Control-Request-Method) -> 204', async () => {
  const res = await worker.fetch(
    new Request('https://caja-negra.worker/msg', {
      method: 'OPTIONS',
      headers: {
        Origin: 'https://movingparticle.github.io',
        'Access-Control-Request-Method': 'POST',
        'Access-Control-Request-Headers': 'authorization,content-type',
      },
    }),
    env
  );
  assert.equal(res.status, 204);
  assert.equal(res.headers.get('access-control-allow-origin'), '*');
});

test('token por query no autoriza (?token= y ?key=) -> 401', async () => {
  for (const q of ['?token=' + env.TEAM_TOKEN, '?key=' + env.TEAM_TOKEN]) {
    const res = await worker.fetch(new Request(`https://caja-negra.worker/health${q}`), env);
    assert.equal(res.status, 401, `query ${q} no debe autorizar`);
    assert.deepEqual(await res.json(), { error: 'E001', mensaje: 'no autorizado' });
  }
});

test('Bearer con doble espacio no autoriza -> 401', async () => {
  const res = await worker.fetch(
    new Request('https://caja-negra.worker/health', {
      headers: { Authorization: `Bearer  ${env.TEAM_TOKEN}` },
    }),
    env
  );
  assert.equal(res.status, 401);
});

test('Bearer con espacio simple autoriza -> 200', async () => {
  const res = await worker.fetch(
    new Request('https://caja-negra.worker/health', {
      headers: { Authorization: `Bearer ${env.TEAM_TOKEN}` },
    }),
    env
  );
  assert.equal(res.status, 200);
  assert.deepEqual(await res.json(), { ok: true });
});

test('método incorrecto en ruta conocida -> 404 antes de auth', async () => {
  const bad = await worker.fetch(
    new Request('https://caja-negra.worker/health', { method: 'POST' }),
    env
  );
  assert.equal(bad.status, 404);
  assert.deepEqual(await bad.json(), { error: 'E404', mensaje: 'ruta desconocida' });
});

// ---------------------------------------------------------------------------
// P0-C: integridad - controles límite 2 y 98
// ---------------------------------------------------------------------------

test('control 98 es válido (ALTA;N16)', async () => {
  await reset();
  assert.equal(calculateControl('ALTA;N16'), 98);
  const r = await send({ m: 'ALTA;N16;98' });
  assert.equal(r.status, 201);
  assert.deepEqual(r.json, { cuentaId: 'AC-0001' });
});

test('control 2 es válido (ALTA;N48)', async () => {
  await reset();
  assert.equal(calculateControl('ALTA;N48'), 2);
  const r = await send({ m: 'ALTA;N48;2' });
  assert.equal(r.status, 201);
});

test('PING ignora el checksum pero exige aridad', async () => {
  const ok = await send({ m: 'PING;999' });
  assert.equal(ok.status, 200);
  assert.deepEqual(ok.json, { pong: true });
  const bad = await send({ m: 'PING;1;2' });
  assert.equal(bad.status, 400);
  assert.equal(bad.json.error, 'E302');
});

// ---------------------------------------------------------------------------
// Sugerencia en E301 (feature descubierta del oráculo)
// ---------------------------------------------------------------------------

test('suggestCommand coincide con el oráculo (Levenshtein <= 2)', () => {
  assert.equal(suggestCommand('ALTXX'), 'ALTA');
  assert.equal(suggestCommand('ALTXXX'), null);
  assert.equal(suggestCommand('ATLB'), null); // lev 3
  assert.equal(suggestCommand('AAT'), 'ALTA'); // empate -> orden de inserción
  assert.equal(suggestCommand(' ALTA'), 'ALTA'); // espacio inicial
  assert.equal(suggestCommand('CONSU'), null); // lev 3
  assert.equal(suggestCommand('CONSUL'), 'CONSULTA');
  assert.equal(suggestCommand('AALT'), 'HALT'); // más cercano que ALTA
  assert.equal(levenshtein('ATLB', 'ALTA'), 3);
});

test('E301 incluye campo sugerencia solo si hay comando cercano', async () => {
  await reset();
  const near = await send({ m: msg('ALTAX;A') });
  assert.equal(near.status, 400);
  assert.deepEqual(near.json, { error: 'E301', mensaje: 'comando desconocido ', sugerencia: 'ALTA' });

  const far = await send({ m: msg('FOO;1') });
  assert.equal(far.status, 400);
  assert.deepEqual(far.json, { error: 'E301', mensaje: 'comando desconocido ' });
  assert.equal('sugerencia' in far.json, false);
});

// ---------------------------------------------------------------------------
// HALT: comando destructivo con confirmación (el incidente)
// ---------------------------------------------------------------------------

test('HALT: aridad exacta 1', async () => {
  await reset();
  const zero = await send({ m: msg('HALT') });
  assert.equal(zero.json.error, 'E302');
  const two = await send({ m: msg('HALT;1;2') });
  assert.equal(two.json.error, 'E302');
});

test('HALT sin confirmación -> 409 E520 y no detiene el servicio', async () => {
  await reset();
  const warn = await send({ m: msg('HALT;AC-0001') });
  assert.equal(warn.status, 409);
  assert.deepEqual(warn.json, {
    error: 'E520',
    mensaje: 'operación destructiva: detiene el servicio; reenvía con confirmación',
  });
  // El servicio sigue operativo tras el 409
  const ping = await send({ m: msg('PING') });
  assert.equal(ping.status, 200);
});

test('HALT;1 detiene el servicio: todo /msg -> 503 E599 hasta reset', async () => {
  await reset();
  const halt = await send({ m: msg('HALT;1') });
  assert.equal(halt.status, 503);
  assert.deepEqual(halt.json, { error: 'E599', mensaje: 'service halted' });

  // Cualquier /msg (incluso válido) -> 503 E599
  const ping = await send({ m: msg('PING') });
  assert.equal(ping.status, 503);
  assert.deepEqual(ping.json, { error: 'E599', mensaje: 'service halted' });

  // /health sigue 200
  const health = await send(null, { method: 'GET', path: '/health' });
  assert.equal(health.status, 200);

  // /__reset recupera
  await reset();
  const after = await send({ m: msg('PING') });
  assert.equal(after.status, 200);
  assert.deepEqual(after.json, { pong: true });
});

test('HALT;1 consume X-Req y el halt persiste sin reset', async () => {
  await reset();
  const p1 = await send({ m: msg('PING') });
  assert.equal(p1.xreq, '1');
  const halt = await send({ m: msg('HALT;1') });
  assert.equal(halt.xreq, '2');
  const p2 = await send({ m: msg('PING') });
  assert.equal(p2.xreq, '3');
  await reset();
});

// ---------------------------------------------------------------------------
// Motor unitario: HALT
// ---------------------------------------------------------------------------

test('BankingEngine HALT y reset del estado halted', () => {
  const e = new BankingEngine();
  assert.equal(e.halted, false);
  assert.equal(e.processMessage(msg('HALT;X')).status, 409);
  assert.equal(e.halted, false);
  assert.equal(e.processMessage(msg('HALT;1')).status, 503);
  assert.equal(e.halted, true);
  e.reset();
  assert.equal(e.halted, false);
});

// ---------------------------------------------------------------------------
// INCIDENTE (15:30): formato de saldo decimal, límite 50000 y E510
// ---------------------------------------------------------------------------

test('formato de saldo: entero en centavos -> string decimal "X.YY"', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('DEPOSITO;AC-0001;1'));
  assert.equal(e.processMessage(msg('CONSULTA;AC-0001')).body.saldo, '0.01');
  e.processMessage(msg('DEPOSITO;AC-0001;500'));
  assert.equal(e.processMessage(msg('CONSULTA;AC-0001')).body.saldo, '5.01');
  e.reset();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;1000'));
  e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1000'));
  e.processMessage(msg('ANULA;OP-0001')); // depósito revertido -> negativo
  assert.equal(e.processMessage(msg('CONSULTA;AC-0001')).body.saldo, '-10.00');
});

test('límite de transferencia ahora es 50000 (50000 ok, 50001 E506)', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;50000')).status, 200);
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;50001')).body.error, 'E506');
});

test('E510: 3 fallos E506/E507 bloquean la cuenta origen (intentos incremental)', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999')).body.error, 'E506');
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999')).body.error, 'E506');
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999')).body.error, 'E506');
  const b1 = e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1'));
  assert.equal(b1.status, 423);
  assert.deepEqual(b1.body, { error: 'E510', mensaje: 'cuenta bloqueada', intentos: 1 });
  const b2 = e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1'));
  assert.equal(b2.body.intentos, 2);
});

test('E510: la precedencia respeta E303/E304/E401 antes del bloqueo', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  for (let i = 0; i < 3; i++) e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999'));
  e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1')); // activa intentos
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;0')).body.error, 'E303');
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0001;1')).body.error, 'E304');
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-9999;1')).body.error, 'E401');
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999')).body.error, 'E510');
});

test('E510: un DEPOSITO exitoso desbloquea la cuenta', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  for (let i = 0; i < 4; i++) e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999'));
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1')).body.error, 'E510');
  assert.equal(e.processMessage(msg('DEPOSITO;AC-0001;1')).status, 200);
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1')).status, 200);
});

test('E510: el bloqueo es por cuenta origen', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  e.processMessage(msg('DEPOSITO;AC-0002;9000000000'));
  for (let i = 0; i < 4; i++) e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999'));
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1')).body.error, 'E510');
  // AC-0002 no está bloqueada como origen
  assert.equal(e.processMessage(msg('TRANSFER;AC-0002;AC-0001;1')).status, 200);
});

test('E510: /__reset limpia el bloqueo', () => {
  const e = new BankingEngine();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  for (let i = 0; i < 4; i++) e.processMessage(msg('TRANSFER;AC-0001;AC-0002;99999'));
  e.reset();
  e.processMessage(msg('ALTA;A'));
  e.processMessage(msg('ALTA;B'));
  e.processMessage(msg('DEPOSITO;AC-0001;9000000000'));
  assert.equal(e.processMessage(msg('TRANSFER;AC-0001;AC-0002;1')).status, 200);
});
