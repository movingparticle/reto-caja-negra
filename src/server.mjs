import http from 'node:http';
import { URL } from 'node:url';
import { ReplicaEngine } from './replica.mjs';

const PORT = parseInt(process.env.PORT || '3000', 10);
const HOST = process.env.HOST || '0.0.0.0';
const TEAM_TOKEN = process.env.TEAM_TOKEN || 'frontier-team-token-default';
const MAX_PAYLOAD_SIZE = 64 * 1024; // 64 KiB límite de seguridad

export function createServer(engine = new ReplicaEngine(), options = {}) {
  const teamToken = options.teamToken || TEAM_TOKEN;

  const server = http.createServer(async (req, res) => {
    try {
      const parsedUrl = new URL(req.url, `http://${req.headers.host || 'localhost'}`);
      const pathname = parsedUrl.pathname;
      const method = req.method?.toUpperCase() || 'GET';

      // 1. Lectura segura del payload (si existe)
      let rawBody = '';
      let bodyExceeded = false;

      for await (const chunk of req) {
        rawBody += chunk;
        if (rawBody.length > MAX_PAYLOAD_SIZE) {
          bodyExceeded = true;
          break;
        }
      }

      if (bodyExceeded) {
        res.writeHead(413, { 'content-type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ error: 'payload_too_large' }));
        return;
      }

      let parsedBody = null;
      if (rawBody.trim().length > 0) {
        try {
          parsedBody = JSON.parse(rawBody);
        } catch {
          // Si el JSON es malformado, se pasa raw o se maneja según contrato
          parsedBody = rawBody;
        }
      }

      // 2. Healthcheck del evaluador
      if (method === 'GET' && pathname === '/health') {
        res.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
        res.end(JSON.stringify({ status: 'ok', uptime: process.uptime() }));
        return;
      }

      // 3. Reset del evaluador con Token del equipo
      if (method === 'POST' && pathname === '/__reset') {
        const authHeader = req.headers['authorization'] || '';
        const match = authHeader.match(/^Bearer\s+(.+)$/i);
        const providedToken = match ? match[1].trim() : null;

        if (providedToken && providedToken === teamToken) {
          engine.reset();
          res.writeHead(200, { 'content-type': 'application/json; charset=utf-8' });
          res.end(JSON.stringify({ reset: true, timestamp: Date.now() }));
          return;
        }
        // Con otro token o sin token: responde exactamente como el original
        // No expone el reset y delega a la réplica como una ruta ordinaria
      }

      // 4. Captura universal /* (comportamiento del servicio original)
      const queryParams = Object.fromEntries(parsedUrl.searchParams.entries());
      const response = engine.processRequest({
        method,
        path: pathname,
        headers: req.headers,
        query: queryParams,
        body: parsedBody,
      });

      const responseHeaders = {
        'content-type': 'application/json; charset=utf-8',
        ...(response.headers || {}),
      };

      res.writeHead(response.status || 200, responseHeaders);
      const payloadString = typeof response.body === 'string'
        ? response.body
        : JSON.stringify(response.body);

      res.end(payloadString);
    } catch (err) {
      // Error no controlado: respuesta limpia sin filtrar trazas
      res.writeHead(500, { 'content-type': 'application/json; charset=utf-8' });
      res.end(JSON.stringify({ error: 'internal_server_error' }));
    }
  });

  return server;
}

// Iniciar servidor directamente si se ejecuta desde CLI
if (process.argv[1] && process.argv[1].endsWith('server.mjs')) {
  const engine = new ReplicaEngine();
  const server = createServer(engine);
  server.listen(PORT, HOST, () => {
    console.log(`[Entrypoint] Servidor activo en http://${HOST}:${PORT}`);
    console.log(`[Entrypoint] Healthcheck: http://${HOST}:${PORT}/health`);
    console.log(`[Entrypoint] Configurado con TEAM_TOKEN: ${TEAM_TOKEN ? 'DEFINIDO' : 'DEFAULT'}`);
  });
}
