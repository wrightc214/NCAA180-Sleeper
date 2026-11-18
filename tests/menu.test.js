// Shared site menu renderer (templates/menu.js -> reports/assets/menu.js), 2026-11-17.
// Loads the template with fixture data and checks the pure models the DOM step draws from.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');

function load(data) {
  const src = fs.readFileSync(path.join(__dirname, '..', 'templates', 'menu.js'), 'utf8')
    .replace('/*__DATA__*/null', JSON.stringify(data));
  const m = new Module('menu-fixture');
  m._compile(src, 'menu-fixture.js');
  return m.exports;
}

const DATA = {
  awards: 'week-10.html',
  tabs: [
    {id: 'awards', label: 'Awards', href: 'week-10.html'},
    {id: 'standings', label: 'Standings', href: 'standings.html'},
    {id: 'poll', label: 'Poll', href: 'poll.html', aliases: ['poll-how', 'poll-bots']},
    {id: 'watch', label: 'Selection Watch', href: 'selection-watch.html', state: 'hidden-dev'},
    {id: 'app', label: 'Notification settings', href: 'app.html', icon: 'bell'},
  ],
  rows: {
    'awards-seasons': {label: 'Season', aria: 'Seasons', items: [
      {label: '2025', href: 'week-2025-11.html', match: '^week-2025-\\d+\\.html$'},
      {label: '2026', href: 'week-10.html', match: '^week-\\d{2}\\.html$'}]},
    'awards-weeks-2026': {label: 'Week', aria: 'Weeks', min: 2, items: [
      {label: 'Wk 1', href: 'week-01.html'}, {label: 'Wk 2', href: 'week-02.html'}]},
    'awards-weeks-2019': {label: 'Week', aria: 'Weeks', min: 2, items: [{label: 'Wk 1', href: 'week-2019-01.html'}]},
    'projection-archive': {label: 'Projection', aria: 'Projection archive', min: 2, items: [
      {label: 'After wk 9', href: 'postseason-proj-wk09.html'},
      {label: 'After wk 10', href: 'postseason-proj-wk10.html', match: '^postseason(-proj-wk10)?\\.html$'}]},
    'special': {label: 'Event', aria: 'Special events', items: [
      {label: 'The Guillotine', href: 'special.html', icon: '../assets/logos/G.png'},
      {label: 'Dwight Fight', href: 'dwight.html', state: 'hidden-dev'}]},
  },
};
const M = load(DATA);
const cur = (list) => list.filter((x) => x.current).map((x) => x.label);

test('main tabs: order, highlight by id and alias, bell last', () => {
  assert.deepStrictEqual(M.mainModel('standings', false).map((t) => t.label), ['Awards', 'Standings', 'Poll', 'Notification settings']);
  assert.deepStrictEqual(cur(M.mainModel('awards', false)), ['Awards']);
  assert.deepStrictEqual(cur(M.mainModel('poll-how', false)), ['Poll']);
  assert.deepStrictEqual(cur(M.mainModel('app', false)), ['Notification settings']);
  assert.strictEqual(M.mainModel('awards', false).at(-1).bell, true);
  assert.deepStrictEqual(cur(M.mainModel('about', false)), []);  // About: hidden, no tab lit
});

test('Awards tab points at the latest week', () => {
  assert.strictEqual(M.mainModel('awards', false)[0].href, 'week-10.html');
});

test('states: hidden-dev only with Dev view; hidden never in the data', () => {
  assert.ok(!M.mainModel('awards', false).some((t) => t.label === 'Selection Watch'));
  const dev = M.mainModel('awards', true).find((t) => t.label === 'Selection Watch');
  assert.strictEqual(dev.state, 'hidden-dev');
  assert.deepStrictEqual(M.rowModel('special', false, 'special.html').items.map((i) => i.label), ['The Guillotine']);
  assert.deepStrictEqual(M.rowModel('special', true, 'special.html').items.map((i) => i.label), ['The Guillotine', 'Dwight Fight']);
});

