// Shared trophy component, browser twin (reports/assets/trophy.js), task 5.1.
// Python parity over the whole ledger: tests/test_trophies.py.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('fs');
const path = require('path');
const T = require('../reports/assets/trophy.js');

const root = path.join(__dirname, '..');
const read = p => JSON.parse(fs.readFileSync(path.join(root, p), 'utf8'));
T.init({config: read('config/trophies.json'), league: read('config/league.json'), metrics: read('assets/fonts/barlow-trophy-metrics.json')});

test('two plaque lines: team, then "<year> <event>"', () => {
  const cases = [
    [{EventType: 'CCG', Conference: 'Big Sky'}, 'Montana State', 2026, '2026 Big Sky Champion'],
    [{EventType: 'Bowl', Event: 'Gator Bowl'}, 'Clemson', 2026, '2026 Gator Bowl'],
    [{EventType: 'PlayoffRound', Event: 'Rose Bowl', Round: 'Final Four'}, 'Arizona State', 2026, '2026 Rose Bowl · Final Four'],
    [{EventType: 'NationalTitle'}, 'Arizona State', 2026, '2026 National Champion'],
    [{EventType: 'NIT'}, 'Tuskegee', 2026, '2026 NIT Champion'],
  ];
  for (const [ev, team, year, l2] of cases) {
    const en = T.engraving(ev, team, year);
    assert.deepStrictEqual([en.line1, en.line2], [team, l2]);
  }
  assert.strictEqual(T.engraving({EventType: 'CCG', Conference: 'Big Sky'}, 'Montana State', 2026).alt,
    '2026 Big Sky Championship trophy, won by Montana State');
});

test('default plaque box and the Dwight Fight override', () => {
  assert.deepStrictEqual(T.engraving({EventType: 'NIT'}, 'X', 2026).box, {left: 23.33, top: 76.16, width: 53.33, height: 13.33});
  const d = T.engraving({EventType: 'DwightFight'}, 'Arizona State', 2026);
  assert.strictEqual(d.color, '#4a260d');
  assert.deepStrictEqual([d.box.left, d.box.top], [24.6, 82.5]);
});

test('html: art + engraved text, alt, lazy, and a fallback for missing art', () => {
  const h = T.html({EventType: 'Bowl', Event: 'Gator Bowl'}, 'Clemson', 2026, null, {width: 200});
  assert.match(h, /src="\.\.\/assets\/trophies\/bowls\/Gator%20Bowl\.png"/);
  assert.match(h, /alt="2026 Gator Bowl trophy, won by Clemson"/);
  assert.match(h, /class="tp-1"[^>]*>Clemson</);
  assert.match(h, /class="tp-2 tp-up"[^>]*>2026 Gator Bowl</);
  assert.match(h, /loading="lazy"/);
  assert.match(h, /onerror=/);  // swaps to data-fallback if the file is missing
  const fb = h.match(/data-fallback="([^"]*)"/)[1].replace(/&quot;/g, '"').replace(/&lt;/g, '<').replace(/&gt;/g, '>').replace(/&amp;/g, '&');
  assert.match(fb, /class="trophy fallback/);
  assert.match(fb, /2026 Gator Bowl/);
  assert.doesNotMatch(fb, /src="[^"]*assets\/trophies\//);  // data-art names it; no <img> of the missing file
});

test('sizes only shrink: long names get smaller text, never wider than the box', () => {
  const s = T.engraving({EventType: 'Bowl', Event: 'Gator Bowl'}, 'Ole', 2026);
  const l = T.engraving({EventType: 'Bowl', Event: 'Gator Bowl'}, 'Mississippi Valley State', 2026);
  assert.ok(l.size1 < s.size1);
  assert.ok(s.size1 <= s.box.height * 0.4);
});

test('ledger CSV parser', () => {
  const rows = T.parseCsv('﻿Season,Team\r\n2025,"Texas A&M, ""TAMU"""\n\n2026,Army\n');
  assert.deepStrictEqual(rows, [{Season: '2025', Team: 'Texas A&M, "TAMU"'}, {Season: '2026', Team: 'Army'}]);
});
