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
  const fmt = v => (v == null || !Number.isFinite(+v)) ? '—' : Math.round(+v).toLocaleString('en-US');
  const pct = (v, d = 0) => (v == null || !Number.isFinite(+v)) ? '—' : (+v * 100).toFixed(d) + '%';
  let INDEX = null;

  // Rank change badge: positive = moved up. Arrow + number, never colour alone.
  function move(now, prev) {
    if (now == null || prev == null || now === prev) return '<span class="tm-mv flat" title="No change">–</span>';
    const up = prev - now;
    return `<span class="tm-mv ${up > 0 ? 'up' : 'dn'}" title="Last week #${prev}">${up > 0 ? '▲' : '▼'}${Math.abs(up)}</span>`;
  }
  function deltaPct(now, prev) {
    if (now == null || prev == null) return '';
    const d = Math.round((now - prev) * 1000) / 10;
    if (!d) return '<span class="tm-mv flat" title="No change">–</span>';
    return `<span class="tm-mv ${d > 0 ? 'up' : 'dn'}" title="Last week ${pct(prev, 1)}">${d > 0 ? '▲' : '▼'}${Math.abs(d).toFixed(1)}</span>`;
  }

  // ---- line chart (SVG, one y axis, hover crosshair + tooltip, direct end labels) ------------------
  // series: [{name, values (null = gap), cls: 's1'|'s2', dots?: only draw markers}], x: labels.
  let CHART_ID = 0;
  function lineChart({x, series, invert = false, yMin, yMax, fmtY = fmt, title, height = 220, note = '', width = (window.innerWidth < 560 ? 360 : 520)}) {
    const id = 'tmc' + (++CHART_ID);
    const W = width, H = height, M = {l: 48, r: 58, t: 14, b: 26};
    const all = series.flatMap(s => s.values).filter(v => v != null && Number.isFinite(v));
    if (!all.length) return '';
    let lo = yMin ?? Math.min(...all), hi = yMax ?? Math.max(...all);
    if (lo === hi) { lo -= 1; hi += 1; }
    const pad = (hi - lo) * 0.06; if (yMin == null) lo -= pad; if (yMax == null) hi += pad;
    const X = i => M.l + (x.length === 1 ? (W - M.l - M.r) / 2 : i * (W - M.l - M.r) / (x.length - 1));
    const Y = v => invert ? M.t + (v - lo) / (hi - lo) * (H - M.t - M.b) : H - M.b - (v - lo) / (hi - lo) * (H - M.t - M.b);
    const ticks = 4, grid = [];
    for (let k = 0; k <= ticks; k++) {
      const v = lo + (hi - lo) * k / ticks;
      grid.push(`<line x1="${M.l}" x2="${W - M.r}" y1="${Y(v)}" y2="${Y(v)}" class="g"/><text x="${M.l - 6}" y="${Y(v) + 4}" class="yl">${esc(fmtY(v))}</text>`);
    }
    const every = Math.ceil(x.length / (W < 400 ? 5 : 10));
    const xl = x.map((l, i) => (i % every === 0 || i === x.length - 1) ? `<text x="${X(i)}" y="${H - 6}" class="xl">${esc(l)}</text>` : '').join('');
    const placed = [];  // end labels: keep at least 13px apart
    const labelY = y => { let v = y; while (placed.some(p => Math.abs(p - v) < 13)) v += 13; placed.push(v); return v; };
    const paths = series.map(s => {
      let d = '', pen = false;
      s.values.forEach((v, i) => { if (v == null) { pen = false; return; } d += `${pen ? 'L' : 'M'}${X(i).toFixed(1)},${Y(v).toFixed(1)}`; pen = true; });
      const dots = s.values.map((v, i) => v == null ? '' : `<circle cx="${X(i)}" cy="${Y(v)}" r="${s.dots ? 4.5 : 3}" class="${s.cls}"/>`).join('');
      const li = s.values.map((v, i) => v == null ? -1 : i).filter(i => i >= 0).pop();
      const end = li >= 0 && !s.dots ? `<text x="${X(li) + 8}" y="${labelY(Y(s.values[li]) + 4)}" class="el">${esc(s.short || s.name)}</text>` : '';
      return (s.dots ? '' : `<path d="${d}" class="${s.cls}"/>`) + dots + end;
    }).join('');
    const legend = series.length > 1 ? `<div class="tm-legend">${series.map(s => `<span><i class="${s.cls}${s.dots ? ' dot' : ''}"></i>${esc(s.name)}</span>`).join('')}</div>` : '';
    const rows = x.map((l, i) => `<tr><td>${esc(l)}</td>${series.map(s => `<td>${s.values[i] == null ? '—' : esc(fmtY(s.values[i]))}</td>`).join('')}</tr>`).join('');
    return `<figure class="tm-chart" id="${id}" data-x='${esc(JSON.stringify(x))}'>` +
      (title ? `<figcaption>${esc(title)}</figcaption>` : '') + legend +
      `<svg viewBox="0 0 ${W} ${H}" role="img" aria-label="${esc(title || 'chart')}">${grid.join('')}${xl}${paths}` +
      `<line class="cross" y1="${M.t}" y2="${H - M.b}" x1="0" x2="0" visibility="hidden"/>` +
      `<rect class="hit" x="${M.l - 10}" y="0" width="${W - M.l - M.r + 20}" height="${H}" data-l="${M.l}" data-r="${M.r}" data-w="${W}" data-n="${x.length}"/></svg>` +
      `<div class="tm-tip" hidden></div>` +
      `<details class="tm-tbl"><summary>Table</summary><table><thead><tr><th></th>${series.map(s => `<th>${esc(s.name)}</th>`).join('')}</tr></thead><tbody>${rows}</tbody></table></details>` +
      (note ? `<p class="note">${note}</p>` : '') + `</figure>`;
  }
  // One delegated handler: hover/tap a chart -> crosshair + tooltip from its own table.
  function wireCharts(root) {
    root.querySelectorAll('.tm-chart').forEach(fig => {
      const hit = fig.querySelector('.hit'), svg = fig.querySelector('svg'), tip = fig.querySelector('.tm-tip'), cross = fig.querySelector('.cross');
      if (!hit) return;
      const n = +hit.dataset.n, l = +hit.dataset.l, r = +hit.dataset.r, w = +hit.dataset.w;
      const heads = [...fig.querySelectorAll('.tm-tbl th')].slice(1).map(t => t.textContent);
      const rows = [...fig.querySelectorAll('.tm-tbl tbody tr')].map(tr => [...tr.children].map(td => td.textContent));
      const show = e => {
        const b = svg.getBoundingClientRect();
        const sx = (e.clientX - b.left) * w / b.width;
        const i = Math.max(0, Math.min(n - 1, Math.round(n === 1 ? 0 : (sx - l) / ((w - l - r) / (n - 1)))));
        const cx = l + (n === 1 ? (w - l - r) / 2 : i * (w - l - r) / (n - 1));
        cross.setAttribute('x1', cx); cross.setAttribute('x2', cx); cross.setAttribute('visibility', 'visible');
        tip.innerHTML = `<b>${esc(rows[i][0])}</b>` + heads.map((h, k) => `<span>${esc(h)}: ${esc(rows[i][k + 1])}</span>`).join('');
        tip.hidden = false;
        const px = cx / w * b.width;
        tip.style.left = Math.min(Math.max(px - tip.offsetWidth / 2, 0), b.width - tip.offsetWidth) + 'px';
      };
      hit.addEventListener('pointermove', show);
      hit.addEventListener('pointerdown', show);
      hit.addEventListener('pointerleave', () => { tip.hidden = true; cross.setAttribute('visibility', 'hidden'); });
    });
  }

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
    const meta = [`${d.defunct ? 'Last manager' : 'Manager'}: ${esc(d.manager)}`];
    if (d.defunct) meta.push(`Defunct · played ${d.defunct.first === d.defunct.last ? d.defunct.first : d.defunct.first + '–' + d.defunct.last}`);
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
    const f = d.first_value;
    return '<div class="tm-roster">' + d.roster_groups.map(g => `<div><h3>${esc(g.pos)} <small>(${g.players.length})</small></h3><ul>` +
      g.players.map(p => `<li${p.star ? ' class="star"' : ''}><span>${p.star ? '<b class="tm-star" aria-label="High value">★</b> ' : ''}${esc(p.name)}</span>` +
        `<small>${esc(p.nfl)}${p.value ? ' · ' + fmt(p.value) : ''}</small></li>`).join('') + '</ul></div>').join('') + '</div>' +
      `<p class="note">Sorted by FantasyCalc dynasty value.${f ? ` ★ = worth more than an average ${f.season} 1st-round pick (${fmt(f.value)}).` : ''}</p>`;
  }

  function picksHtml(d) {
    const p = d.picks;
    if (!p) return '<p class="tm-empty">Pick data unavailable.</p>';
    if (!p.owned) return '<p class="tm-empty">Owns no future picks.</p>';
    return `<p class="tm-picks-n"><b>${p.owned}</b> future pick${p.owned === 1 ? '' : 's'} owned. Best by value:</p>` +
      `<ul class="tm-picks">${p.picks.map(x => `<li>${esc(x)}</li>`).join('')}</ul>`;
  }

  function managersHtml(d) {
    if (!d.managers || !d.managers.length) return '<p class="tm-empty">No managers on file.</p>';
    const span = ys => { const a = Math.min(...ys), b = Math.max(...ys); return a === b ? `${a}` : `${a}–${b}`; };
    const wp = m => { const g = m.w + m.l + m.t; return g ? ((m.w + m.t / 2) / g).toFixed(3).replace(/^0/, '') : '—'; };
    return `<div class="tm-scroll"><table class="tm-tbl-plain"><thead><tr><th>Manager</th><th>Seasons</th><th class="n">Record</th><th class="n">Pct</th><th class="n">Post</th><th class="n">Titles</th></tr></thead><tbody>` +
      d.managers.map(m => `<tr><td><b>${esc(m.manager)}</b></td><td>${span(m.years)} <small>(${m.years.length})</small></td>` +
        `<td class="n">${m.w}-${m.l}${m.t ? '-' + m.t : ''}</td><td class="n">${wp(m)}</td><td class="n">${m.pw}-${m.pl}</td><td class="n">${m.titles || ''}</td></tr>`).join('') +
      '</tbody></table></div><p class="note">Regular-season record; Post = postseason games won-lost.</p>';
  }

  function h2hHtml(d) {
    const h = d.h2h || [];
    if (!h.length) return '<p class="tm-empty">No games on file.</p>';
    const row = x => {
      const href = teamHref(x.key);
      const nm = href ? `<a class="team-link" href="${href}">${esc(x.name)}</a>` : esc(x.name);
      return `<tr><td>${nm}${x.post ? ` <small>(${x.post} postseason)</small>` : ''}</td><td class="n">${x.w}-${x.l}${x.t ? '-' + x.t : ''}</td>` +
        `<td class="n">${pts(x.pf)}</td><td class="n">${pts(x.pa)}</td><td class="n">${x.last}</td></tr>`;
    };
    return `<div class="tm-scroll"><table class="tm-tbl-plain" id="tm-h2h-t"><thead><tr><th>Opponent</th><th class="n">Record</th><th class="n">PF</th><th class="n">PA</th><th class="n">Last</th></tr></thead><tbody>` +
      h.map((x, i) => row(x).replace('<tr>', `<tr${i >= 12 ? ' hidden' : ''}>`)).join('') + '</tbody></table></div>' +
      (h.length > 12 ? `<button type="button" class="tm-more" id="tm-h2h-more">Show all ${h.length}</button>` : '') +
      '<p class="note">Every game this roster has played, regular season and postseason. Opponents are listed under their current name.</p>';
  }


  const ODDS_LABEL = {CCG: 'Conf. title game', Playoff: 'Playoff', Bowl: 'Bowl', Prestige: 'Prestige bowl', Marquee: 'Marquee bowl', NIT: 'NIT', Natty: 'National title'};
  function tile(value, label, extra = '') { return `<div class="tm-tile"><b>${value}</b><span>${label}</span>${extra}</div>`; }
  function overviewHtml(d) {
    const o = d.overview || {}, m = o.map || {}, cur = d.seasons.find(s => s.year === d.season) || {}, r = cur.record || {};
    const t = [];
    if (d.rank) t.push(tile(`#${d.rank}`, `Overall of ${d.of || 180}`));
    if (o.poll) t.push(tile(o.poll.status === 'Ranked' ? `#${o.poll.rank}` : (o.poll.status === 'ORV' ? 'ORV' : 'NR'), `Top 25 poll`,
      o.poll.status === 'Ranked' && o.poll.prev_status === 'Ranked' ? move(o.poll.rank, o.poll.prev) : (o.poll.status === 'Ranked' ? '<span class="tm-mv up">New</span>' : '')));
    if (o.bots) t.push(tile(`#${o.bots.rank}`, `Bot consensus${o.bots.bot_avg ? ` · avg ${o.bots.bot_avg.toFixed(1)}` : ''}`, move(o.bots.rank, o.bots.prev)));
    const fpv = (cur.poll && cur.poll.summary && cur.poll.summary.fpv) || 0;
    if (fpv) t.push(tile(fpv, `1st-place votes (${d.season})`));
    if (m.dyn) t.push(tile(fmt(m.dyn[0]), `Dynasty value · #${m.dyn[1]}${m.dyn_lg ? ` · #${m.dyn_lg[0]} in ${esc(d.short)}` : ''}`, move(m.dyn[1], m.dyn[2])));
    if (m.pv) t.push(tile(fmt(m.pv[0]), `Pick value · #${m.pv[1]}`, move(m.pv[1], m.pv[2])));
    if (m.red) t.push(tile(fmt(m.red[0]), `Lineup value · #${m.red[1]}`, move(m.red[1], m.red[2])));
    if (m.con) t.push(tile(`#${m.con[1]}`, 'Contender rank', move(m.con[1], m.con[2])));
    if (m.ppg) t.push(tile((+m.ppg[0]).toFixed(1), `Points per game · #${m.ppg[1]}`, move(m.ppg[1], m.ppg[2])));
    if (o.eff) t.push(tile(`${o.eff[0]}%`, `Lineup efficiency · #${o.eff[1]}`, move(o.eff[1], o.eff[2])));
    if (r.xw != null) t.push(tile((+r.xw).toFixed(1), `Expected wins · luck ${((r.w + r.t / 2) - r.xw >= 0 ? '+' : '') + ((r.w + r.t / 2) - r.xw).toFixed(1)}`));
    if (r.ap) t.push(tile(`${r.ap[0]}-${r.ap[1]}${r.ap[2] ? '-' + r.ap[2] : ''}`, 'All-play record'));
    if (r.med) t.push(tile(`${r.med[0]}-${r.med[1]}${r.med[2] ? '-' + r.med[2] : ''}`, 'Vs league median'));
    if (o.sched) {
      t.push(tile(`#${o.sched.sos[0]}`, `Schedule difficulty (thru wk ${o.sched.week})`, move(o.sched.sos[0], o.sched.sos[1])));
      t.push(tile(`#${o.sched.sor[0]}`, `Strength of record (thru wk ${o.sched.week})`, move(o.sched.sor[0], o.sched.sor[1])));
    }
    const head = [`${d.season}: ${rec(r) || '0-0'}`, d.place ? `${ord(d.place[0])} in ${esc(d.division)}` : '', r.pf != null ? `PF ${pts(r.pf)} · PA ${pts(r.pa)}` : '']
      .filter(Boolean).map(x => `<span>${x}</span>`).join('');
    // Postseason: the team's games once it has one; until then the Selection Watch odds.
    const games = o.post || [];
    let post = '';
    if (games.length) {
      post = `<div class="tm-ov-post"><h3>Postseason</h3><ul>${games.map(g => `<li><b>${esc(g.label)}</b> vs ${esc(g.opp)} · ` +
        (g.res ? `${g.res === 'W' ? 'Won' : g.res === 'L' ? 'Lost' : 'Tied'} ${pts(g.pf)}–${pts(g.pa)}` : esc(g.status || 'Pending')) + '</li>').join('')}</ul></div>`;
    } else if (o.odds) {
      const od = o.odds;
      post = `<div class="tm-ov-post"><h3>Postseason odds <small>(after week ${od.after_week})</small></h3><div class="tm-odds">` +
        od.cols.map(c => `<div><b>${pct(od.now[c], od.now[c] > 0 && od.now[c] < 0.01 ? 1 : 0)}</b><span>${esc(ODDS_LABEL[c] || c)}</span>${od.prev ? deltaPct(od.now[c], od.prev[c]) : ''}</div>`).join('') + '</div></div>';
    }
    let next = '';
    const n = o.next;
    const pending = games.find(g => !g.res);
    if (n && n.win != null && (o.phase !== 'post' || (pending && pending.w === n.week))) {
      next = `<p class="tm-ov-next">Week ${n.week} vs <b>${esc(n.opp)}</b> · win chance <b>${n.win.toFixed(1)}%</b> · projected ${pts(n.proj)}–${pts(n.opp_proj)}</p>`;
    }
    const trend = (o.trend || []).length > 1 ? lineChart({
      x: o.trend.map(p => `Wk ${p[0]}`), series: [{name: 'Dynasty value', values: o.trend.map(p => p[1]), cls: 's1', short: 'Value'}],
      title: `Dynasty value through ${d.season}`, height: 160, note: `Ranks of 180: ${o.trend.map(p => '#' + p[2]).join(' → ')}`}) : '';
    return `<article class="tm-ov" data-snap-card="${esc(d.name)} overview"><header class="tm-ov-head">${head}</header>` +
      next + `<div class="tm-tiles">${t.join('')}</div>` + post + trend +
      `<p class="note">▲/▼ = change in rank since last week. Values: FantasyCalc dynasty (Roster Map, week ${m.week || '—'}).</p></article>`;
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

  function seasonCharts(d) {
    const ss = d.seasons.filter(s => s.record && s.record.games).slice().sort((a, b) => a.year - b.year);
    if (!ss.length) return '';
    const x = ss.map(s => String(s.year));
    const pf = lineChart({x, title: 'Points for vs max possible (regular season)',
      series: [{name: 'Points for', short: 'PF', values: ss.map(s => s.record.pf), cls: 's1'},
               {name: 'Max PF', short: 'Max', values: ss.map(s => s.record.max ?? null), cls: 's2'}],
      note: 'Points for on standard scoring; Max PF is the best possible lineup each week (Sleeper).'});
    const eff = lineChart({x, title: 'Lineup efficiency (PF ÷ Max PF)', fmtY: v => v.toFixed(0) + '%', height: 170,
      series: [{name: 'Efficiency', values: ss.map(s => s.record.max ? s.record.pf_official / s.record.max * 100 : null), cls: 's1'}]});
    const wins = lineChart({x, title: 'Wins vs expected wins', fmtY: v => v.toFixed(1),
      series: [{name: 'Wins', values: ss.map(s => s.record.w + s.record.t / 2), cls: 's1'},
               {name: 'Expected wins', short: 'xW', values: ss.map(s => s.record.xw ?? null), cls: 's2'}],
      note: 'Expected wins = each week\'s share of the league this score would have beaten (all-play).'});
    const polls = d.seasons.filter(s => s.poll && s.poll.summary);
    const pr = v => v == null ? '—' : '#' + v;
    const ptable = polls.length ? `<h3 class="tm-sub">Polls by season</h3><div class="tm-scroll"><table class="tm-tbl-plain"><thead><tr><th>Year</th>` +
      `<th class="n">Bots peak</th><th class="n">Low</th><th class="n">Final</th><th class="n">Top 25 peak</th><th class="n">Low</th><th class="n">Final</th><th class="n">1st-pl. votes</th></tr></thead><tbody>` +
      polls.map(s => { const c = s.poll.summary.cons || {}, o = s.poll.summary.official;
        return `<tr><td>${s.year}</td><td class="n">${pr(c.peak)}</td><td class="n">${pr(c.low)}</td><td class="n">${pr(c.final)}</td>` +
          (o ? `<td class="n">${pr(o.peak)}</td><td class="n">${pr(o.low)}</td><td class="n">${o.final == null ? 'NR' : pr(o.final)}</td>` : '<td class="n" colspan="3"><small>Not ranked</small></td>') +
          `<td class="n">${s.poll.summary.fpv || ''}</td></tr>`; }).join('') +
      '</tbody></table></div><p class="note">Bots = the bot consensus ranking of all 180 teams. Top 25 = the official poll, shown only for seasons the team was ranked (low = lowest ranked week).</p>' : '';
    const ap = ss.filter(s => s.record.ap);
    const aptable = ap.length ? `<h3 class="tm-sub">Strength beyond the schedule</h3><div class="tm-scroll"><table class="tm-tbl-plain"><thead><tr><th>Year</th><th class="n">Record</th><th class="n">All-play</th><th class="n">Vs median</th><th class="n">xW</th><th class="n">Luck</th><th class="n">Efficiency</th></tr></thead><tbody>` +
      ap.slice().reverse().map(s => { const r = s.record, w = r.w + r.t / 2, apg = r.ap[0] + r.ap[1] + r.ap[2];
        return `<tr><td>${s.year}</td><td class="n">${rec(r)}</td><td class="n">${r.ap[0]}-${r.ap[1]}${r.ap[2] ? '-' + r.ap[2] : ''} <small>${apg ? ((r.ap[0] + r.ap[2] / 2) / apg).toFixed(3).replace(/^0/, '') : ''}</small></td>` +
          `<td class="n">${r.med[0]}-${r.med[1]}${r.med[2] ? '-' + r.med[2] : ''}</td><td class="n">${(+r.xw).toFixed(1)}</td><td class="n">${(w - r.xw >= 0 ? '+' : '') + (w - r.xw).toFixed(1)}</td>` +
          `<td class="n">${r.max ? (r.pf_official / r.max * 100).toFixed(1) + '%' : '—'}</td></tr>`; }).join('') + '</tbody></table></div>' : '';
    return `<div class="tm-charts">${pf}${wins}${eff}</div>${ptable}${aptable}`;
  }

  function seasonPoll(s) {
    const p = s.poll;
    if (!p || !p.cons.length) return '';
    const wk = [...new Set([...p.cons.map(c => c[0]), ...p.top.map(c => c[0])])].sort((a, b) => a - b);
    const cons = new Map(p.cons), top = new Map(p.top.filter(t => t[2] === 'Ranked').map(t => [t[0], t[1]]));
    const all = [...p.cons.map(c => c[1]), ...top.values()];
    const hi = Math.max(25, ...all);
    const sm = p.summary, c = sm.cons || {}, o = sm.official;
    const line = [`Bots: peak #${c.peak} · low #${c.low} · final #${c.final}`,
      o ? `Top 25: peak #${o.peak} · low #${o.low} · final ${o.final == null ? 'NR' : '#' + o.final}` : 'Top 25: not ranked',
      sm.fpv ? `${sm.fpv} first-place vote${sm.fpv === 1 ? '' : 's'}` : ''].filter(Boolean).join(' · ');
    return lineChart({x: wk.map(w => `Wk ${w}`), invert: true, yMin: 1, yMax: hi, fmtY: v => '#' + Math.round(v), height: 180,
      title: `${s.year} weekly poll rank`,
      series: [{name: 'Bot consensus', short: 'Bots', values: wk.map(w => cons.get(w) ?? null), cls: 's1'},
               ...(top.size ? [{name: 'Top 25 (ranked weeks)', short: 'Top 25', values: wk.map(w => top.get(w) ?? null), cls: 's2', dots: true}] : [])],
      note: esc(line)});
  }

  function seasons(d) {
    if (!d.seasons.length) return '<p class="tm-empty">No seasons on file.</p>';
    const open = d.settings.current_season_open !== false;
    const openYear = d.defunct ? d.defunct.last : d.season;
    return d.seasons.map(s => {
      const id = s.identity || {bg: d.bg, ink: d.ink};
      const bits = [];
      if (s.record) {
        const r = s.record, off = r.pf_official != null && (Math.abs(r.pf - r.pf_official) > 0.005 || Math.abs(r.pa - r.pa_official) > 0.005);
        bits.push(`${rec(r)} · PF ${pts(r.pf)} · PA ${pts(r.pa)}${off ? ` <small>(† Sleeper ${pts(r.pf_official)}–${pts(r.pa_official)})</small>` : ''}`);
      }
      if (s.place) bits.push(`${ord(s.place[0])} of ${s.place[1]} in ${esc(s.division || 'division')}`);
      if (s.record && s.record.xw != null) bits.push(`xW ${(+s.record.xw).toFixed(1)}`);
      const sum = [s.post || (s.year === d.season ? '' : 'No postseason'), s.manager ? 'Manager: ' + s.manager : ''].filter(Boolean).join(' · ');
      return `<details class="tm-season" data-year="${s.year}"${open && s.year === openYear ? ' open' : ''}><summary>` +
        `<span class="yr">${s.year}</span><span class="tm-chip" style="--chip-bg:${esc(id.bg)};--chip-ink:${esc(id.ink)}">${esc(s.name)}</span>` +
        `<span>${bits.join(' · ')}</span>${sum ? `<span class="sum">${esc(sum)}</span>` : ''}</summary>` +
        `<div class="body">${seasonPoll(s)}<table class="tm-games"><colgroup><col class="c-wk"><col><col class="c-sc"><col class="c-r"></colgroup><tbody>${s.games.map(gameRow).join('')}</tbody></table></div></details>`;
    }).join('');
  }

  function drafts(d) {
    if (!d.drafts.length) return '<p class="tm-empty">No draft picks on file.</p>';
    const recon = d.drafts.some(b => b.source === 'sheet');
    return d.drafts.map(b => `<div class="tm-draft"><h3>${b.year} ${esc(b.label)}${b.source === 'sheet' ? ' <sup title="Reconstructed">‡</sup>' : ''}</h3><ol>` +
      b.picks.map(p => `<li><b>${p.round}.${String(p.pick).padStart(2, '0')}</b><span>${esc(p.player)} <small>${esc([p.pos, p.nfl].filter(Boolean).join(' · '))}` +
        `${p.note ? ' · ' + esc(p.note) : ''}</small></span></li>`).join('') + '</ol></div>').join('') +
      (recon ? '<p class="note">‡ Reconstructed, not from Sleeper data; pick order may not be exact.</p>' : '');
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
    const group = ([lid, lg]) => `<div><h3>${esc(lg.short)}${lg.defunct ? ` <small>(through ${lg.last})</small>` : ''}</h3><ul>` +
      Object.entries(INDEX.teams[lid] || {}).sort((a, b) => a[1].name.localeCompare(b[1].name))
        .map(([r, t]) => `<li><a href="${L.href(lid, r)}">${esc(t.name)}<small>${esc(t.manager)}</small></a></li>`).join('') + '</ul></div>';
    const all = Object.entries(INDEX.leagues);
    const gone = all.filter(([, lg]) => lg.defunct);
    $('tm-pick').innerHTML = myTeamCard() + all.filter(([, lg]) => !lg.defunct).map(group).join('') +
      (gone.length ? `<div class="tm-defunct"><h3>Defunct teams</h3><div class="tm-pick">${gone.map(group).join('')}</div></div>` : '');
  }

  // My team (the app page's pick, stored on this device; a device with follows but no pick uses its first
  // followed team -- the same rule as app.js / the Games page). Read straight from storage because app.js
  // loads deferred, after this script.
  function myTeam() {
    try {
      const st = JSON.parse(localStorage.getItem('ncaa180.push') || '{}');
      const k = st.myTeam || ((st.follows || []).find(f => f.kind === 'team') || {}).key;
      if (!k) return null;
      const t = String(k).split('|').slice(1).join('|'), i = t.lastIndexOf(':');
      if (i < 0) return null;
      const conf = t.slice(0, i), roster = L.rid(t.slice(i + 1));
      const lid = Object.keys(INDEX.leagues).find(id => !INDEX.leagues[id].defunct && INDEX.leagues[id].short === conf);
      return lid && (INDEX.teams[lid] || {})[roster] ? {league: lid, roster, ...INDEX.teams[lid][roster]} : null;
    } catch (e) { return null; }
  }
  function myTeamCard() {
    const m = myTeam();
    if (!m) return '<div class="tm-mine none"><h3>My team</h3><p>No team set on this device. <a href="app.html">Set your team</a></p></div>';
    return `<div class="tm-mine"><h3>My team</h3><a href="${L.href(m.league, m.roster)}">${esc(m.name)}<small>${esc(m.manager)} · ${esc(INDEX.leagues[m.league].short)}</small></a></div>`;
  }

  async function main() {
    try { INDEX = await getJson('data/teams/index.json'); }
    catch (e) { $('tm-error').textContent = 'Team data could not be loaded. ' + e.message; $('tm-error').hidden = false; return; }
    const q = new URLSearchParams(location.search);
    let league = q.get('league'), roster = L.rid(q.get('roster'));
    if (!league && !roster) { picker(); return finish(); }
    if (!(INDEX.teams[league] || {})[roster]) {  // a past season's league ID: match by league name + roster
      const cur = L.currentTeam(INDEX, {leagueId: league, roster});
      if (!cur) { picker('No team page found for that team. Pick a team:'); return finish(); }
      league = cur.league; roster = cur.roster;
      history.replaceState(null, '', L.href(league, roster));
    }
    let d;
    try { d = await getJson('data/teams/' + INDEX.teams[league][roster].file); }
    catch (e) { $('tm-error').textContent = 'Team data could not be loaded. ' + e.message; $('tm-error').hidden = false; return; }
    document.title = `${d.name} · ${document.title.replace(/^Team · /, '')}`;
    $('tm-top').innerHTML = header(d);
    if (d.defunct) {  // no current data: the header says it's defunct
      ['tm-over-sec', 'tm-roster-sec', 'tm-picks-sec'].forEach(id => $(id).remove());
    } else {
      $('tm-over').innerHTML = overviewHtml(d);
      $('tm-roster').innerHTML = rosterHtml(d);
      $('tm-picks').innerHTML = picksHtml(d);
    }
    $('tm-mgr').innerHTML = managersHtml(d);
    $('tm-h2h').innerHTML = h2hHtml(d);
    const more = $('tm-h2h-more');
    if (more) more.addEventListener('click', () => { document.querySelectorAll('#tm-h2h-t tr[hidden]').forEach(tr => { tr.hidden = false; }); more.remove(); });
    $('tm-trophies').innerHTML = await trophies(d);
    $('tm-season-charts').innerHTML = seasonCharts(d);
    $('tm-seasons').innerHTML = seasons(d);
    const stdFrom = d.seasons.some(s => s.standard) ? Math.min(...d.seasons.filter(s => s.standard).map(s => s.year)) : d.season;
    $('tm-season-note').textContent = `Scores and PF/PA are on standard scoring (the score that should have occurred). Results from ${stdFrom} on are decided on standard scoring; earlier results and records are as recorded by Sleeper and never flipped. † marks Sleeper's official score where it differs.`;
    $('tm-drafts').innerHTML = drafts(d);
    transactions(d);
    $('tm-sections').hidden = false;
    wireCharts(document);
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
