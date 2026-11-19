'use strict';
const assert = require('node:assert/strict');
const fs = require('node:fs');
const test = require('node:test');
const vm = require('node:vm');
const Core = require('../reports/assets/selection-watch-core.js');
const Games = require('../reports/assets/selection-watch-games.js');
const page = fs.readFileSync(require.resolve('../reports/assets/selection-watch.js'), 'utf8');

function setup(baseline, settings = {}, {search='', fixtureURL, fixtureData={}, missingLive=false, liveData, scores} = {}) {
  const nodes = new Map();
  const element = id => {
    if (!nodes.has(id)) nodes.set(id, {
      textContent: '', innerHTML: '', dataset: {}, listeners: {},
      addEventListener(name, fn) { this.listeners[name] = fn; },
      insertAdjacentHTML(_, text) { this.innerHTML += text; },
      cloneNode() { return {outerHTML: '<details></details>', querySelectorAll: () => []}; },
    });
    return nodes.get(id);
  };
  const save = element('save'), seen = [], timers = [], exports = [], requests = [];
  const labels = [['title','Selection Watch']].map(([key,value]) => {
    const node = element('label-'+key);
    node.dataset.swLabel = key;
    node.textContent = value;
    return node;
  });
  element('sw-brand').textContent = 'Generated brand';
  save.dataset.save = 'sw-board';
  element('sw-content').hidden = true;
  const CCG = {id: 'ccg', a: 'conf|1', b: 'conf|4'};
  const odds = winPct => ({LeagueID: 'conf', RosterID: 1, OpponentRosterID: 4, WinPct: winPct});
  const payloads = {
    'postseason/selection-watch.json': {year: 2026, ccg_week: 12, field_size: 2, tie: [],
      order: [1, 2, 3, 4].map(rank => ({rank, k: 'conf|' + rank, team: 'Team ' + rank})), ccg: [CCG]},
    '../config/league.json': {data: {scoreboard: '/score'}, api: {espn: '/espn', sleeper: '/sleeper'},
      brand: settings.brand, refresh: settings.refresh},
    '../config/nav.json': {tabs: [{id: 'selection-watch', state: settings.state ?? 'hidden-dev'}]},
    '../config/selection_watch.json': settings.feature,
    '/score/index.json': {season: 2026, weeks: [12]},
    '/score/2026/players.json': {},
    '/espn?dates=2026&week=12&seasontype=2': {
      season: {year: 2026}, week: {number: 12}, events: [{status: {type: {state: 'pre'}}}],
    },
    '/sleeper/stats/nfl/regular/2026/12': {},
    '/sleeper/league/conf/matchups/12': [{roster_id: 1}, {roster_id: 4}],
    '/sleeper/league/conf': {scoring_settings: {}},
  };
  if (liveData) Object.assign(payloads['postseason/selection-watch.json'], liveData);
  if (fixtureURL) payloads[fixtureURL] = {...payloads['postseason/selection-watch.json'], ...fixtureData};
  if (missingLive) delete payloads['postseason/selection-watch.json'];
  const document = {
    getElementById: element, body: element('body'), hidden: false, addEventListener() {},
    querySelectorAll(selector) { return selector === '#sw-content button.sw-save' ? [save] : selector === '[data-sw-label]' ? labels : []; },
  };
  let summary = {live: false, probability: null, pregame: null, final: false, status: 'Upcoming',
    models: [{actual: 0}, {actual: 0}]};
  const ready = vm.runInNewContext(page, {
    window: {NCAA180: {menu: {dev: () => settings.dev === true}}, SelectionWatchGames: scores?{load: async()=>({scores})}:Games, ScoreboardCore: {statsMap: x => x}, ScoreboardOverview: {summarize: () => summary},
      SelectionWatchCore: {...Core, odds(d, p) { seen.push(p.ccg); return Core.odds(d, p); }}},
    document, location: {search}, URLSearchParams, AbortController,
    NCAASnap: {async save(options) { exports.push(options); }},
    setTimeout: (_, delay) => timers.push(delay), clearTimeout() {},
    async fetch(url) {
      requests.push(url);
      const body = url === '/score/2026/week-12.json' ? baseline : payloads[url];
      return {ok: body !== undefined, status: body === undefined ? 404 : 200, async json() { return body; }};
    },
  });
  return {document, element, save, seen, ready, odds, timers, exports, requests, setBaseline(value) { baseline = value; },
    setSummary(value) { summary = {...summary, ...value}; },
    refresh() { return element('sw-refresh').listeners.click(); }};
}

