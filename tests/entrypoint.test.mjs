import { test, describe, before, after } from 'node:test';
import assert from 'node:assert/strict';
import { createServer } from '../src/server.mjs';
import { ReplicaEngine } from '../src/replica.mjs';

describe('Contrato del Entrypoint Oficial (Frontier)', () => {
  let server;
  let baseUrl;
  const testToken = 'secret-test-token-123';

  before(async () => {
    const engine = new ReplicaEngine();
    server = createServer(engine, { teamToken: testToken });
    await new Promise((resolve) => server.listen(0, '127.0.0.1', resolve));
    const port = server.address().port;
    baseUrl = `http://127.0.0.1:${port}`;
  });

  after(async () => {
    await new Promise((resolve) => server.close(resolve));
  });

  test('GET /health responde 200 OK y status ok', async () => {
    const res = await fetch(`${baseUrl}/health`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.status, 'ok');
  });

  test('POST /__reset con token válido reinicia estado y responde 200 OK', async () => {
    const res = await fetch(`${baseUrl}/__reset`, {
      method: 'POST',
      headers: {
        Authorization: `Bearer ${testToken}`,
      },
    });
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.reset, true);
  });

  test('POST /__reset con token inválido o ausente responde como el servicio original (no resetea ni expone el endpoint)', async () => {
    // 1. Sin cabecera Authorization
    const resNoAuth = await fetch(`${baseUrl}/__reset`, {
      method: 'POST',
    });
    // Debe comportarse como una ruta común desconocida en el original (404)
    assert.equal(resNoAuth.status, 404);
    const bodyNoAuth = await resNoAuth.json();
    assert.equal(bodyNoAuth.error, 'not_found');

    // 2. Con token incorrecto
    const resWrongToken = await fetch(`${baseUrl}/__reset`, {
      method: 'POST',
      headers: {
        Authorization: 'Bearer token-falso-999',
      },
    });
    assert.equal(resWrongToken.status, 404);
  });

  test('Ruta raíz GET / responde según la réplica', async () => {
    const res = await fetch(`${baseUrl}/`);
    assert.equal(res.status, 200);
    const body = await res.json();
    assert.equal(body.active, true);
  });

  test('Ruta desconocida responde 404 según la réplica', async () => {
    const res = await fetch(`${baseUrl}/ruta-inexistente-12345`);
    assert.equal(res.status, 404);
  });

  test('Payload mayor a 64 KiB es rechazado con 413 Payload Too Large', async () => {
    const bigPayload = 'x'.repeat(70 * 1024);
    const res = await fetch(`${baseUrl}/data`, {
      method: 'POST',
      headers: { 'content-type': 'application/json' },
      body: JSON.stringify({ data: bigPayload }),
    });
    assert.equal(res.status, 413);
  });
});
