import http from 'node:http';
import { BankingEngine } from './engine.mjs';

export function createServer(options = {}) {
  const extraTokens = (process.env.ALLOWED_TOKENS || '')
    .split(',')
    .map(t => t.trim())
    .filter(Boolean);
  const allowedTokens = new Set([
    options.token,
    process.env.TEAM_TOKEN,
    ...extraTokens,
  ].filter(Boolean));
  const engine = options.engine || new BankingEngine();
  let xReqSeq = 0;

  const server = http.createServer(async (req, res) => {
    // Helper to send json response
    const sendJson = (status, data, headers = {}) => {
      res.writeHead(status, {
        'Content-Type': 'application/json; charset=utf-8',
        ...headers,
      });
      res.end(JSON.stringify(data));
    };

    // Helper to check authentication
    const authHeader = req.headers['authorization'];
    let providedToken = null;
    if (authHeader && authHeader.startsWith('Bearer ')) {
      providedToken = authHeader.slice(7).trim();
    }
    const isValidToken = Boolean(providedToken && allowedTokens.has(providedToken));

    // Read request body
    let bodyBuffer = [];
    req.on('data', chunk => {
      bodyBuffer.push(chunk);
    });

    req.on('end', () => {
      const bodyText = Buffer.concat(bodyBuffer).toString('utf-8');
      const url = req.url;
      const method = req.method;

      // Check endpoints
      if (url === '/health' && method === 'GET') {
        if (!isValidToken) {
          return sendJson(401, { error: 'E001', mensaje: 'no autorizado' });
        }
        return sendJson(200, { ok: true });
      }

      if (url === '/__reset' && method === 'POST') {
        if (!isValidToken) {
          return sendJson(401, { error: 'E001', mensaje: 'no autorizado' });
        }
        engine.reset();
        xReqSeq = 0;
        return sendJson(200, { ok: true });
      }

      if (url === '/msg' && method === 'POST') {
        if (!isValidToken) {
          return sendJson(401, { error: 'E001', mensaje: 'no autorizado' });
        }

        const currentXReq = ++xReqSeq;
        const msgJson = (status, data) => sendJson(status, data, { 'X-Req': String(currentXReq) });

        // Validate JSON body
        if (!bodyText || bodyText.trim().length === 0) {
          return msgJson(400, { error: 'E100', mensaje: 'json inválido' });
        }

        let parsed;
        try {
          parsed = JSON.parse(bodyText);
        } catch {
          return msgJson(400, { error: 'E100', mensaje: 'json inválido' });
        }

        // Validate presence of string field 'm'
        if (
          parsed === null ||
          typeof parsed !== 'object' ||
          Array.isArray(parsed) ||
          typeof parsed.m !== 'string'
        ) {
          return msgJson(400, { error: 'E102', mensaje: 'falta m' });
        }

        const result = engine.processMessage(parsed.m);
        return msgJson(result.status, result.body);
      }

      // Any other route or method
      return sendJson(404, { error: 'E404', mensaje: 'ruta desconocida' });
    });
  });

  return { server, engine };
}