test('missing first-load odds cannot render or export a fabricated board', async () => {
  const h = setup({odds: []});
  await h.ready;
  assert.match(h.element('sw-error').textContent, /no verified current probabilities/);
  assert.deepEqual(h.seen, []);
  assert.equal(h.element('sw-board-rows').innerHTML, '');
  assert.equal(h.save.disabled, true);
});

test('real zero is accepted, but malformed fallback odds preserve the last verified board', async () => {
  const h = setup({odds: []});
  h.setBaseline({odds: [h.odds('0')]});
  await h.ready;
  assert.deepEqual(h.seen, [0]);
  assert.equal(h.save.disabled, false);
  const savedBoard = h.element('sw-board-rows').innerHTML;
  const savedTime = h.element('body').dataset.snapTime;
  h.setSummary({probability: 0, pregame: 0}); // Shared Games model coerces raw blanks to zero.
  for (const invalid of ['', ' ', null, false, -1, 101, 'bad']) {
    h.setBaseline({odds: [h.odds(invalid)]});
    await h.refresh();
    assert.match(h.element('sw-error').textContent, /Showing last verified data/);
    assert.equal(h.seen.at(-1), 0);
    assert.equal(h.element('sw-board-rows').innerHTML, savedBoard);
    assert.equal(h.element('body').dataset.snapTime, savedTime);
  }
});

test('live odds, modern frozen odds and reversed legacy fallback retain their priority', async () => {
  const h = setup({odds: []});
  const sides = [
    {LeagueID: 'conf', RosterID: 4, WinPct: 70},
    {LeagueID: 'conf', RosterID: 1, WinPct: 30},
  ];
  const reverse = {...h.odds('75'), RosterID: 4, OpponentRosterID: 1};
  h.setBaseline({games: [{sides}], odds: [reverse]});
  await h.ready;
  assert.equal(h.seen.at(-1), .3);
  assert.match(h.element('sw-board-rows').innerHTML,/Pregame odds/);
  assert.doesNotMatch(h.element('sw-board-rows').innerHTML,/sw-margin/);
  h.setSummary({live: true, started: true, probability: 0, models: [{actual: 90},{actual: 102.4}]});
  await h.refresh();
  assert.equal(h.seen.at(-1), 0);
  assert.match(h.element('sw-board-rows').innerHTML,/100%<\/small><small class="sw-margin"[^>]*>\+12\.4<\/small>/);
  assert.match(h.element('sw-board-rows').innerHTML,/Live odds/);
  h.setSummary({probability: null});
  sides[1].WinPct = null;
  await h.refresh();
  assert.equal(h.seen.at(-1), .25);
  assert.match(h.element('sw-board-rows').innerHTML,/Pregame fallback · live odds unavailable/);
  h.setSummary({live: false, final: true});
  await h.refresh();
  assert.match(h.element('sw-board-rows').innerHTML,/Stolen/);
  assert.doesNotMatch(h.element('sw-board-rows').innerHTML,/sw-margin/);
});

test('league settings control the live refresh cadence and the page and export brand', async () => {
  const h = setup({odds: []}, {brand: 'New League & Co.', refresh: {normal_ms: 86753},
    feature: {labels: {title: 'Playoff Tracker'}, export_filename_prefix: 'tracker'}});
  h.setBaseline({odds: [h.odds(60)]});
  await h.ready;
  assert.equal(h.timers.at(-1), 86753);
  assert.equal(h.document.title, 'Playoff Tracker | New League & Co.');
  assert.equal(h.element('sw-brand').textContent, 'New League & Co.');
  await h.save.listeners.click({stopPropagation() {}});
  assert.equal(h.exports[0].footer, 'New League & Co. Playoff Tracker');
  assert.equal(h.exports[0].name, 'tracker-sw-board');
});

