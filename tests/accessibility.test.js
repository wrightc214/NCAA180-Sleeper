// Accessibility 5.8 regression tests for standalone source module and generated menu bundle.
// Loads the template with fixture data and checks the pure models the DOM step draws from.
const test = require('node:test');
const assert = require('node:assert');
const fs = require('node:fs');
const path = require('node:path');
const Module = require('node:module');

function load(data, ownerOverride) {
  const ownerColors = ownerOverride || JSON.parse(
    fs.readFileSync(path.join(__dirname, '..', 'config', 'league.json'), 'utf8')).accessibility_colors;
  const accessibilitySource = fs.readFileSync(path.join(__dirname, '..', 'templates', 'accessibility.js'), 'utf8')
    .replace('/*__OWNER_ACCESSIBILITY_COLORS__*/null', JSON.stringify(ownerColors));
  const src = fs.readFileSync(path.join(__dirname, '..', 'templates', 'menu.js'), 'utf8')
    .replace('/*__DATA__*/null', JSON.stringify(data))
    .replace('/*__ACCESSIBILITY__*/', accessibilitySource);
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

// Colour tokens (Project Manager 5.8): hard-coded Standard set + the win % diverging scale.
test('owner palette overrides propagate to Standard, neutral, custom defaults and reset', () => {
  const original = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'league.json'), 'utf8')).accessibility_colors;
  const changed = JSON.parse(JSON.stringify(original));
  changed.light.positive = '#125c39';
  changed.light.negative = '#852f32';
  changed.light.neutral = '#596a7b';
  changed.dark.positive = '#8adeb0';
  changed.dark.negative = '#ff9898';
  changed.dark.neutral = '#b5bbc5';
  const m = load(DATA, changed);
  assert.strictEqual(m.colors.defaults.light['--good'], changed.light.positive);
  assert.strictEqual(m.colors.defaults.light['--bad'], changed.light.negative);
  assert.strictEqual(m.colors.defaults.light['--neutral'], changed.light.neutral);
  assert.strictEqual(m.colors.defaults.dark['--good'], changed.dark.positive);
  assert.strictEqual(m.colors.defaults.dark['--bad'], changed.dark.negative);
  assert.strictEqual(m.colors.defaults.dark['--neutral'], changed.dark.neutral);
  assert.strictEqual(m.colors.tokens().neutral, changed.light.neutral);
  assert.strictEqual(m.access.modes.standard.light[0], changed.light.positive);
  assert.strictEqual(m.access.modes.standard.dark[1], changed.dark.negative);
  assert.strictEqual(m.access.defaults.custom.good, changed.light.positive);
  assert.strictEqual(m.access.defaults.custom.bad, changed.light.negative);
  assert.strictEqual(m.access.read().custom.good, changed.light.positive);
  assert.strictEqual(m.access.read().custom.bad, changed.light.negative);
});

