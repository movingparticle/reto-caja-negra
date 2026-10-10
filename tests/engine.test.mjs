import test from 'node:test';
import assert from 'node:assert/strict';
import { readFileSync } from 'node:fs';
import { resolve } from 'node:path';
import { BankingEngine } from '../src/engine.mjs';

test('Replicates all 20 examples from pruebas/ejemplos.jsonl exactly', () => {
  const filePath = resolve('pruebas/ejemplos.jsonl');
  const lines = readFileSync(filePath, 'utf-8').trim().split('\n').filter(Boolean);

  const engine = new BankingEngine();

  for (const line of lines) {
    const example = JSON.parse(line);
    const { id, request, status: expectedStatus, response: expectedResponse } = example;

    const result = engine.processMessage(request.m);

    assert.equal(
      result.status,
      expectedStatus,
      `Step ${id} failed status check: expected ${expectedStatus}, got ${result.status}`
    );

    assert.deepEqual(
      result.body,
      expectedResponse,
      `Step ${id} failed response check: expected ${JSON.stringify(expectedResponse)}, got ${JSON.stringify(result.body)}`
    );
  }
});
