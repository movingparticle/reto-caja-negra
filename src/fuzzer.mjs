/**
 * Harness de Probing & Fuzzing Guiado (Active Learning)
 * Permite interrogar la API opaca y generar entradas estructuradas para LOG.md
 */

const TARGET_URL = process.env.TARGET_URL || 'http://localhost:3000';
const TEAM_TOKEN = process.env.TEAM_TOKEN || '';

/**
 * Envía una sonda HTTP al servicio objetivo y analiza la respuesta
 */
export async function sendProbe({ method = 'GET', path = '/', headers = {}, body = null, reason = '', hypothesis = '' }) {
  const url = `${TARGET_URL.replace(/\/$/, '')}${path}`;
  const requestHeaders = {
    'content-type': 'application/json',
    ...(TEAM_TOKEN ? { Authorization: `Bearer ${TEAM_TOKEN}` } : {}),
    ...headers,
  };

  const startTime = Date.now();
  let responseData = null;
  let status = null;

  try {
    const res = await fetch(url, {
      method,
      headers: requestHeaders,
      body: body ? JSON.stringify(body) : undefined,
    });

    status = res.status;
    const text = await res.text();
    try {
      responseData = JSON.parse(text);
    } catch {
      responseData = text;
    }
  } catch (error) {
    status = 'CONN_ERROR';
    responseData = error.message;
  }

  const durationMs = Date.now() - startTime;

  return {
    probe: `${method} ${path}`,
    reason,
    hypothesis,
    status,
    body: responseData,
    durationMs,
  };
}

// Ejecución interactiva rápida
if (process.argv[1] && process.argv[1].endsWith('fuzzer.mjs')) {
  console.log(`[Fuzzer] Interrogando objetivo: ${TARGET_URL}`);
  sendProbe({
    method: 'GET',
    path: '/health',
    reason: 'Validar healthcheck',
    hypothesis: 'Debe responder 200 con status ok',
  }).then((res) => {
    console.log('[Resultado de sonda]:', JSON.stringify(res, null, 2));
  });
}
