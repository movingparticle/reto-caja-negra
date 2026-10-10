/**
 * Security and Hardening Module for Reto 2 (Cloudflare Workers & Node.js)
 *
 * Implements:
 * 1. Constant-time string verification (timing-attack resistant via constant-time bitwise accumulator).
 * 2. Multi-key authorization (Evaluator Team Token + Tutor/Admin Keys).
 * 3. Body size capping (DoS protection, max 64 KiB).
 * 4. Input sanitization (null byte prevention, non-printable control characters).
 * 5. Security headers (HSTS, nosniff, no-frame, noindex).
 */

export const MAX_BODY_BYTES = 8192; // 8 KiB (exact live server limit)

export const SECURITY_HEADERS = {
  'Content-Type': 'application/json; charset=utf-8',
  'X-Content-Type-Options': 'nosniff',
  'X-Frame-Options': 'DENY',
  'Referrer-Policy': 'no-referrer',
  'X-Robots-Tag': 'noindex, nofollow',
  'Strict-Transport-Security': 'max-age=31536000; includeSubDomains',
};

/**
 * Constant-time string comparison using byte-by-byte bitwise XOR accumulation.
 * Guarantees execution time is independent of input characters, preventing timing attacks.
 */
export function timingSafeStringCompare(a, b) {
  if (typeof a !== 'string' || typeof b !== 'string') {
    return false;
  }
  const encoder = new TextEncoder();
  const aBuf = encoder.encode(a);
  const bBuf = encoder.encode(b);

  if (aBuf.byteLength !== bBuf.byteLength) {
    return false;
  }

  let mismatch = 0;
  for (let i = 0; i < aBuf.byteLength; i++) {
    mismatch |= aBuf[i] ^ bBuf[i];
  }

  return mismatch === 0;
}

/**
 * Validates whether the incoming token matches any of the authorized keys.
 * Authorized keys include:
 * - Official evaluator team token
 * - Optional tutor key / admin key
 * - Comma-separated allowlist
 */
export function isAuthorizedToken(providedToken, allowedTokens) {
  if (!providedToken || typeof providedToken !== 'string') {
    return false;
  }

  const validTokens = Array.isArray(allowedTokens)
    ? allowedTokens
    : [allowedTokens];

  for (const validToken of validTokens) {
    if (validToken && timingSafeStringCompare(providedToken, validToken)) {
      return true;
    }
  }

  return false;
}

/**
 * Hardens incoming payload string:
 * - Checks for forbidden control characters (e.g. null bytes \0).
 * - Checks max payload length.
 */
export function sanitizeInput(rawMessage) {
  if (typeof rawMessage !== 'string') {
    return { valid: false, error: 'E102', message: 'falta m' };
  }

  // Reject oversized strings (e.g. > 16 KiB for a single message string)
  if (rawMessage.length > 16384) {
    return { valid: false, error: 'E201', message: 'control mal formado' };
  }

  // Reject null bytes and hazardous control codes (ASCII 0-8, 11, 12, 14-31)
  // Allows standard tab (9), newline (10), carriage return (13) and printable text
  if (/[\x00-\x08\x0B\x0C\x0E-\x1F]/.test(rawMessage)) {
    return { valid: false, error: 'E201', message: 'control mal formado' };
  }

  return { valid: true, sanitized: rawMessage };
}
