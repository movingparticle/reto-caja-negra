/**
 * Sugerencia de comando (feature del oráculo en E301).
 *
 * Cuando el comando no existe, el oráculo devuelve un campo adicional
 * `sugerencia` con el comando conocido más cercano (distancia de Levenshtein
 * <= 2). Si no hay ninguno suficientemente cercano, omite el campo.
 *
 * Evidencia (tools/probe_suggestion.py, tools/probe_threshold.py):
 *   - "ALTXX"  -> sugerencia "ALTA"   (distancia 2)
 *   - "ALTXXX" -> sin sugerencia      (distancia 3)
 *   - "ATLB"   -> sin sugerencia      (Levenshtein 3; Damerau 2) => métrica = Levenshtein
 *   - "AAT"    -> "ALTA" (empate ALTA/HALT resuelto por orden de inserción)
 *
 * El orden de la lista define el desempate (primer mínimo).
 */

export const KNOWN_COMMANDS = [
  'PING',
  'ALTA',
  'CONSULTA',
  'DEPOSITO',
  'TRANSFER',
  'ANULA',
  'HALT',
];

export function levenshtein(a, b) {
  const m = a.length;
  const n = b.length;
  const prev = new Array(n + 1);
  const curr = new Array(n + 1);
  for (let j = 0; j <= n; j++) prev[j] = j;
  for (let i = 1; i <= m; i++) {
    curr[0] = i;
    for (let j = 1; j <= n; j++) {
      const cost = a[i - 1] === b[j - 1] ? 0 : 1;
      curr[j] = Math.min(prev[j] + 1, curr[j - 1] + 1, prev[j - 1] + cost);
    }
    for (let j = 0; j <= n; j++) prev[j] = curr[j];
  }
  return prev[n];
}

export function suggestCommand(command) {
  if (typeof command !== 'string') return null;
  const upper = command.toUpperCase();
  let best = null;
  let bestDist = Infinity;
  for (const known of KNOWN_COMMANDS) {
    const d = levenshtein(upper, known);
    if (d < bestDist) {
      bestDist = d;
      best = known;
    }
  }
  return bestDist <= 2 ? best : null;
}
