import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { createServer } from '../src/server.mjs';

test('Server end-to-end integration test with probed invariants', async () => {
  const token = 'test-token-12345';
  const { server } = createServer({ token });

  await new Promise(res => server.listen(0, '127.0.0.1', res));
  const port = server.address().port;
  const baseUrl = `http://127.0.0.1:${port}`;

  try {
    // 1. Health check unauthorized
    const resNoAuth = await fetch(`${baseUrl}/health`);
    assert.equal(resNoAuth.status, 401);
    assert.deepEqual(await resNoAuth.json(), { error: 'E001', mensaje: 'no autorizado' });

    // 2. Health check authorized
    const resHealth = await fetch(`${baseUrl}/health`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.equal(resHealth.status, 200);
    assert.deepEqual(await resHealth.json(), { ok: true });

    // 3. Unknown route
    const res404 = await fetch(`${baseUrl}/unknown-route`, {
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.equal(res404.status, 404);
    assert.deepEqual(await res404.json(), { error: 'E404', mensaje: 'ruta desconocida' });

    // 4. Invalid JSON body -> E100
    const resBadJson = await fetch(`${baseUrl}/msg`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: 'not a json',
    });
    assert.equal(resBadJson.status, 400);
    assert.deepEqual(await resBadJson.json(), { error: 'E100', mensaje: 'json inválido' });

    // 5. Missing m -> E102
    const resNoM = await fetch(`${baseUrl}/msg`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
      body: JSON.stringify({ other: 123 }),
    });
    assert.equal(resNoM.status, 400);
    assert.deepEqual(await resNoM.json(), { error: 'E102', mensaje: 'falta m' });

    // 6. Reset
    const resReset = await fetch(`${baseUrl}/__reset`, {
      method: 'POST',
      headers: { Authorization: `Bearer ${token}` },
    });
    assert.equal(resReset.status, 200);
    assert.deepEqual(await resReset.json(), { ok: true });

    // 7. Run all 20 post-incident examples from pruebas/ejemplos_post_incidente.jsonl over HTTP
    const filePath = resolve('pruebas/ejemplos_post_incidente.jsonl');
    const lines = readFileSync(filePath, 'utf-8').trim().split('\n').filter(Boolean);

    let expectedXReq = 0;
    for (const line of lines) {
      const example = JSON.parse(line);
      const { id, request, status: expectedStatus, response: expectedResponse } = example;
      expectedXReq++;

      const res = await fetch(`${baseUrl}/msg`, {
        method: 'POST',
        headers: {
          Authorization: `Bearer ${token}`,
          'Content-Type': 'application/json',
        },
        body: JSON.stringify(request),
      });

      assert.equal(res.status, expectedStatus, `Step ${id} status failed`);
      assert.equal(res.headers.get('x-req'), String(expectedXReq), `Step ${id} X-Req failed`);
      const body = await res.json();
      assert.deepEqual(body, expectedResponse, `Step ${id} body failed`);
    }
  } finally {
    server.close();
  }
});