const replay = {enabled: true, query: 'replay', url: 'fixtures/finished.json'};
const demo = {enabled: true, query: 'demo', url: 'fixtures/demo.json'};
const previewSettings = previews => ({feature: {previews}});

test('a configured historical route uses the fixture year and never polls the live Games model', async () => {
  const h = setup({}, previewSettings({historical: replay}), {
    search: '?preview=replay', fixtureURL: replay.url, fixtureData: {year: 2024, style: {'Team 4': {background: '#14213a'}},
      ccg: [{id: 'ccg', a: 'conf|1', b: 'conf|4', winner: 'conf|4', pa: 90, pb: 100}]},
  });
  await h.ready;
  assert.equal(h.requests[3], replay.url);
  assert.match(h.element('sw-status').innerHTML, /2024 CCG finals · Historical replay/);
  assert.ok(!h.requests.some(url => /^\/(espn|sleeper)/.test(url)));
  assert.match(h.element('sw-updated').textContent, /Historical replay/);
  assert.equal(h.document.body.dataset.snapTime, undefined);
  assert.match(h.element('sw-board-rows').innerHTML, /sw-team admitted[^>]*--team-fill:#14213a;--team-ink:#fff/);
  assert.match(h.element('sw-board-rows').innerHTML, /sw-team dim/);
  await h.save.listeners.click({stopPropagation() {}});
  assert.equal(h.exports[0].stamp.time, null);
  assert.match(h.exports[0].stamp.note, /Historical replay/);
});

test('missing, disabled and ambiguous preview settings never fetch a fixture or fall through to live', async () => {
  for (const settings of [{}, previewSettings({historical: {...replay, enabled: false}}),
    previewSettings({historical: {...replay, url: ''}}),
    previewSettings({historical: replay, provisional: {...demo, query: replay.query}})]) {
    const h = setup({}, settings, {search: '?preview=replay'});
    await h.ready;
    assert.match(h.element('sw-error').textContent, /Unknown or disabled preview/);
    assert.deepEqual(h.requests, ['../config/nav.json', '../config/selection_watch.json', '../config/league.json']);
  }
});

test('provisional disclosures survive relabeling and the live and historical routes reject provisional data', async () => {
  const settings = previewSettings({historical: replay, provisional: demo});
  const h = setup({}, settings, {search: '?preview=demo', fixtureURL: demo.url, fixtureData: {provisional: true}});
  await h.ready;
  assert.match(h.element('sw-status').innerHTML, /PROVISIONAL · UNOFFICIAL/);
  assert.doesNotMatch(h.element('sw-board-rows').innerHTML, /View game|scoreboard\.html/);
  assert.doesNotMatch(h.element('sw-noimpact-rows').innerHTML, /View game|scoreboard\.html/);
  await h.save.listeners.click({stopPropagation() {}});
  assert.equal(h.exports[0].stamp.note, 'PROVISIONAL');
  assert.doesNotMatch(h.exports[0].footer, /Unofficial/i);

  for (const [search, fixtureURL, pattern] of [
    ['', 'postseason/selection-watch.json', /Provisional data.*live page/],
    ['?preview=replay', replay.url, /Provisional data.*historical preview/],
    ['?preview=demo', demo.url, /missing PROVISIONAL label/],
  ]) {
    const bad = setup({}, settings, {search, fixtureURL, fixtureData: {provisional: search !== '?preview=demo'}});
    await bad.ready;
    assert.match(bad.element('sw-error').textContent, pattern);
    assert.equal(bad.requests.length, 4);
  }
});

test('hidden nav state stops direct and preview loads before any other requests', async () => {
  for (const search of ['', '?preview=demo']) {
    const h = setup({}, {state: 'hidden', feature: {previews: {provisional: demo}}}, {search});
    await h.ready;
    assert.deepEqual(h.requests, ['../config/nav.json']);
    assert.equal(h.element('sw-content').hidden, true);
    assert.match(h.element('sw-error').textContent, /disabled/);
  }
});

test('the unpublished live board has a friendly configurable message', async () => {
  for (const availability_message of [undefined, 'Check back Tuesday.']) {
    const h = setup({}, {feature: {availability_message}}, {missingLive: true});
    await h.ready;
    assert.equal(h.element('sw-content').hidden, true);
    assert.equal(h.element('sw-error').textContent,
      availability_message || 'Available after the regular season is final.');
    assert.equal(h.requests.at(-1), 'postseason/selection-watch.json');
  }
});


test('what-if uses a reversible probability and stamps it into saves', async () => {
  const settings={dev:false};
  const h=setup({odds:[]},settings);
  h.setBaseline({odds:[h.odds(60)]});
  await h.ready;
  assert.equal(h.element('sw-discord-draft').hidden,true);
  await h.element('sw-discord-draft').listeners.click();
  assert.equal(h.exports.length,0);
  settings.dev=true;
  await h.refresh();
  assert.equal(h.element('sw-discord-draft').hidden,false);
  h.element('sw-picks').listeners.change({target:{dataset:{game:'ccg'},value:'conf|4'}});
  assert.equal(h.seen.at(-1),0);
  assert.match(h.element('sw-whatif-banner').textContent,/WHAT-IF.*Team 4 wins/);
  assert.equal(h.element('sw-discord-draft').disabled,true);
  await h.save.listeners.click({stopPropagation() {}});
  assert.equal(h.exports.at(-1).whatif[0],'Team 4 wins');
  h.element('sw-reset-picks').listeners.click();
  assert.equal(h.seen.at(-1),.6);
  assert.equal(h.element('sw-whatif-banner').hidden,true);
  await h.element('sw-discord-draft').listeners.click();
  assert.match(h.exports.at(-1).html,/Held for owner approval/);
  settings.dev=false;
  const count=h.exports.length;
  await h.element('sw-discord-draft').listeners.click();
  assert.equal(h.exports.length,count);
});

test('What-if shows a held pair or placard while the natural team is leading, then a Saved final', async () => {
  for(const outside of [true,false]){
    const key=i=>'conf|'+i;
    const b=outside?6:3;
    const scores={
      x:{pA:.7,source:'Pregame odds'},
      y:{pA:.7,source:'Pregame odds'},
      ccg:{pA:.7,leader:key(4),live:true,scoreA:127.4,scoreB:115,source:'Live odds'},
    };
    const h=setup({}, {}, {scores,liveData:{
      field_size:5,play_ins:[],
      order:Array.from({length:9},(_,i)=>({k:key(i+1),rank:i+1,team:'Team '+(i+1),conf:'Example'})),
      ccg:[{id:'x',a:key(1),b:key(8)},{id:'y',a:key(2),b:key(9)},{id:'ccg',a:key(4),b:key(b)}],
    }});
    await h.ready;
    const pick=(game,value)=>h.element('sw-picks').listeners.change({target:{dataset:{game},value:key(value)}});
    const board=()=>h.element('sw-board-rows').innerHTML;
    assert.doesNotMatch(board(),/data-held/);
    pick('x',8);
    pick('y',9);
    assert.match(h.element('sw-whatif-banner').textContent,/WHAT-IF/);
    if(outside) {
      assert.match(board(),/data-held="pair"[^]*data-thief="conf\|6"[^]*Example CCG · Team 4 leads</);
    } else {
      assert.match(board(),/data-held="placard"[^]*Example CCG · Team 4 leads — a win keeps this spot/);
    }
    pick('ccg',4);
    assert.match(board(),/Saved/);
    assert.match(board(),/Example Champion/);
    if(outside){
      pick('ccg',6);
      assert.doesNotMatch(board(),/data-held="pair"/);
      assert.match(board(),/data-thief="conf\|6"[^]*Stolen/);
    }
  }
});
