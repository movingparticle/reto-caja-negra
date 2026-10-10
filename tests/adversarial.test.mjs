import test from 'node:test';
import assert from 'node:assert/strict';
import { BankingEngine } from '../src/engine.mjs';
import { calculateControl } from '../src/checksum.mjs';

function msg(payload) {
  const ctrl = calculateControl(payload);
  return `${payload};${ctrl}`;
}

test('Adversarial Test Suite: Probed Invariants & Exact Precedence', () => {
  const engine = new BankingEngine();

  // 1. Arity checks (E302)
  assert.equal(engine.processMessage(msg('PING;extra')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('ALTA')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('ALTA;A;B')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('CONSULTA')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('CONSULTA;A;B')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0002')).body.error, 'E302');
  assert.equal(engine.processMessage(msg('ANULA')).body.error, 'E302');

  // 2. Unknown command (E301)
  const unknownRes = engine.processMessage(msg('UNKNOWN;123'));
  assert.equal(unknownRes.status, 400);
  assert.equal(unknownRes.body.error, 'E301');
  assert.equal(unknownRes.body.mensaje, 'comando desconocido ');

  // 3. Monto checks (E303)
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001;0')).body.error, 'E303');
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001;-100')).body.error, 'E303');
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001;abc')).body.error, 'E303');
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001;0100')).body.error, 'E303'); // leading zero forbidden
  assert.equal(engine.processMessage(msg('DEPOSITO;AC-0001;10000000000')).body.error, 'E303'); // 11 digits forbidden
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0002;0')).body.error, 'E303');
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0002;-50')).body.error, 'E303');
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0002;050')).body.error, 'E303');

  // Verify ISO 7064 Mod 97-10 check digit 97 invariant (not 0)
  assert.equal(calculateControl('DEPOSITO;AC-0002;2147483647'), 97);

  // 4. Same origin and destination (E304)
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0001;500')).body.error, 'E304');

  // 5. Precedence tests:
  // Same account + invalid monto -> E303 takes precedence over E304
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0001;0')).body.error, 'E303');

  // Same account + limit exceeded -> E304 takes precedence over E506
  assert.equal(engine.processMessage(msg('TRANSFER;AC-0001;AC-0001;150000')).body.error, 'E304');

  // Non-existent account + limit exceeded -> E401 takes precedence over E506
  assert.equal(engine.processMessage(msg('TRANSFER;AC-9999;AC-8888;150000')).body.error, 'E401');

  // 6. Account creation and case sensitivity
  const a1 = engine.processMessage(msg('ALTA;Alice'));
  const a2 = engine.processMessage(msg('ALTA;Bob'));
  assert.equal(a1.body.cuentaId, 'AC-0001');
  assert.equal(a2.body.cuentaId, 'AC-0002');

  // Lowercase account ID -> 404 E401
  assert.equal(engine.processMessage(msg('CONSULTA;ac-0001')).status, 404);
  assert.equal(engine.processMessage(msg('CONSULTA;ac-0001')).body.error, 'E401');

  // 7. Deposit and transfers
  engine.processMessage(msg('DEPOSITO;AC-0001;500'));
  engine.processMessage(msg('TRANSFER;AC-0001;AC-0002;400'));

  // AC-0001 has 100 left
  assert.equal(engine.processMessage(msg('CONSULTA;AC-0001')).body.saldo, 100);

  // Annul deposit OP-0001 -> AC-0001 balance becomes -400!
  const anulaDep = engine.processMessage(msg('ANULA;OP-0001'));
  assert.equal(anulaDep.status, 200);
  assert.equal(anulaDep.body.ok, true);
  assert.equal(engine.processMessage(msg('CONSULTA;AC-0001')).body.saldo, -400);

  // Re-annul OP-0001 -> returns ya anulada
  const reAnula = engine.processMessage(msg('ANULA;OP-0001'));
  assert.equal(reAnula.status, 200);
  assert.equal(reAnula.body.ok, false);
  assert.equal(reAnula.body.motivo, 'ya anulada');

  // 8. Annul non-existent operation -> 404 E402
  const anulaNoOp = engine.processMessage(msg('ANULA;OP-9999'));
  assert.equal(anulaNoOp.status, 404);
  assert.equal(anulaNoOp.body.error, 'E402');
  assert.equal(anulaNoOp.body.mensaje, 'operación inexistente');

  // 9. Reset
  engine.reset();
  const fresh = engine.processMessage(msg('ALTA;Fresh'));
  assert.equal(fresh.body.cuentaId, 'AC-0001');
});
