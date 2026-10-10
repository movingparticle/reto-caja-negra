/**
 * ISO 7064 Mod 97-10 Checksum Algorithm for Reto 2
 *
 * Specification:
 * 1. Payload is converted to uppercase.
 * 2. Letters A-Z map to 1..26 without padding (A=1, B=2, ..., I=9, J=10, ..., Z=26).
 * 3. Digits '0'-'9' remain 0..9.
 * 4. All other characters (e.g. ';', '-', accents, spaces) are omitted.
 * 5. The resulting digits form a large decimal number N.
 * 6. Control check digits: CD = (98 - (N * 100)) % 97.
 *    Equivalently: CD = (98 - ((N % 97) * 3)) % 97.
 */

export function calculateControl(payload) {
  let rem = 0n;
  const upper = payload.toUpperCase();

  for (let i = 0; i < upper.length; i++) {
    const code = upper.charCodeAt(i);
    if (code >= 65 && code <= 90) {
      // 'A' - 'Z' -> 1 - 26
      const val = code - 64; // 1 to 26
      if (val >= 10) {
        rem = (rem * 100n + BigInt(val)) % 97n;
      } else {
        rem = (rem * 10n + BigInt(val)) % 97n;
      }
    } else if (code >= 48 && code <= 57) {
      // '0' - '9'
      const val = code - 48;
      rem = (rem * 10n + BigInt(val)) % 97n;
    }
  }

  const control = Number(98n - ((rem * 3n) % 97n));
  return control;
}

export function validateControl(rawMessage) {
  // Check for semicolon existence
  const lastSemi = rawMessage.lastIndexOf(';');
  if (lastSemi === -1) {
    return { valid: false, error: 'E103', message: 'falta control' };
  }

  // Check for any empty segments in the entire message
  const parts = rawMessage.split(';');
  if (parts.some(p => p.length === 0)) {
    return { valid: false, error: 'E104', message: 'segmento vacío' };
  }

  const payload = rawMessage.slice(0, lastSemi);
  const rawControl = rawMessage.slice(lastSemi + 1);

  // Check if control is purely 1 or 2 digits (no signs, no characters, max 2 digits)
  if (!/^\d{1,2}$/.test(rawControl)) {
    return { valid: false, error: 'E201', message: 'control mal formado' };
  }

  const controlNum = parseInt(rawControl, 10);
  const expectedControl = calculateControl(payload);

  // Strict string comparison to reject leading zeros (e.g. "03" !== "3")
  if (rawControl !== String(expectedControl)) {
    return { valid: false, error: 'E202', message: 'control inválido', expectedControl };
  }

  return { valid: true, payload, control: controlNum };
}
