// The Guillotine browser model (reports/assets/guillotine-model.js), 2026-11-14.
const test = require('node:test');
const assert = require('node:assert');
const G = require('../reports/assets/guillotine-model.js');

test('target: half rounded down, one in the last week', () => {
  assert.deepStrictEqual([180, 90, 45, 22].map((n, i) => G.target(n, 13 + i, 17)), [90, 45, 22, 11]);
  assert.strictEqual(G.target(11, 17, 17), 1);
});

test('cut line: k-th best', () => {
  assert.strictEqual(G.cutLine([5, 9, 7, 7, 1], 3), 7);
  assert.strictEqual(G.cutLine([], 3), null);
});

test('advance odds: certain teams, ties at the line, coin flips, stable', () => {
  // known finals: top 2 of 4 survive; the two tied at the line both survive
  assert.deepStrictEqual(G.advanceOdds([{mu: 10, sd: 0}, {mu: 8, sd: 0}, {mu: 8, sd: 0}, {mu: 1, sd: 0}], 2), [100, 100, 100, 0]);
  const even = G.advanceOdds([{mu: 100, sd: 20}, {mu: 100, sd: 20}], 1, 8000);
  assert.ok(Math.abs(even[0] - 50) < 3 && Math.abs(even[1] - 50) < 3);
  const many = Array.from({length: 180}, (_, i) => ({mu: 200 - i, sd: 24}));
  const o = G.advanceOdds(many, 90);
  assert.ok(o[0] > 99 && o[179] < 1);
  assert.ok(Math.abs(o.reduce((a, b) => a + b, 0) - 9000) < 1);  // exactly 90 survive per draw
  assert.deepStrictEqual(G.advanceOdds(many, 90), o);               // fixed seed: no flicker on refresh
});
