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
      let rawText = '';
      try {
        const bodyArrayBuffer = await request.arrayBuffer();
        if (bodyArrayBuffer.byteLength > MAX_BODY_BYTES) {
          return jsonResponse(413, { error: 'E101', mensaje: 'cuerpo demasiado grande' });
        }
        rawText = new TextDecoder('utf-8', { fatal: true }).decode(bodyArrayBuffer);
      } catch {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (!rawText || rawText.trim().length === 0) {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      let parsed;
      try {
        parsed = JSON.parse(rawText);
      } catch {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (
        parsed === null ||
        typeof parsed !== 'object' ||
        Array.isArray(parsed) ||
        typeof parsed.m !== 'string'
      ) {
        return jsonResponse(400, { error: 'E102', mensaje: 'falta m' });
      }

      const sanitized = sanitizeInput(parsed.m);
      if (!sanitized.valid) {
        return jsonResponse(400, { error: sanitized.error, mensaje: sanitized.message });
      }

      const currentXReq = ++this.xReqSeq;
      const result = this.engine.processMessage(sanitized.sanitized);
      return jsonResponse(result.status, result.body, { 'X-Req': String(currentXReq) });
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

    // 1. CORS Pre-flight Handling
    if (request.method === 'OPTIONS') {
      return new Response(null, {
        status: 204,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
          'Access-Control-Allow-Methods': 'GET, POST, OPTIONS',
          'Access-Control-Allow-Headers': 'Authorization, Content-Type',
          'Access-Control-Max-Age': '86400',
        },
      });
    }

    // 2. Validate known route (unknown routes return 404 regardless of auth, exactly as live server)
    const pathname = url.pathname;
    if (pathname !== '/msg' && pathname !== '/health' && pathname !== '/__reset') {
      return new Response(JSON.stringify({ error: 'E404', mensaje: 'ruta desconocida' }), {
        status: 404,
        headers: {
          ...SECURITY_HEADERS,
          'Access-Control-Allow-Origin': '*',
        },
      });
    }

    // 3. Authentication Check (Timing-safe)
    // Supports both Authorization: Bearer <token> AND query param (?token=... o ?key=...) para navegadores
    const officialToken = env.TEAM_TOKEN || 'cn-p-abh_bog_wlw9_8r83-QnLthfmAjCo3D6QXyf_Ztb';
    const tutorKey = env.TUTOR_KEY || env.TUTOR_TOKEN || null;
    const legacyToken = 'ftr_904403fa4633e37c63c98b305a14ccbd';
    const extraTokens = (env.ALLOWED_TOKENS || '').split(',').map(t => t.trim()).filter(Boolean);

    const allowedTokens = [officialToken, tutorKey, legacyToken, ...extraTokens].filter(Boolean);

    const authHeader = request.headers.get('authorization') || '';
    let providedToken = null;
    if (authHeader.startsWith('Bearer ')) {
      providedToken = authHeader.slice(7).trim();
    } else if (url.searchParams.has('key')) {
      providedToken = url.searchParams.get('key');
    } else if (url.searchParams.has('token')) {
      providedToken = url.searchParams.get('token');
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
      fallbackEngine.reset();
      fallbackXReqSeq = 0;
      return jsonResponse(200, { ok: true });
    }

    if (pathname === '/msg' && method === 'POST') {
      let rawText = '';
      try {
        const bodyArrayBuffer = await request.arrayBuffer();
        if (bodyArrayBuffer.byteLength > MAX_BODY_BYTES) {
          return jsonResponse(413, { error: 'E101', mensaje: 'cuerpo demasiado grande' });
        }
        rawText = new TextDecoder('utf-8', { fatal: true }).decode(bodyArrayBuffer);
      } catch {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (!rawText || rawText.trim().length === 0) {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      let parsed;
      try {
        parsed = JSON.parse(rawText);
      } catch {
        return jsonResponse(400, { error: 'E100', mensaje: 'json inválido' });
      }

      if (
        parsed === null ||
        typeof parsed !== 'object' ||
        Array.isArray(parsed) ||
        typeof parsed.m !== 'string'
      ) {
        return jsonResponse(400, { error: 'E102', mensaje: 'falta m' });
      }

      const sanitized = sanitizeInput(parsed.m);
      if (!sanitized.valid) {
        return jsonResponse(400, { error: sanitized.error, mensaje: sanitized.message });
      }

      const currentXReq = ++fallbackXReqSeq;
      const result = fallbackEngine.processMessage(sanitized.sanitized);
      return jsonResponse(result.status, result.body, { 'X-Req': String(currentXReq) });
    }

    return jsonResponse(404, { error: 'E404', mensaje: 'ruta desconocida' });
  },
};
