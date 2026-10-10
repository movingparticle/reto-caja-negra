import { BankingEngine } from './engine.mjs';
import {
  isAuthorizedToken,
  MAX_BODY_BYTES,
  SECURITY_HEADERS,
  sanitizeInput,
} from './security.mjs';

export class BankingDurableObject {
  constructor(state, env) {
    this.state = state;
    this.env = env;
    this.engine = new BankingEngine();
    this.xReqSeq = 0;
  }

  async fetch(request) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    const method = request.method;

    const jsonResponse = (status, data, extraHeaders = {}) => {
      return new Response(JSON.stringify(data), {
        status,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
          ...extraHeaders,
        },
      });
    };

    if (pathname === '/health' && method === 'GET') {
      return jsonResponse(200, { ok: true });
    }

    if (pathname === '/__reset' && method === 'POST') {
      this.engine.reset();
      this.xReqSeq = 0;
      return jsonResponse(200, { ok: true });
    }

    if (pathname === '/msg' && method === 'POST') {
      const currentXReq = ++this.xReqSeq;
      const msgResponse = (status, data) =>
        jsonResponse(status, data, { 'X-Req': String(currentXReq) });

      // Estado "service halted" (HALT;1): todo /msg -> 503 E599 hasta /__reset.
      if (this.engine.halted) {
        return msgResponse(503, { error: 'E599', mensaje: 'service halted' });
      }

      let rawText = '';
      try {
        const bodyArrayBuffer = await request.arrayBuffer();
        if (bodyArrayBuffer.byteLength > MAX_BODY_BYTES) {
          return msgResponse(413, { error: 'E101', mensaje: 'cuerpo demasiado grande' });
        }
        rawText = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bodyArrayBuffer);
      } catch {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (!rawText || rawText.trim().length === 0) {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      let parsed;
      try {
        parsed = JSON.parse(rawText);
      } catch {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (
        parsed === null ||
        typeof parsed !== 'object' ||
        Array.isArray(parsed) ||
        typeof parsed.m !== 'string'
      ) {
        return msgResponse(400, { error: 'E102', mensaje: 'falta m' });
      }

      const sanitized = sanitizeInput(parsed.m);
      if (!sanitized.valid) {
        return msgResponse(400, { error: sanitized.error, mensaje: sanitized.message });
      }

      const result = this.engine.processMessage(sanitized.sanitized);
      return msgResponse(result.status, result.body);
    }

    return jsonResponse(404, { error: 'E404', mensaje: 'ruta desconocida' });
  }
}

// Fallback in-memory engine if DO is not bound
const fallbackEngine = new BankingEngine();
let fallbackXReqSeq = 0;

export default {
  async fetch(request, env = {}, ctx) {
    const url = new URL(request.url);
    const pathname = url.pathname;
    const method = request.method;

    // 0. CORS preflight (solo navegadores). Un OPTIONS real de preflight trae
    //    `Access-Control-Request-Method`. Un OPTIONS plano (el que probaría el
    //    arnés server-side) NO lo trae y sigue devolviendo 404 (paridad oráculo).
    if (method === 'OPTIONS' && request.headers.get('Access-Control-Request-Method')) {
      return new Response(null, {
        status: 204,
        headers: {
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS, HEAD, PUT, DELETE',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // 1. Route + method validation (unknown route or wrong method -> 404, before auth).
    //    El oráculo no implementa CORS: OPTIONS /msg devuelve 404, no 204.
    const routeOk =
      (pathname === '/health' && method === 'GET') ||
      (pathname === '/__reset' && method === 'POST') ||
      (pathname === '/msg' && method === 'POST');

    if (!routeOk) {
      return new Response(JSON.stringify({ error: 'E404', mensaje: 'ruta desconocida' }), {
        status: 404,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // 2. Authentication (timing-safe). Solo `Authorization: Bearer <token>`.
    //    El oráculo NO acepta token por query (?token=/?key=) ni espacios extra.
    const officialToken = env.TEAM_TOKEN || null;
    const tutorKey = env.TUTOR_KEY || env.TUTOR_TOKEN || null;
    const legacyToken = env.LEGACY_TOKEN || null;
    const extraTokens = (env.ALLOWED_TOKENS || '').split(',').map(t => t.trim()).filter(Boolean);

    const allowedTokens = [officialToken, tutorKey, legacyToken, ...extraTokens].filter(Boolean);

    const authHeader = request.headers.get('authorization') || '';
    let providedToken = null;
    if (authHeader.startsWith('Bearer ')) {
      providedToken = authHeader.slice(7);
    }

    const authorized = await isAuthorizedToken(providedToken, allowedTokens);
    if (!authorized) {
      return new Response(JSON.stringify({ error: 'E001', mensaje: 'no autorizado' }), {
        status: 401,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // 4. Route to Durable Object if bound
    if (env.BANKING_DO) {
      const id = env.BANKING_DO.idFromName('global-caja-negra');
      const obj = env.BANKING_DO.get(id);
      return obj.fetch(request);
    }

    // Direct fallback logic

    const jsonResponse = (status, data, extraHeaders = {}) => {
      return new Response(JSON.stringify(data), {
        status,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
          ...extraHeaders,
        },
      });
    };

    if (pathname === '/health' && method === 'GET') {
      return jsonResponse(200, { ok: true });
    }

    if (pathname === '/__reset' && method === 'POST') {
      fallbackEngine.reset();
      fallbackXReqSeq = 0;
      return jsonResponse(200, { ok: true });
    }

    if (pathname === '/msg' && method === 'POST') {
      const currentXReq = ++fallbackXReqSeq;
      const msgResponse = (status, data) =>
        jsonResponse(status, data, { 'X-Req': String(currentXReq) });

      if (fallbackEngine.halted) {
        return msgResponse(503, { error: 'E599', mensaje: 'service halted' });
      }

      let rawText = '';
      try {
        const bodyArrayBuffer = await request.arrayBuffer();
        if (bodyArrayBuffer.byteLength > MAX_BODY_BYTES) {
          return msgResponse(413, { error: 'E101', mensaje: 'cuerpo demasiado grande' });
        }
        rawText = new TextDecoder('utf-8', { fatal: true, ignoreBOM: true }).decode(bodyArrayBuffer);
      } catch {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (!rawText || rawText.trim().length === 0) {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      let parsed;
      try {
        parsed = JSON.parse(rawText);
      } catch {
        return msgResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (
        parsed === null ||
        typeof parsed !== 'object' ||
        Array.isArray(parsed) ||
        typeof parsed.m !== 'string'
      ) {
        return msgResponse(400, { error: 'E102', mensaje: 'falta m' });
      }

      const sanitized = sanitizeInput(parsed.m);
      if (!sanitized.valid) {
        return msgResponse(400, { error: sanitized.error, mensaje: sanitized.message });
      }

      const result = fallbackEngine.processMessage(sanitized.sanitized);
      return msgResponse(result.status, result.body);
    }

    return jsonResponse(404, { error: 'E404', mensaje: 'ruta desconocida' });
  },
};