test('sub-rows: highlight by file, season match patterns, minimum length', () => {
  assert.deepStrictEqual(cur(M.rowModel('awards-seasons', false, 'week-2025-04.html').items), ['2025']);
  assert.deepStrictEqual(cur(M.rowModel('awards-seasons', false, 'week-03.html').items), ['2026']);
  assert.deepStrictEqual(cur(M.rowModel('awards-weeks-2026', false, 'week-02.html').items), ['Wk 2']);
  assert.strictEqual(M.rowModel('awards-weeks-2019', false, 'week-2019-01.html'), null);  // one week: no row
  assert.deepStrictEqual(cur(M.rowModel('projection-archive', false, 'postseason.html').items), ['After wk 10']);
  assert.deepStrictEqual(cur(M.rowModel('projection-archive', false, 'postseason-proj-wk09.html').items), ['After wk 9']);
  assert.strictEqual(M.rowModel('nope', false, 'x.html'), null);
  assert.strictEqual(M.rowModel('special', false, 'special.html').items[0].icon, '../assets/logos/G.png');
});

test('DEV bar: only with Dev view, only on non-public pages', () => {
  assert.strictEqual(M.needsBar('watch', null, false), false);
  assert.strictEqual(M.needsBar('watch', null, true), true);           // hidden-dev tab
  assert.strictEqual(M.needsBar('standings', null, true), false);      // public
  assert.strictEqual(M.needsBar('about', 'hidden', true), true);       // hidden page: state baked in the page
  assert.strictEqual(M.needsBar('standings', 'hidden', true), false);  // promoted to visible: menu wins over a stale page
});

test('generated reports/assets/menu.js parses and carries no hidden tabs', () => {
  const src = fs.readFileSync(path.join(__dirname, '..', 'reports', 'assets', 'menu.js'), 'utf8');
  const m = new Module('menu-built');
  m._compile(src, 'menu-built.js');
  const tabs = m.exports.data.tabs;
  assert.ok(tabs.length > 0);
  assert.ok(!tabs.some((t) => t.state === 'hidden'));
  assert.ok(!src.includes('about.html'), 'hidden About page must not appear in the public menu file');
});

// Colour tokens (Project Manager 5.8): hard-coded Standard set + the win % diverging scale.
test('colour tokens: css carries light, dark and fill sets', () => {
  const c = load(DATA).colors;
  assert.match(c.css, /^:root\{--good:#1a7f37;--bad:#b42318;--neutral:#6b7484;/);
  assert.match(c.css, /--good-fill:#1a7f37;--bad-fill:#b42318;--on-fill:#ffffff;/);
  assert.match(c.css, /prefers-color-scheme:dark\)\{:root:not\(\[data-theme=light\]\)\{--good:#4fc785;/);
  assert.match(c.css, /:root\[data-theme=dark\]\{--good:#4fc785;/);
});

test('colour scale: ends are the tokens, 50% is neutral, monotonic, clamps', () => {
  const c = load(DATA).colors;
  const t = {good: '#1a7f37', bad: '#b42318', neutral: '#6b7484'};
  const rgb = h => 'rgb(' + [1, 3, 5].map(i => parseInt(h.slice(i, i + 2), 16)).join(',') + ')';
  const near = (a, b) => { const x = a.match(/\d+/g).map(Number), y = b.match(/\d+/g).map(Number);
    return x.every((v, i) => Math.abs(v - y[i]) <= 1); };
  assert.ok(near(c.scale(1, t), rgb(t.good)));
  assert.ok(near(c.scale(0, t), rgb(t.bad)));
  assert.ok(near(c.scale(0.5, t), rgb(t.neutral)));
  assert.strictEqual(c.scale(1.7, t), c.scale(1, t));
  assert.strictEqual(c.scale(-3, t), c.scale(0, t));
  assert.strictEqual(c.scale('x', t), t.neutral);
  // further from 50% = further from the neutral grey, both directions
  const n = rgb(t.neutral).match(/\d+/g).map(Number);
  const d = p => Math.hypot(...c.scale(p, t).match(/\d+/g).map((v, i) => v - n[i]));
  for (const [a, b] of [[0.55, 0.7], [0.7, 0.85], [0.85, 1], [0.45, 0.3], [0.3, 0.15], [0.15, 0]])
    assert.ok(d(a) < d(b), `${a} vs ${b}`);
});


test('legacy movement tokens bridge to good/bad in light and both dark theme selectors', () => {
  const css = load(DATA).colors.css;
  const pair = '--up:var(--good);--dn:var(--bad)';
  assert.ok(css.includes(':root{' + pair + '}'));
  assert.ok(css.includes('@media (prefers-color-scheme:dark){:root:not([data-theme=light]){' + pair + '}}'));
  assert.ok(css.includes(':root[data-theme=dark]{' + pair + '}'));
});
