import test from 'node:test';
import assert from 'node:assert/strict';
import { calculateControl, validateControl } from '../src/checksum.mjs';

test('calculateControl matches all 16 sample inputs', () => {
  const samples = [
    ['PING', 64],
    ['ALTA;Lucia', 82],
    ['ALTA;Mateo', 3],
    ['CONSULTA;AC-0001', 14],
    ['DEPOSITO;AC-0001;250000', 86],
    ['TRANSFER;AC-0001;AC-0002;40000', 86],
    ['CONSULTA;AC-0002', 11],
    ['TRANSFER;AC-0001;AC-0002;120000', 55],
    ['TRANSFER;AC-0001;AC-0002;100000', 12],
    ['CONSULTa;AC-0001', 14],
    ['SALDOS;AC-0001', 38],
    ['ANULA;OP-0003', 66],
    ['CONSULTA;AC-0009', 87],
    ['TRANSFER;AC-0002;AC-0001;50000', 23],
    ['DEPOSITO;AC-0002;700', 35],
    ['ALTA;Lucia;Gomez', 11],
  ];

  for (const [payload, expected] of samples) {
    const computed = calculateControl(payload);
    assert.equal(computed, expected, `Failed for payload: ${payload}`);
  }
});

test('validateControl verifies correct control', () => {
  const res = validateControl('ALTA;Lucia;82');
  assert.equal(res.valid, true);
  assert.equal(res.payload, 'ALTA;Lucia');
  assert.equal(res.control, 82);
});

test('validateControl rejects invalid control with E202', () => {
  const res = validateControl('ALTA;Lucia;83');
  assert.equal(res.valid, false);
  assert.equal(res.error, 'E202');
  assert.equal(res.message, 'control inválido');
});

test('validateControl rejects malformed control with E201', () => {
  const res = validateControl('DEPOSITO;AC-0002;700;5X');
  assert.equal(res.valid, false);
  assert.equal(res.error, 'E201');
  assert.equal(res.message, 'control mal formado');
});

test('validateControl rejects missing control with E103', () => {
  const res = validateControl('PING');
  assert.equal(res.valid, false);
  assert.equal(res.error, 'E103');
  assert.equal(res.message, 'falta control');
});

test('validateControl rejects empty segments with E104', () => {
  const res = validateControl('ALTA;;82');
  assert.equal(res.valid, false);
  assert.equal(res.error, 'E104');
  assert.equal(res.message, 'segmento vacío');
});

test('validateControl rejects leading zeroes in control (e.g. 03 vs 3)', () => {
  const res = validateControl('ALTA;Mateo;03');
  assert.equal(res.valid, false);
  assert.equal(res.error, 'E202');
});
