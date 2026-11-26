/* team.js -- the team page (task 5.20): reports/team.html?league=<current league id>&roster=<id>.
 * Builds everything in the browser from data/teams/<league slug>-<roster>.json (scripts/team_pages.py).
 * No query string -> a team picker. A past season's league ID is accepted and swapped for this season's
 * (NCAATeamLink.currentTeam: league name + roster). After drawing, the standard section treatment
 * (snapshot.js + sections.js) is loaded so every section and card gets its fold and Save image button.
 */
(function () {
  'use strict';
  const BASE = '../';
  const $ = id => document.getElementById(id);
  const esc = v => String(v ?? '').replace(/[&<>"']/g, c => ({'&': '&amp;', '<': '&lt;', '>': '&gt;', '"': '&quot;', "'": '&#39;'}[c]));
  const pts = v => (v == null || v === '' || !Number.isFinite(+v)) ? '—' : (+v).toFixed(2);
  const ord = n => { n = +n; const s = (n % 100 >= 11 && n % 100 <= 13) ? 'th' : ({1: 'st', 2: 'nd', 3: 'rd'}[n % 10] || 'th'); return n + s; };
  const L = window.NCAATeamLink;
  let INDEX = null;

  async function getJson(p) {
    const r = await fetch(BASE + p, {cache: 'no-cache'});
    if (!r.ok) throw Error(`${p}: HTTP ${r.status}`);
    return r.json();
  }
  const rec = r => r ? `${r.w}-${r.l}${r.t ? '-' + r.t : ''}` : '';
  const teamHref = key => {
    if (!key || !INDEX) return '';
    const [lg, r] = key.split('|');
    const t = L.currentTeam(INDEX, {leagueName: lg, roster: r});
    return t ? L.href(t.league, t.roster) : '';
  };

  // ---- header -------------------------------------------------------------------------------
  function header(d) {
    const meta = [`Manager: ${esc(d.manager)}`];
    if (d.record) meta.push(`${d.season}: ${rec(d.record)}`);
    if (d.rank) meta.push(`#${d.rank}${d.of ? ' of ' + d.of : ''} overall`);
    if (d.place) meta.push(`${ord(d.place[0])} in ${esc(d.division || 'division')}`);
    const former = (d.former || []).map(f => `${esc(f.name)} (${f.from === f.to ? f.from : f.from + '–' + f.to})`).join(', ');
    return `<header class="tm-head" style="--team-bg:${esc(d.bg)};--team-ink:${esc(d.ink)}">` +
      (d.logo ? `<img src="${esc(d.logo)}" alt="" onerror="this.remove()">` : '') +
      `<div><div class="eyebrow">${esc(d.short)}${d.division ? ' · ' + esc(d.division) : ''}</div>` +
      `<h1>${esc(d.name)}</h1><div class="tm-meta">${meta.map(m => `<span>${m}</span>`).join('')}</div>` +
      (former ? `<div class="tm-former">Formerly ${former}</div>` : '') + `</div></header>`;
  }

  // ---- sections ------------------------------------------------------------------------------
  function rosterHtml(d) {
    if (!d.roster_groups.length) return '<p class="tm-empty">No players on the current roster.</p>';
    return '<div class="tm-roster">' + d.roster_groups.map(g => `<div><h3>${esc(g.pos)} <small>(${g.players.length})</small></h3><ul>` +
      g.players.map(p => `<li><span>${esc(p.name)}</span><small>${esc(p.nfl)}</small></li>`).join('') + '</ul></div>').join('') + '</div>';
  }

  async function trophies(d) {
    if (!d.trophies.length) return `<p class="tm-empty">${esc(d.name)} hasn't won a trophy yet.</p>`;
    try { await window.NCAATrophy.load(BASE); } catch (e) { console.warn('trophy config', e); }
    return '<div class="tm-trophies">' + d.trophies.map(t => {
      const title = `${t.Season} ${t.Event} · ${t.Team}`;
      let fig = '';
      try { fig = window.NCAATrophy.html(t, null, null, null, {width: 200}); } catch (e) { fig = `<p>${esc(t.Event)}</p>`; }
      return `<article data-snap-card="${esc(title)}"><header>${esc(t.Season)} · ${esc(t.Event)}</header>${fig}</article>`;
    }).join('') + '</div>';
  }

  function gameRow(g) {
    const opp = g.opp_key && teamHref(g.opp_key) ? `<a class="team-link" href="${teamHref(g.opp_key)}">${esc(g.opp)}</a>` : esc(g.opp);
    const wk = `Wk ${g.w}`;
    let what = opp, score = '', res = '';
    if (g.kind === 'post') what = `<b>${esc(g.label)}</b><small>vs ${opp}</small>`;
    if (g.res) {
      res = `<span class="tm-res ${esc(g.res)}">${esc(g.res)}</span>`;
      score = g.place ? `${pts(g.pf)}<small>${ord(g.place)} of ${g.size}</small>` : `${pts(g.pf)}–${pts(g.pa)}`;
    } else if (g.kind === 'post') {
      score = `<small>${esc(g.status || 'Pending')}</small>`;
    }
    const notes = [];
    if (g.official) notes.push(`† Sleeper: ${pts(g.official[0])}–${pts(g.official[1])}`);
    if (g.note) notes.push(esc(g.note));
    return `<tr class="${g.kind}"><td class="wk">${wk}</td><td>${what}${notes.length ? `<small>${notes.join(' · ')}</small>` : ''}</td>` +
      `<td class="n">${score}</td><td>${res}</td></tr>`;
  }

  function seasons(d) {
    if (!d.seasons.length) return '<p class="tm-empty">No seasons on file.</p>';
    const open = d.settings.current_season_open !== false;
    return d.seasons.map(s => {
      const id = s.identity || {bg: d.bg, ink: d.ink};
      const bits = [];
      if (s.record) bits.push(`${rec(s.record)} · PF ${pts(s.record.pf)} · PA ${pts(s.record.pa)}`);
      if (s.place) bits.push(`${ord(s.place[0])} of ${s.place[1]} in ${esc(s.division || 'division')}`);
      const sum = [s.post || (s.year === d.season ? '' : 'No postseason'), s.manager ? 'Manager: ' + s.manager : ''].filter(Boolean).join(' · ');
      return `<details class="tm-season" data-year="${s.year}"${open && s.year === d.season ? ' open' : ''}><summary>` +
        `<span class="yr">${s.year}</span><span class="tm-chip" style="--chip-bg:${esc(id.bg)};--chip-ink:${esc(id.ink)}">${esc(s.name)}</span>` +
        `<span>${bits.join(' · ')}</span>${sum ? `<span class="sum">${esc(sum)}</span>` : ''}</summary>` +
        `<div class="body"><table class="tm-games"><colgroup><col class="c-wk"><col><col class="c-sc"><col class="c-r"></colgroup><tbody>${s.games.map(gameRow).join('')}</tbody></table></div></details>`;
    }).join('');
  }

  function drafts(d) {
    if (!d.drafts.length) return '<p class="tm-empty">No draft picks on file.</p>';
    return d.drafts.map(b => `<div class="tm-draft"><h3>${b.year} ${esc(b.label)}${b.source === 'sheet' ? ' <small>(from Chris\'s draft sheets)</small>' : ''}</h3><ol>` +
      b.picks.map(p => `<li><b>${p.round}.${String(p.pick).padStart(2, '0')}</b><span>${esc(p.player)} <small>${esc([p.pos, p.nfl].filter(Boolean).join(' · '))}` +
        `${p.note ? ' · ' + esc(p.note) : ''}</small></span></li>`).join('') + '</ol></div>').join('');
  }

  const day = t => new Date(t).toISOString().slice(0, 10);
  const TYPE = {free_agent: 'Free agent', waiver: 'Waiver', commissioner: 'Commissioner', trade: 'Trade'};
  function txItem(t) {
    if (t.html) return t.html;
    const when = `<span class="when">${t.y} · Wk ${t.wk} · ${day(t.t)} · ${esc(TYPE[t.type] || t.type)}</span>`;
    if (t.type === 'trade') {  // a trade the Transactions page can't draw as a two-team card
      return `<div class="tm-move">${when}<span>With ${esc((t.partners || []).join(', '))}</span>` +
        (t.gets || []).map(x => `<span class="add">${esc(x)}</span>`).join('') + (t.gives || []).map(x => `<span class="drop">${esc(x)}</span>`).join('') + '</div>';
    }
    const p = ([n, pos]) => `${pos ? `<span class="tx-pos tx-pos-${esc(String(pos).toLowerCase())}">${esc(pos)}</span> ` : ''}${esc(n)}`;
    return `<div class="tm-move">${when}${t.adds.map(x => `<span class="add">${p(x)}</span>`).join('')}${t.drops.map(x => `<span class="drop">${p(x)}</span>`).join('')}</div>`;
  }
  function transactions(d) {
    const box = $('tm-tx');
    if (!d.transactions.length) { box.innerHTML = '<p class="tm-empty">No transactions on file.</p>'; return; }
    const step = d.settings.transactions_shown || 25;
    box.innerHTML = d.transactions.map(t => `<div class="tm-tx-item">${txItem(t)}</div>`).join('');
    const items = [...box.children];
    let shown = 0;
    const btn = document.createElement('button');
    btn.type = 'button'; btn.className = 'tm-more';
    const more = () => {
      shown = Math.min(items.length, shown + step);
      items.forEach((el, i) => { el.hidden = i >= shown; });
      btn.hidden = shown >= items.length;
      btn.textContent = `Show more (${items.length - shown} left)`;
    };
    btn.addEventListener('click', more);
    box.after(btn);
    more();
  }

  // Trade grade colours: same painting as the Transactions page (shared theme tokens).
  function paint() {
    for (const el of document.querySelectorAll('#tm-tx [data-score]')) {
      const scale = window.NCAA180 && NCAA180.colors && NCAA180.colors.scale;
      el.style.color = scale ? scale(Number(el.dataset.colorScore ?? el.dataset.score) / 100) : 'var(--neutral)';
    }
  }

  function loadScript(src) {
    return new Promise(res => { const s = document.createElement('script'); s.src = src; s.onload = s.onerror = res; document.body.append(s); });
  }
  async function finish() {
    await loadScript('assets/snapshot.js');
    await loadScript('assets/sections.js');
    document.body.dataset.ready = '1';
  }

  // ---- picker / errors -----------------------------------------------------------------------
  function picker(msg) {
    if (msg) { $('tm-error').textContent = msg; $('tm-error').hidden = false; }
    $('tm-picker').hidden = false;
    $('tm-pick').innerHTML = Object.entries(INDEX.leagues).map(([lid, lg]) => `<div><h3>${esc(lg.short)}</h3><ul>` +
      Object.entries(INDEX.teams[lid] || {}).sort((a, b) => a[1].name.localeCompare(b[1].name))
        .map(([r, t]) => `<li><a href="${L.href(lid, r)}">${esc(t.name)}<small>${esc(t.manager)}</small></a></li>`).join('') + '</ul></div>').join('');
  }

  async function main() {
    try { INDEX = await getJson('data/teams/index.json'); }
    catch (e) { $('tm-error').textContent = 'Team data could not be loaded. ' + e.message; $('tm-error').hidden = false; return; }
    const q = new URLSearchParams(location.search);
    let league = q.get('league'), roster = L.rid(q.get('roster'));
    if (!league && !roster) { picker(); return finish(); }
    if (!(INDEX.teams[league] || {})[roster]) {  // a past season's league ID: match by league name + roster
      const cur = L.currentTeam(INDEX, {leagueId: league, roster});
      if (!cur) { picker('That team is not in the league this season. Pick a team:'); return finish(); }
      league = cur.league; roster = cur.roster;
      history.replaceState(null, '', L.href(league, roster));
    }
    let d;
    try { d = await getJson('data/teams/' + INDEX.teams[league][roster].file); }
    catch (e) { $('tm-error').textContent = 'Team data could not be loaded. ' + e.message; $('tm-error').hidden = false; return; }
    document.title = `${d.name} · ${document.title.replace(/^Team · /, '')}`;
    $('tm-top').innerHTML = header(d);
    $("tm-roster").innerHTML = rosterHtml(d);
    $('tm-trophies').innerHTML = await trophies(d);
    $('tm-seasons').innerHTML = seasons(d);
    $('tm-season-note').textContent = `Scores are on standard scoring (the score that should have occurred). Results from ${d.seasons.some(s => s.standard) ? Math.min(...d.seasons.filter(s => s.standard).map(s => s.year)) : d.season} on are decided on standard scoring; earlier results, records and PF/PA are as recorded by Sleeper, the same as the Standings pages. † marks Sleeper's official score where it differs.`;
    $('tm-drafts').innerHTML = drafts(d);
    transactions(d);
    $('tm-sections').hidden = false;
    paint();
    const tok = document.getElementById('n180-tokens');
    const obs = new MutationObserver(paint);
    if (tok) obs.observe(tok, {childList: true, characterData: true, subtree: true});
    obs.observe(document.documentElement, {attributes: true, attributeFilter: ['data-theme']});
    document.body.dataset.snapTag = d.name;
    await finish();
  }
  main();
})();
