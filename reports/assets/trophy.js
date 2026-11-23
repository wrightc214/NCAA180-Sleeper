/* trophy.js -- the shared trophy component for pages that draw in the browser (task 5.1).
 * Twin of scripts/trophies.py (engraving(), trophy_html()); tests/test_trophies.py checks that both
 * produce the same text, box and fitted sizes for the same row.
 *
 *   await NCAATrophy.load('../')                       config/trophies.json + font metrics + bowl aliases
 *   NCAATrophy.html(event, winner, year, line2, opts)  <figure> markup (opts: width, prefix, cls, lazy)
 *   NCAATrophy.engraving(event, winner, year, line2)   {line1, line2, box, size1, size2, color, alt, art, ...}
 *   NCAATrophy.init({config, league, metrics})          synchronous setup (tests / pre-fetched data)
 *
 * event: a ledger row ({Season, EventType, Event, Round, Team, Conference}) or an EventType string.
 * The plaque is HTML text over the art in percentages of the image, sized in cqw (crisp at any size,
 * readable by screen readers, captured by Save image). A missing art file swaps to the event's generic
 * stand-in art, then to the fallback block.
 */
(function (root, factory) {
  const api = factory();
  if (typeof module === 'object' && module.exports) module.exports = api;
  else root.NCAATrophy = api;
})(typeof self !== 'undefined' ? self : this, function () {
  'use strict';
  const LINE_HEIGHT = 1.15, LETTER_SPACING = -0.02, SAFETY = 1.03;
  const FALLBACK_BOX = {left: 0, top: 0, width: 100, height: 25};
  let C = null, M = null, BOWL_ART = {}, APPROVED = new Set();
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const clean = o => Object.fromEntries(Object.entries(o || {}).filter(([k]) => !k.startsWith('_')));
  const floor = (x, nd) => Math.floor(x * 10 ** nd) / 10 ** nd;
  const fmt = (tpl, d) => String(tpl).replace(/\{(\w+)\}/g, (_, k) => d[k] ?? '').trim();

  function init({config, league, metrics}) {
    C = config; M = metrics;
    const bowls = (league && league.postseason && league.postseason.bowls) || {};
    BOWL_ART = {...clean(bowls.history_names), ...clean(config.bowl_art)};
    APPROVED = new Set(bowls.approved_logos || []);
    return api;
  }
  async function load(base = '../') {
    if (C) return api;
    const get = async p => { const r = await fetch(base + p, {cache: 'no-cache'}); if (!r.ok) throw Error(p + ' HTTP ' + r.status); return r.json(); };
    const [config, league, metrics] = await Promise.all([get('config/trophies.json'), get('config/league.json'),
      get('assets/fonts/barlow-trophy-metrics.json')]);
    return init({config, league, metrics});
  }
  function row(event, winner, year) {
    const r = event && typeof event === 'object' ? {...event} : {EventType: String(event)};
    if (winner != null) r.Team = winner;
    if (year != null) r.Season = year;
    return r;
  }
  function fields(r) {
    const ev = String(r.Event ?? '');
    return {year: String(r.Season ?? ''), team: String(r.Team ?? ''), conference: String(r.Conference ?? ''),
      round: String(r.Round ?? ''), event: (C.bowl_labels || {})[ev] ?? ev, art: BOWL_ART[ev] ?? ev};
  }
  function eventCfg(r) {
    const ev = C.events[String(r.EventType ?? '')];
    if (!ev || typeof ev !== 'object') throw Error('No config/trophies.json events entry for EventType ' + r.EventType);
    return ev;
  }
  const artKey = r => fmt(eventCfg(r).art, fields(r));
  const genericKey = r => fmt(eventCfg(r).generic ?? '', fields(r));
  function geometry(art) {
    return {...clean(C.plaque), ...clean((C.overrides || {})[art])};
  }
  function textEm(text, weight) {
    const t = M[weight], fb = M.fallback;
    let s = 0;
    for (const ch of text) s += (t[ch] ?? fb);
    return (s + LETTER_SPACING * [...text].length) * SAFETY;
  }
  function engraving(event, winner, year, line2, fallback = false) {
    if (!C) throw Error('NCAATrophy.load() first');
    const r = row(event, winner, year), f = fields(r), ev = eventCfg(r), art = artKey(r), g = geometry(art), S = Number(g.size);
    const box = fallback ? {...FALLBACK_BOX} : {left: floor(g.x / S * 100, 2), top: floor(g.y / S * 100, 2),
      width: floor(g.w / S * 100, 2), height: floor(g.h / S * 100, 2)};
    const l1 = f.team, l2 = line2 != null ? String(line2) : fmt(ev.line2, f);
    const shown2 = g.uppercase_line2 ? l2.toUpperCase() : l2;
    const avail = box.width * (1 - 2 * Number(g.padding));
    const s1 = Math.min(box.height * Number(g.line1_max), avail / Math.max(textEm(l1, '700'), 1e-6));
    const s2 = Math.min(box.height * Number(g.line2_max), avail / Math.max(textEm(shown2, '400'), 1e-6));
    return {art, fallback, line1: l1, line2: l2, upper2: !!g.uppercase_line2, box,
      size1: floor(s1, 3), size2: floor(s2, 3), color: g.text_color,
      alt: fmt(ev.alt ?? '{year} {event} trophy, won by {team}', f), name: fmt(ev.name ?? '{event}', f),
      logo: fmt(ev.logo ?? '', f)};
  }
  const url = (prefix, p) => esc(prefix + String(p).split('/').map(encodeURIComponent).join('/'));
  function lines(en) {
    return `<span class="tp-1" style="font-size:${en.size1}cqw">${esc(en.line1)}</span>` +
      `<span class="tp-2${en.upper2 ? ' tp-up' : ''}" style="font-size:${en.size2}cqw">${esc(en.line2)}</span>`;
  }
  function fallbackHtml(event, winner, year, line2, o) {
    const en = engraving(event, winner, year, line2, true);
    const folder = en.logo.split('/').slice(-2, -1)[0];
    const stem = en.logo.split('/').pop().replace(/\.png$/i, '');
    const ok = en.logo && !((folder === 'Bowls' || folder === 'Playoffs') && !APPROVED.has(stem));
    const img = ok ? `<img src="${url(o.prefix, en.logo)}" alt="" onerror="this.remove()">` : '';
    return `<figure class="trophy fallback ${esc(o.cls || '')}" style="--tw:${o.width}px" data-art="${esc(en.art)}" role="img" aria-label="${esc(en.alt)}">` +
      `<div class="trophy-art">${img}<div class="trophy-plaque" style="color:${esc(en.color)}">${lines(en)}</div></div></figure>`;
  }
  function html(event, winner, year, line2, opts = {}) {
    const o = {width: (C.display || {}).list || 180, prefix: '../', cls: '', lazy: true, ...opts};
    const en = engraving(event, winner, year, line2), b = en.box;
    const fb = fallbackHtml(event, winner, year, line2, o);
    const pos = `left:${b.left}%;top:${b.top}%;width:${b.width}%;height:${b.height}%;color:${esc(en.color)}`;
    // Missing art never shows a broken image: own art -> the event's generic stand-in -> the fallback block.
    const gen = genericKey(row(event, winner, year));
    const swap = `const f=this.closest('figure');if(f.dataset.generic&&!f.dataset.tried){f.dataset.tried=1;this.src=f.dataset.generic}else f.outerHTML=f.dataset.fallback`;
    return `<figure class="trophy ${esc(o.cls)}" style="--tw:${o.width}px" data-art="${esc(en.art)}"` +
      `${gen ? ` data-generic="${url(o.prefix, gen)}"` : ''} data-fallback="${esc(fb)}">` +
      `<div class="trophy-art"><img src="${url(o.prefix, en.art)}" alt="${esc(en.alt)}" width="${o.width}" height="${o.width}"` +
      `${o.lazy ? ' loading="lazy" decoding="async"' : ''} onerror="${esc(swap)}">` +
      `<div class="trophy-plaque" style="${pos}">${lines(en)}</div></div></figure>`;
  }
  // The ledger (both files), for pages that draw in the browser. Quoted CSV supported.
  function parseCsv(text) {
    const out = []; let r = [], cell = '', q = false;
    for (let i = 0; i < text.length; i++) {
      const c = text[i];
      if (c === '"') { if (q && text[i + 1] === '"') { cell += '"'; i++; } else q = !q; }
      else if (c === ',' && !q) { r.push(cell); cell = ''; }
      else if ((c === '\n' || c === '\r') && !q) { if (c === '\r' && text[i + 1] === '\n') i++; r.push(cell); if (r.some(Boolean)) out.push(r); r = []; cell = ''; }
      else cell += c;
    }
    if (cell || r.length) { r.push(cell); if (r.some(Boolean)) out.push(r); }
    const keys = (out.shift() || []).map(k => k.replace(/^\ufeff/, ''));
    return out.map(a => Object.fromEntries(keys.map((k, i) => [k, a[i] ?? ''])));
  }
  let LEDGER = null;
  async function ledger(base = '../') {
    if (LEDGER) return LEDGER;
    const one = async p => { try { const r = await fetch(base + p, {cache: 'no-cache'}); return r.ok ? parseCsv(await r.text()) : []; } catch (e) { return []; } };
    const [h, s] = await Promise.all([one('data/Trophies_Historic.csv'), one('data/Trophies_Season.csv')]);
    return (LEDGER = [...h, ...s]);
  }
  const api = {load, init, engraving, html, ledger, parseCsv, artKey: (e, w, y) => artKey(row(e, w, y)), FALLBACK_BOX,
    get config() { return C; }};
  return api;
});
