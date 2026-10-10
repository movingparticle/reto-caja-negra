import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import worker from '../src/worker.mjs';

const env = {
  TEAM_TOKEN: process.env.TEAM_TOKEN || 'test-team-token-fixture',
  TUTOR_KEY: 'tutor_secret_key_123',
};

test('Cloudflare Worker Hardening & Multi-Key Auth', async () => {
  // 1. Unauthorized request
  const unauthRes = await worker.fetch(
    new Request('https://caja-negra.worker/health'),
    env
  );
  assert.equal(unauthRes.status, 401);
  assert.equal(unauthRes.headers.get('x-content-type-options'), 'nosniff');
  assert.deepEqual(await unauthRes.json(), { error: 'E001', mensaje: 'no autorizado' });

  // 2. Authorized via Evaluator Team Token
  const authTeamRes = await worker.fetch(
    new Request('https://caja-negra.worker/health', {
      headers: { Authorization: `Bearer ${env.TEAM_TOKEN}` },
    }),
    env
  );
  assert.equal(authTeamRes.status, 200);
  assert.deepEqual(await authTeamRes.json(), { ok: true });

  // 3. Authorized via Tutor Key
  const authTutorRes = await worker.fetch(
    new Request('https://caja-negra.worker/health', {
      headers: { Authorization: `Bearer ${env.TUTOR_KEY}` },
    }),
    env
  );
  assert.equal(authTutorRes.status, 200);
  assert.deepEqual(await authTutorRes.json(), { ok: true });

  // 4. OPTIONS /msg: el oráculo no implementa CORS -> 404 E404 (no 204)
  const corsRes = await worker.fetch(
    new Request('https://caja-negra.worker/msg', { method: 'OPTIONS' }),
    env
  );
  assert.equal(corsRes.status, 404);
  assert.deepEqual(await corsRes.json(), { error: 'E404', mensaje: 'ruta desconocida' });

  // 5. Anti-DoS: Oversized body bytes (> 8 KiB)
  const hugePadding = ' '.repeat(10000);
  const hugeRes = await worker.fetch(
    new Request('https://caja-negra.worker/msg', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.TEAM_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: '{"m":"PING;64",' + hugePadding + '"extra":1}',
    }),
    env
  );
  assert.equal(hugeRes.status, 413);
  assert.deepEqual(await hugeRes.json(), { error: 'E101', mensaje: 'cuerpo demasiado grande' });

  // 6. Anti-Injection: Null byte in payload
  const nullByteBody = JSON.stringify({ m: 'PING\x00;64' });
  const nullRes = await worker.fetch(
    new Request('https://caja-negra.worker/msg', {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${env.TEAM_TOKEN}`,
        'Content-Type': 'application/json',
      },
      body: nullByteBody,
    }),
    env
  );
  assert.equal(nullRes.status, 400);
  assert.deepEqual(await nullRes.json(), { error: 'E201', mensaje: 'control mal formado' });

  // 7. Reset via worker
  const resetRes = await worker.fetch(
    new Request('https://caja-negra.worker/__reset', {
      method: 'POST',
      headers: { Authorization: `Bearer ${env.TEAM_TOKEN}` },
    }),
    env
  );
  assert.equal(resetRes.status, 200);

  // 8. Execute all 20 post-incident examples from pruebas/ejemplos_post_incidente.jsonl against Worker
  const filePath = resolve('pruebas/ejemplos_post_incidente.jsonl');
  const lines = readFileSync(filePath, 'utf-8').trim().split('\n').filter(Boolean);

  let expectedXReq = 0;
  for (const line of lines) {
    const example = JSON.parse(line);
    const { id, request, status: expectedStatus, response: expectedResponse } = example;
    expectedXReq++;

    const res = await worker.fetch(
      new Request('https://caja-negra.worker/msg', {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${env.TEAM_TOKEN}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      }),
      env
    );

    assert.equal(res.status, expectedStatus, `Worker Step ${id} status failed`);
    assert.equal(res.headers.get('x-req'), String(expectedXReq), `Worker Step ${id} X-Req failed`);
    const body = await res.json();
    assert.deepEqual(body, expectedResponse, `Worker Step ${id} body failed`);
  }

  // 9. Routing Precedence: Unknown routes return 404 E404 even without Authorization
  const unauthUnknown = await worker.fetch(new Request('https://caja-negra.worker/some-random-route'));
  assert.equal(unauthUnknown.status, 404);
  assert.deepEqual(await unauthUnknown.json(), { error: 'E404', mensaje: 'ruta desconocida' });

  // 10. Known routes require Authorization
  const unauthMsg = await worker.fetch(new Request('https://caja-negra.worker/msg', { method: 'POST', body: '{}' }));
  assert.equal(unauthMsg.status, 401);
  assert.deepEqual(await unauthMsg.json(), { error: 'E001', mensaje: 'no autorizado' });
});