test('owner Standard fills are contrast-adjusted when owner chooses pale colours', () => {
  const colors = JSON.parse(fs.readFileSync(path.join(__dirname, '..', 'config', 'league.json'), 'utf8')).accessibility_colors;
  const changed = JSON.parse(JSON.stringify(colors));
  changed.light.positive = '#ffffcc';
  changed.light.negative = '#ffdddd';
  const m = load(DATA, changed);
  const css = m.access.apply && m.colors.css;
  // Browserless mode applies its Standard palette on initial load.
  const fill = m.colors.css.match(/--good-fill:(#[0-9a-f]{6});--bad-fill:(#[0-9a-f]{6})/i);
  assert.ok(fill, 'Standard fill tokens present');
  assert.ok(m.access.contrast(fill[1], '#ffffff') >= 4.5);
  assert.ok(m.access.contrast(fill[2], '#ffffff') >= 4.5);
});

test('user custom colours remain exact even with poor contrast', () => {
  const old = global.localStorage;
  const stored = {};
  global.localStorage = {
    getItem: k => stored[k] || null,
    setItem: (k, v) => { stored[k] = v; },
    removeItem: k => { delete stored[k]; }
  };
  try {
    const m = load(DATA);
    m.access.save({mode:'custom',custom:{good:'#ffffff',bad:'#fffffe'}});
    assert.strictEqual(m.access.read().custom.good, '#ffffff');
    assert.strictEqual(m.access.read().custom.bad, '#fffffe');
    assert.match(m.colors.css, /--good:#ffffff;--bad:#fffffe;/);
    assert.match(m.colors.css, /--good-fill:#ffffff;--bad-fill:#fffffe;/);
    assert.ok(m.access.contrast('#ffffff','#fffffe') < 1.5);
  } finally {
    global.localStorage = old;
  }
});

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

test('accessibility settings: presets, custom, reset and malformed storage', () => {
  const old = global.localStorage;
  const values = {};
  global.localStorage = {
    getItem: k => values[k] ?? null,
    setItem: (k, v) => { values[k] = String(v); },
    removeItem: k => { delete values[k]; },
  };
  try {
    const access = load(DATA).access;
    assert.strictEqual(access.read().mode, 'standard');
    for (const mode of ['rg', 'by', 'none', 'custom', 'standard']) {
      access.save({mode});
      assert.strictEqual(access.read().mode, mode);
    }
    access.save({custom: {good: '#ffffff', bad: '#000000'}, motion: 'on', emphasis: true});
    assert.strictEqual(access.read().custom.good, '#ffffff');
    assert.strictEqual(access.read().motion, 'on');
    assert.strictEqual(access.read().emphasis, true);
    access.save({custom: {good: access.defaults.custom.good, bad: access.defaults.custom.bad}});
    assert.strictEqual(access.read().motion, 'on', 'custom restore does not reset motion');
    assert.ok(access.contrast('#000000', '#ffffff') >= 21 - 0.01);
    assert.ok(access.contrast(access.adjust('#ffffff', '#ffffff'), '#ffffff') >= 4.5);
    access.reset();
    assert.strictEqual(values['ncaa180.access'], undefined);
    assert.strictEqual(access.read().mode, 'standard');
    values['ncaa180.access'] = '{invalid';
    assert.strictEqual(access.read().mode, 'standard');
  } finally {
    if (old === undefined) delete global.localStorage;
    else global.localStorage = old;
  }
});

test('accessibility: no-colour uses monochrome fills and invalid settings are normalized', () => {
  const old=global.localStorage, store={};
  global.localStorage={getItem:k=>store[k]||null,setItem:(k,v)=>{store[k]=v;},removeItem:k=>{delete store[k];}};
  try {
    const m=load(DATA);
    m.access.save({mode:'none'});
    assert.match(m.colors.css, /--good-fill:#3c3c3c/);
    assert.match(m.colors.css, /--bad-fill:#656565/);
    assert.match(m.colors.css, /--n180-emphasis:1/);
    m.access.save({mode:'unrecognized',motion:'bogus',custom:{good:'red'}});
    assert.strictEqual(m.access.read().mode,'standard');
    assert.strictEqual(m.access.read().motion,'system');
    assert.strictEqual(m.access.read().custom.good,m.access.defaults.custom.good);
  } finally { if(old===undefined) delete global.localStorage; else global.localStorage=old; }
});

test('generated menu matches source template exactly except embedded navigation data', () => {
  const template = fs.readFileSync(path.join(__dirname, '..', 'templates', 'menu.js'), 'utf8');
  const built = fs.readFileSync(path.join(__dirname, '..', 'reports', 'assets', 'menu.js'), 'utf8');
  const embedded = built.match(/var D = (\{.*?\});\n  var DEV_KEY/s);
  assert.ok(embedded, 'generated menu embeds nav JSON');
  const a11y = fs.readFileSync(path.join(__dirname, '..', 'templates', 'accessibility.js'), 'utf8')
    .replace('/*__OWNER_ACCESSIBILITY_COLORS__*/null', JSON.stringify(JSON.parse(
      fs.readFileSync(path.join(__dirname, '..', 'config', 'league.json'), 'utf8')).accessibility_colors));
  assert.strictEqual(template.replace('/*__ACCESSIBILITY__*/', a11y)
    .replace('/*__DATA__*/null', embedded[1]), built);
  assert.ok(JSON.parse(embedded[1]).tabs.some(t => t.id === 'access' && t.state === 'hidden-dev'));
});

test('accessible fill and foreground contrast for all palettes in both themes', () => {
  const old = global.localStorage, values = {};
  global.localStorage = {getItem:k=>values[k]||null,setItem:(k,v)=>{values[k]=v;},removeItem:k=>{delete values[k];}};
  try {
    const m=load(DATA),a=m.access;
    for(const mode of ['standard','rg','by','none','custom']){
      a.save({mode,custom:{good:'#ffffff',bad:'#eeeeee'}});
      const css=m.colors.css;
      for(const name of ['good-fill','bad-fill']){
        const match=css.match(new RegExp('--'+name+':(#[0-9a-f]{6})'));
        assert.ok(match,mode+' '+name);
        if(mode!=='custom') assert.ok(a.contrast(match[1],'#ffffff')>=4.5,mode+' '+name+' contrast');
      }
      const light=css.match(/^:root\{([^}]*)\}/)[1];
      const dark=css.match(/:root\[data-theme=dark\]\{([^}]*)\}/)[1];
      for(const [text,bg] of [[light,'#ffffff'],[dark,'#171b22']]){
        for(const name of ['good','bad']){
          const match=text.match(new RegExp('--'+name+':(#[0-9a-f]{6})'));
          assert.ok(match,mode+' '+name);
          if(mode!=='custom') assert.ok(a.contrast(match[1],bg)>=4.5,mode+' '+name+' text contrast');
        }
      }
    }
  } finally {if(old===undefined)delete global.localStorage;else global.localStorage=old;}
});

test('Accessibility page includes shared site CSS, dev navigation and accessible controls', () => {
  const html=fs.readFileSync(path.join(__dirname,'..','reports','access.html'),'utf8');
  const weekly=fs.readFileSync(path.join(__dirname,'..','templates','weekly_report.html'),'utf8');
  const shared=weekly.match(/<style>[\s\S]*?<\/style>/)[0];
  assert.ok(html.includes(shared),'shared site stylesheet embedded');
  assert.match(html,/data-current="access" data-state="hidden-dev"/);
  assert.match(html,/src="assets\/menu\.js"/);
  assert.match(html,/src="assets\/access\.js"/);
  assert.match(html,/id="restore-custom"/);
  assert.match(html,/id="reset-all"/);
});

test('accessibility resets preserve other settings and blocked storage never crashes', () => {
  const old=global.localStorage;
  const values={'ncaa180.dev':'1','ncaa180.push':'saved','ncaa180.team':'saved'};
  try {
    global.localStorage={getItem:k=>values[k]??null,setItem:(k,v)=>{values[k]=v;},removeItem:k=>{delete values[k];}};
    const a=load(DATA).access;
    a.save({mode:'rg'});
    a.reset();
    assert.strictEqual(values['ncaa180.dev'],'1');
    assert.strictEqual(values['ncaa180.push'],'saved');
    assert.strictEqual(values['ncaa180.team'],'saved');
    global.localStorage={getItem(){throw Error('blocked');},setItem(){throw Error('blocked');},removeItem(){throw Error('blocked');}};
    const blocked=load(DATA).access;
    assert.strictEqual(blocked.read().mode,'standard');
    assert.doesNotThrow(()=>blocked.save({mode:'custom'}));
    assert.doesNotThrow(()=>blocked.reset());
  } finally {if(old===undefined)delete global.localStorage;else global.localStorage=old;}
});

test('accessibility emits change events when settings are saved or reset', () => {
  const oldWindow=global.window,oldStorage=global.localStorage, events=[],values={};
  global.window={CustomEvent:class CustomEvent {constructor(type,options){this.type=type;this.detail=options.detail;}},
    dispatchEvent:event=>events.push(event)};
  global.localStorage={getItem:k=>values[k]??null,setItem:(k,v)=>{values[k]=v;},removeItem:k=>{delete values[k];}};
  try {
    const access=load(DATA).access;
    access.save({mode:'rg'});
    assert.strictEqual(events.at(-1).type,'ncaa180:accesschange');
    assert.strictEqual(events.at(-1).detail.mode,'rg');
    access.reset();
    assert.strictEqual(events.at(-1).detail.mode,'standard');
  } finally {
    if(oldWindow===undefined)delete global.window;else global.window=oldWindow;
    if(oldStorage===undefined)delete global.localStorage;else global.localStorage=oldStorage;
  }
});

test('saved-image renderer carries live accessibility token styles', () => {
  const snapshot=fs.readFileSync(path.join(__dirname,'..','reports','assets','snapshot.js'),'utf8');
  const accessibility=fs.readFileSync(path.join(__dirname,'..','templates','accessibility.js'),'utf8');
  assert.match(snapshot,/querySelectorAll\('style,link\[rel="stylesheet"\]'\)/,
    'snapshot copies current document style elements');
  assert.match(accessibility,/var TOKENS_ID = "n180-tokens"/);
  assert.match(accessibility,/st\.textContent = css/,'accessibility colours are written to a style element');
});

test('Accessibility controls update and reset preferences without a browser', () => {
  const script=fs.readFileSync(path.join(__dirname,'..','reports','assets','access.js'),'utf8');
  let state={mode:'standard',custom:{good:'#1a7f37',bad:'#b42318'},motion:'system',emphasis:false};
  const handlers={},nodes={};
  for(const id of ['mode','good','bad','motion','emphasis','good-value','bad-value','warnings','restore-custom','reset-all']){
    nodes[id]={value:'',checked:false,disabled:false,textContent:'',
      addEventListener(type,fn){handlers[id+':'+type]=fn;}};
  }
  const copy=()=>JSON.parse(JSON.stringify(state));
  const api={read:copy,save(patch){state={...state,...patch,custom:{...state.custom,...(patch.custom||{})}};return copy();},
    reset(){state={mode:'standard',custom:{good:'#1a7f37',bad:'#b42318'},motion:'system',emphasis:false};return copy();},
    defaults:{custom:{good:'#1a7f37',bad:'#b42318'}},contrast(){return 5;}};
  const w={NCAA180:{access:api},addEventListener(type,fn){handlers['window:'+type]=fn;}};
  const d={getElementById:id=>nodes[id]};
  new Function('window','document',script)(w,d);
  nodes.mode.value='rg';handlers['mode:change'].call(nodes.mode);
  assert.strictEqual(state.mode,'rg');
  nodes.good.value='#123456';handlers['good:input'].call(nodes.good);
  assert.strictEqual(state.mode,'custom');
  assert.strictEqual(state.custom.good,'#123456');
  handlers['restore-custom:click']();
  assert.strictEqual(state.custom.good,'#1a7f37');
  assert.strictEqual(state.mode,'custom');
  handlers['reset-all:click']();
  assert.strictEqual(state.mode,'standard');
  state.mode='none';handlers['window:ncaa180:accesschange']();
  assert.strictEqual(nodes.mode.value,'none');
});
