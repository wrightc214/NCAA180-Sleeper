// Team pages (task 5.20): season matching in the browser twin (reports/assets/team-link.js).
// Same cases as tests/test_team_pages.py (tests/fixtures/team_link_cases.json): renamed school,
// manager change on the same roster, a season where the roster didn't exist.
const test = require('node:test');
const assert = require('node:assert');
const path = require('path');
const L = require('../reports/assets/team-link.js');
const F = require(path.join(__dirname, 'fixtures', 'team_link_cases.json'));

test('season key = league name + roster ID', () => {
  for (const [[lg, r], want] of F.season_key) assert.strictEqual(L.seasonKey(lg, r), want);
});

test('a team seen in any season resolves to this season by league name + roster', () => {
  for (const c of F.current_team) {
    const got = L.currentTeam(F.index, c.in);
    assert.deepStrictEqual(got ? [got.league, got.roster] : null, c.out, c._case);
  }
});

test('seasons matched: renamed school and manager change keep the key; missing seasons drop out', () => {
  const kb = F.matching_seasons.keys_by_year;
  for (const [[lg, r], want] of F.matching_seasons.cases) assert.deepStrictEqual(L.matchingSeasons(L.seasonKey(lg, r), kb), want);
});

test('links follow the team tab state: hidden-dev shows only with Dev view on', () => {
  const tabs = state => ({NCAA180: {menu: {data: {tabs: state ? [{id: 'team', state}] : []}, dev: () => devOn}}});
  let devOn = false;
  const load = root => { delete require.cache[require.resolve('../reports/assets/team-link.js')];
    globalThis.self = root; try { return require('../reports/assets/team-link.js'); } finally { delete globalThis.self; } };
  let M = load(tabs('hidden-dev'));
  assert.strictEqual(M.wrap('X', 'L', '4'), 'X');
  devOn = true;
  assert.strictEqual(M.wrap('X', 'L', '4'), '<a class="team-link" href="team.html?league=L&roster=4">X</a>');
  devOn = false;
  M = load({NCAA180: {menu: {data: {tabs: [{id: 'team'}]}, dev: () => false}}});
  assert.ok(M.on(), 'visible tab: links for everyone');
  M = load(tabs(null));
  assert.ok(!M.on(), 'no team tab: no links');
  assert.strictEqual(M.href('1331', '4.0'), 'team.html?league=1331&roster=4');
});
