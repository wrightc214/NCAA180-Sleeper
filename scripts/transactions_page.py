"""Static Transactions page: completed trades, waiver movement and season summary.

No external requests. Run after league_transactions.py and player_values.py.
"""
import ast
import collections
import csv
import datetime as dt
import html
import json
import os
import sys
from pathlib import Path

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import league_config as lcfg
import team_names as tn
from site_common import SECTIONS_JS, logo_html, menu_html, page_head, team_colors
from transactions_grades import evaluate_trade, load_config, read_rows

TRANSACTIONS = "data/Transactions_Season.csv"
PLAYERS = "data/Players.csv"
ROSTERS = "data/Rosters_Current.csv"
TEAMS = "data/Teams.csv"
PLAYER_VALUES = "data/PlayerValues_Season.csv"
PICK_VALUES = "data/PickValues_Season.csv"
OUT = "reports/transactions.html"

CSS = """
.tx-controls{display:flex;gap:12px;flex-wrap:wrap;margin:12px 0 20px}
.tx-controls label{display:flex;flex-direction:column;gap:5px;font-size:12px;font-weight:700;color:var(--mute)}
.tx-controls select{min-width:125px;max-width:100%;padding:8px;border-radius:7px;background:var(--panel);color:var(--ink);border:1px solid var(--line);font:inherit}
.tx-cards{display:grid;gap:16px}
.tx-card{border:1px solid var(--line);border-radius:12px;overflow:hidden;background:var(--panel);box-shadow:0 3px 14px #0001}
.tx-card.tx-blockbuster{border-top:2px solid var(--gold,var(--accent))}
.tx-flag{display:inline-block;margin-left:6px;padding:2px 6px;border:1px solid currentColor;border-radius:4px;color:var(--ink);font-weight:800;text-transform:uppercase;font-size:10px;letter-spacing:.07em}
.tx-card.mine{outline:2px solid var(--accent);outline-offset:2px}
.tx-card header{display:flex;justify-content:space-between;align-items:center;gap:12px;margin:0;padding:10px 15px;background:var(--bg);border-bottom:1px solid var(--line)}
.tx-card .tx-head{font-size:12px;font-weight:800;letter-spacing:.04em}
.tx-grid{display:grid;grid-template-columns:minmax(0,1fr) minmax(175px,.72fr) minmax(0,1fr);gap:12px;padding:12px}
.tx-side{border:1px solid var(--line);border-radius:10px;overflow:hidden;min-width:0}
.tx-team{display:flex;align-items:center;gap:12px;padding:12px;background:var(--team-bg,var(--bg));color:var(--team-ink,var(--ink));font-size:19px;font-weight:900}
.tx-team img{width:48px;height:48px;object-fit:contain}
.tx-assets{padding:10px;min-height:78px}
.tx-assets .tx-receives{text-transform:uppercase;letter-spacing:.08em;font-size:11px;font-weight:800;color:var(--mute);margin:0 0 7px}
.tx-asset{padding:6px 8px;margin:4px 0;border:1px solid var(--line);border-radius:6px;font-weight:600}
.tx-pick{font-size:.95em}
.tx-grade{display:flex;justify-content:space-between;align-items:center;gap:8px;padding:7px 0;border-bottom:1px solid var(--line);font-weight:700;font-size:12px}
.tx-grade strong{font:bold 20px var(--num,sans-serif);color:var(--neutral)}
.tx-grade .tx-side-value{min-width:0;text-align:center}
.tx-grade .tx-side-value small{display:block;font-size:11px;color:var(--mute);font-variant-numeric:tabular-nums}
.tx-grade strong[data-score]{color:var(--neutral)}
.tx-center{text-align:center;display:flex;flex-direction:column;justify-content:center;gap:6px}
.tx-center h3{font-size:12px;letter-spacing:.07em;text-transform:uppercase;margin:0}
.tx-muted{color:var(--mute);font-size:12px}
.tx-center .tx-main-grades{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.tx-main-grades strong{font:900 33px var(--num,sans-serif);padding:9px 0;border:1px solid var(--line);border-radius:8px}
.tx-credit{font-size:12px;color:var(--mute);margin:5px 0}
.tx-surplus{margin:8px;padding:9px 11px;border:1px solid var(--good);border-radius:9px;font-weight:800;color:var(--good);text-align:center;font-size:12px}
.tx-surplus small{font-size:11px;font-weight:600}
.tx-note{font-size:12px;color:var(--mute);margin:6px 0}
.tx-movement{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.tx-move{padding:9px 0;border-bottom:1px solid var(--line);font-size:13px}
.tx-move strong{font-size:14px}
.tx-bars{display:grid;grid-template-columns:1fr 1fr;gap:18px}
.tx-bar{display:flex;align-items:center;gap:8px;margin:7px 0;font-size:12px}
.tx-bar span:first-child{flex:0 0 105px}
.tx-bar meter{flex:1;min-width:30px;accent-color:var(--accent)}
.tx-bar b{width:28px;text-align:right}
.tx-empty{color:var(--mute);padding:20px 0}
@media(max-width:760px){.tx-grid{grid-template-columns:minmax(0,1fr) minmax(0,1fr)}
.tx-center{grid-column:1/-1;grid-row:2}.tx-team{font-size:15px}.tx-team img{width:34px;height:34px}
.tx-movement,.tx-bars{grid-template-columns:1fr}.tx-card header{flex-wrap:wrap}}
@media(max-width:440px){.tx-grid{gap:6px;padding:6px}.tx-team{gap:5px;padding:6px;font-size:13px}
.tx-team img{width:30px;height:30px}.tx-assets{padding:6px}.tx-asset{font-size:11px;overflow-wrap:anywhere}}
"""


def parse(value, fallback):
    if value is None or str(value).strip() in ("", "nan", "None"):
        return fallback
    try:
        out = ast.literal_eval(value)
    except (ValueError, SyntaxError):
        raise ValueError(f"Invalid transaction literal: {str(value)[:100]}")
    return fallback if out is None else out


def day(timestamp):
    return dt.datetime.fromtimestamp(int(timestamp) / 1000, tz=dt.timezone.utc).date().isoformat()


def build_teams(rows):
    return {(r["League"].strip(), str(r["Roster ID"])): r["Team"].strip() for r in rows}


def trade_assets(row, teams, players):
    """Returns {roster ID: list of labeled assets}; adds target roster wins.

    Pick owner_id is the recipient roster ID in Sleeper traded_picks. The
    original owner roster_id is used exclusively for the 'via' suffix.
    """
    league = row["LeagueName"].strip()
    rids = {str(x) for x in parse(row["RosterIDs"], [])}
    adds = parse(row["Adds"], {})
    drops = parse(row["Drops"], {})
    picks = parse(row["Picks"], [])
    rids.update(str(x) for x in adds.values())
    rids.update(str(x) for x in drops.values())
    for p in picks:
        rids.update((str(p["owner_id"]), str(p["previous_owner_id"])))
    sides = {rid: [] for rid in sorted(rids, key=lambda x: int(x))}
    for pid, rid in adds.items():
        rid = str(rid)
        p = players.get(str(pid), {})
        name = " ".join(filter(None, (p.get("first_name", ""), p.get("last_name", "")))) or f"Player {pid}"
        sides.setdefault(rid, []).append({"kind": "player", "id": str(pid), "label": name,
                                            "position": p.get("position", "")})
    for p in picks:
        to = str(p["owner_id"])
        orig = teams.get((league, str(p["roster_id"])), f"Roster {p['roster_id']}")
        label = f'{p["season"]} R{p["round"]} (via {orig})'
        sides.setdefault(to, []).append({"kind": "pick", "season": int(p["season"]),
                                           "round": int(p["round"]), "label": label})
    # The transactions file contains some trades with zero assets (e.g. rescissions);
    # display them but do not fabricate what each team received.
    return sides


def movement(rows, roster_rows, players, leagues, week):
    """League-level pickup/drop frequency, excluding trades; current ownership."""
    kinds = ("free_agent", "waiver", "commissioner")
    counts = {"adds": collections.defaultdict(set), "drops": collections.defaultdict(set)}
    for r in rows:
        if r.get("Status") != "complete" or r.get("Type") not in kinds or int(r["Week"]) != week:
            continue
        for field, bucket in (("Adds", "adds"), ("Drops", "drops")):
            for pid in parse(r.get(field), {}):
                counts[bucket][str(pid)].add(r["LeagueName"])
    owned = collections.defaultdict(set)
    for r in roster_rows:
        if r.get("PlayerID"):
            owned[str(r["PlayerID"])].add(r["LeagueName"])
    def report(bucket):
        out = []
        for pid, affected in counts[bucket].items():
            p = players.get(pid, {})
            name = " ".join(filter(None, (p.get("first_name", ""), p.get("last_name", "")))) or f"Player {pid}"
            own = owned.get(pid, set())
            out.append({"name": name, "id": pid, "count": len(affected), "owned": len(own),
                        "total": len(leagues), "available": sorted(leagues - own)})
        return sorted(out, key=lambda x: (-x["count"], x["name"]))
    return {"adds": report("adds"), "drops": report("drops")}


def summary(trades):
    con = collections.Counter(r["LeagueName"] for r in trades)
    weeks = collections.Counter(int(r["Week"]) for r in trades)
    return con, weeks


def esc(value):
    return html.escape(str(value), quote=True)


def render_team(team, colors):
    c = colors.get(team) or {}
    bg, fg = team_colors(c.get("Primary"), c.get("Secondary"), c.get("Background"),
                         c.get("Text"), name=team)
    logo = logo_html(team, prefix="../", bg=bg, alt="")
    return f'<div class="tx-team" style="--team-bg:{esc(bg)};--team-ink:{esc(fg)}">{logo}<span>{esc(team)}</span></div>'


def render_assets(assets, proxies=None, proxy_slot=None):
    if not assets:
        return '<p class="tx-muted">No assets recorded</p>'
    proxies = proxies or {}
    return "".join(f'<div class="tx-asset{" tx-pick" if a["kind"] == "pick" else ""}">'
                   + (f'<span class="tx-muted">{esc(a["position"])} · </span>' if a.get("position") else "")
                   + esc(a["label"])
                   + (f'<small class="tx-muted"> · +{proxies[a["id"]]:,.0f} pts ({esc(proxy_slot)} proxy)</small>'
                      if a.get("id") in proxies else "")
                   + "</div>" for a in assets)


def render_grade(g, name):
    if not g:
        return '<strong title="Historical valuation unavailable">—</strong>'
    score = g["score"][name]
    if score is None:
        return '<strong title="Both sides have zero measured value">—</strong>'
    raw, credit = g["raw"][name], g["credit"][name]
    points = f"{raw:,.0f} raw"
    if credit > 0.01:
        points += f" + {credit:,.0f} consolidation"
    return (f'<span class="tx-side-value" title="{points}">'
            f'<strong data-score="{score:.4f}">{esc(g["grade"][name])}</strong>'
            f'<small>{g["adjusted"][name]:,.0f} pts</small></span>')


def trade_card(r, sides, names, colors, result, shorts):
    league = r["LeagueName"]
    short = shorts.get(league, league.replace("NCAA ", ""))
    ids = list(sides)
    if len(ids) != 2:
        return ""  # Non-two-sided transactions need separate multi-team visual treatment.
    team = {rid: names.get((league, rid), f"Roster {rid}") for rid in ids}
    pairs = [(rid, team[rid], sides[rid]) for rid in ids]
    dyn, con = result.get("dynasty"), result.get("contender")
    surplus = dyn.get("surplus") if dyn else None
    proxies = result.get("proxies", {})
    proxy_slot = result.get("proxy_pick_slot")
    def panel(info):
        rid, name, assets = info
        badge = ""
        if surplus and surplus["team"] == rid:
            swap = surplus.get("swap")
            picks = surplus["picks"]
            if swap:
                label = f'≈ Pick swap · {swap["from"]} → {swap["to"]}'
            else:
                label = " + ".join(("≈ " if estimated else "") + f"Pick {slot}"
                                   for _, slot, estimated in picks)
            suffix = f' · {esc(label)}' if label else ""
            badge = (f'<div class="tx-surplus">Dynasty surplus{suffix}<br>'
                     f'<small>+{surplus["value"]:,.0f} adjusted points'
                     f'{" · estimated slots" if swap or any(p[2] for p in picks) else ""}</small></div>')
        return (f'<div class="tx-side">{render_team(name, colors)}<div class="tx-assets">'
                f'<div class="tx-receives">Receives</div>{render_assets(assets, proxies.get(rid), proxy_slot)}</div>{badge}</div>')
    status = result.get("status")
    grade_rows = ""
    for key, label in ((dyn, "Rebuild value"), (con, "Contender value")):
        note = " · No measurable value" if key and key["score"][ids[0]] is None else ""
        grade_rows += (f'<div class="tx-grade">{render_grade(key, ids[0])}<span>{label}{note}</span>'
                       f'{render_grade(key, ids[1])}</div>')
    fit = '<div class="tx-muted">Team Fit: historical context model pending validation</div>'
    missing_label = ("No values from that week" if not result.get("player_date")
                     else "Historical values unavailable")
    center = (f'<div class="tx-center"><h3>Trade evaluation</h3>{fit}{grade_rows}'
              + (f'<div class="tx-muted">{missing_label}</div>' if status != "complete" else
                 f'<div class="tx-muted">FantasyCalc snapshot {esc(result.get("player_date"))}</div>')
              + '</div>')
    credit = ""
    if dyn:
        for rid in ids:
            amt = dyn["credit"].get(rid, 0)
            if amt > 0.01:
                credit = f'<div class="tx-credit">+{amt:,.0f} consolidation credit to {esc(team[rid])} (KTC-style)</div>'
    blockbuster = result.get("blockbuster")
    flag = (f'<span class="tx-flag" title="{blockbuster["points"]:,.0f} combined raw dynasty market points'
            f' ({blockbuster["multiple"]:.2f}× snapshot leader). Top traded player: '
            f'{blockbuster["headliner_points"]:,.0f} points ({blockbuster["headliner_share"]:.0%} of leader).">'
            'Blockbuster</span>' if blockbuster else "")
    card_class = "tx-card tx-blockbuster" if blockbuster else "tx-card"
    meta = (f'<div class="tx-head">{esc(short)} · Week {esc(r["Week"])} · {esc(day(r["Created"]))}{flag}</div>'
            f'<span class="tx-muted">Trade {esc(r["TransactionID"])}</span>')
    return (f'<article class="{card_class}" data-conference="{esc(league)}" data-week="{esc(r["Week"])}" '
            f'data-teams="{esc("|".join(team.values()))}" data-identity="{esc(short)}:{esc(ids[0])}|{esc(short)}:{esc(ids[1])}"><header>{meta}</header>'
            f'<div class="tx-grid">{panel(pairs[0])}{center}{panel(pairs[1])}</div>'
            f'{credit}</article>')


def render_movement(rows, short):
    if not rows:
        return '<p class="tx-empty">No player movement this week.</p>'
    return "".join(f'<div class="tx-move"><strong>{esc(r["name"])}</strong> '
                   f'{"picked up in" if r.get("_type") == "adds" else "dropped in"} '
                   f'{r["count"]} {("conference" if r["count"] == 1 else "conferences")} · '
                   f'now owned in {r["owned"]}/{r["total"]}'
                   + (f' (available in {esc(", ".join(short.get(x, x.replace("NCAA ", "")) for x in r["available"]))})'
                      if r["available"] else " (none available)")
                   + '</div>' for r in rows)


def main():
    rows = [r for r in read_rows(TRANSACTIONS) if r.get("Status") == "complete"
            and str(r.get("Year")) == str(lcfg.season())]
    names = build_teams(read_rows(TEAMS))
    players = {str(p["player_id"]): p for p in read_rows(PLAYERS)}
    rosters = read_rows(ROSTERS)
    player_hist = read_rows(PLAYER_VALUES)
    pick_hist = read_rows(PICK_VALUES)
    short = lcfg.league_display()
    colors = {}
    for name in set(names.values()):
        c = tn.colors_row(name)
        if c is not None:
            colors[name] = dict(c)
    grading_config = load_config()
    trades = sorted((r for r in rows if r["Type"] == "trade"),
                    key=lambda r: int(r["Created"]), reverse=True)
    cards = []
    covered = 0
    for r in trades:
        sides = trade_assets(r, names, players)
        if len(sides) != 2:
            print(f'WARN: skipping non-two-party trade {r["TransactionID"]}')
            continue
        result = evaluate_trade(sides, day(r["Created"]), player_hist, pick_hist, int(r["Year"]), grading_config)
        if result["dynasty"] and any(g is not None for g in result["dynasty"]["grade"].values()):
            covered += 1
        cards.append(trade_card(r, sides, names, colors, result, short))
    lg = sorted({r["LeagueName"] for r in rows})
    weeks = sorted({int(r["Week"]) for r in rows})
    last = max(weeks, default=1)
    mv = {str(w): movement(rows, rosters, players, set(lg), w) for w in weeks}
    for m in mv.values():
        for kind in ("adds", "drops"):
            for r in m[kind]:
                r["_type"] = kind
    summ_lg, summ_wk = summary(trades)
    filters = (f'<div class="tx-controls"><label>Conference<select id="tx-conference">'
               '<option value="">All conferences</option>' +
               ''.join(f'<option value="{esc(k)}">{esc(short.get(k, k))}</option>' for k in lg) +
               '</select></label><label>Week<select id="tx-week"><option value="">All weeks</option>' +
               ''.join(f'<option value="{w}">Week {w}</option>' for w in weeks) +
               '</select></label><label>Team<select id="tx-team"><option value="">All teams</option>' +
               ''.join(f'<option value="{esc(n)}">{esc(n)}</option>' for n in sorted(set(names.values()))) +
               '</select></label></div>')
    bars_l = "".join(f'<div class="tx-bar"><span>{esc(short.get(k, k))}</span><meter min="0" max="{max(summ_lg.values(), default=1)}" value="{v}"></meter><b>{v}</b></div>'
                     for k, v in sorted(summ_lg.items(), key=lambda x: (-x[1], x[0])))
    bars_w = "".join(f'<div class="tx-bar"><span>Week {w}</span><meter min="0" max="{max(summ_wk.values(), default=1)}" value="{summ_wk[w]}"></meter><b>{summ_wk[w]}</b></div>'
                     for w in sorted(summ_wk))
    latest_stamp = day(max((r["Created"] for r in rows), default="0")) if rows else "N/A"
    generated = dt.datetime.now(dt.timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    body = f"""
<div class="wrap">
{menu_html("transactions")}
<header><div><div class="eyebrow">{lcfg.season()} season · generated {esc(generated)} · latest transaction {esc(latest_stamp)}</div>
<h1>{esc(lcfg.brand())} <em>Transactions</em></h1></div></header>
<section><h2>Trades <small>({len(cards)})</small></h2>
{filters}
<p class="tx-note">Grades use FantasyCalc values available at trade time — not a verdict.
Rebuild includes rookie picks. Contender values traded picks at zero. Unlisted kickers and D/ST use a {esc(grading_config["proxy_pick_slot"])} proxy in both grades. Surplus pick comparisons use the upcoming draft at trade time. Blockbuster marks a large raw dynasty deal with a high-value player, both measured against the snapshot’s top player. It does not indicate a winner. Team Fit and projected wins/odds
await a validated historical context model.</p>
<div class="tx-cards" id="tx-trades">{''.join(cards)}</div>
<p class="tx-empty" id="tx-no-trades" hidden>No trades match these filters.</p>
<p class="tx-note">{covered} of {len(cards)} trades have a Rebuild grade under the historical valuation rules.</p>
</section>
<section><h2>Player movement</h2>
<div class="tx-controls"><label>Week<select id="tx-move-week">{
''.join(f'<option value="{w}"{" selected" if w == last else ""}>Week {w}</option>' for w in weeks)}</select></label></div>
<p class="tx-note">Distinct conferences with a completed free-agent, waiver or commissioner move;
trades excluded. Ownership and availability are from the current roster snapshot.</p>
<div class="tx-movement"><div><h3>Most added</h3><div id="tx-adds"></div></div>
<div><h3>Most dropped</h3><div id="tx-drops"></div></div></div></section>
<section><h2>Season summary</h2><div class="tx-bars"><div><h3>Trades by conference</h3>{bars_l}</div>
<div><h3>Trades by week</h3>{bars_w}</div></div></section>
</div>"""
    js = """
<script>
(function(){
  'use strict';
  const m = __MOVEMENT__;
  const labels = __LABELS__;
  const cards = [...document.querySelectorAll('#tx-trades .tx-card')];
  const conference = document.getElementById('tx-conference');
  const week = document.getElementById('tx-week');
  const team = document.getElementById('tx-team');
  function filter(){
    let count = 0;
    for(const c of cards){
      const visible = (!conference.value || conference.value === c.dataset.conference)
        && (!week.value || week.value === c.dataset.week)
        && (!team.value || c.dataset.teams.split('|').includes(team.value));
      c.hidden = !visible; if(visible) count++;
    }
    document.getElementById('tx-no-trades').hidden = !!count;
  }
  [conference,week,team].forEach(el => el.addEventListener('change',filter));
  const esc = s => String(s).replace(/[&<>"']/g,c=>({'&':'&amp;','<':'&lt;','>':'&gt;','"':'&quot;',"'":'&#39;'}[c]));
  function renderMove(){
    const d = m[document.getElementById('tx-move-week').value] || {adds:[],drops:[]};
    for(const key of ['adds','drops']){
      const root = document.getElementById('tx-'+key);
      const list = d[key] || [];
      root.innerHTML = list.length ? list.map(p => '<div class="tx-move"><strong>'+esc(p.name)+'</strong> '+
        (key==='adds'?'picked up in ':'dropped in ')+p.count+' '+(p.count===1?'conference':'conferences')+
        ' · now owned in '+p.owned+'/'+p.total+(p.available.length?' (available in '+
        p.available.map(x=>esc(labels[x] || x.replace('NCAA ',''))).join(', ')+')':' (none available)')+'</div>').join('')
        : '<p class="tx-empty">No '+key+' this week.</p>';
    }
  }
  document.getElementById('tx-move-week').addEventListener('change',renderMove);
  renderMove();
  // Shared semantic grade scale; colors follow user-selected tokens without depending on
  // an unimplemented accessibility settings API. Grades and colors use the SAME score.
  function paint(){
    for(const el of document.querySelectorAll('[data-score]')){
      const scale = window.NCAA180 && NCAA180.colors && NCAA180.colors.scale;
      if(scale) el.style.color = scale(Number(el.dataset.score)/100);
      else el.style.color = 'var(--neutral)';
    }
  }
  paint();
  const observer = new MutationObserver(paint);
  const token = document.getElementById('n180-tokens');
  if(token) observer.observe(token,{childList:true,characterData:true,subtree:true});
  function myTeam(){
    const fn = window.NCAA180 && NCAA180.myTeam;
    if(typeof fn !== 'function') return;
    try {
      const mine = fn();
      if(mine && mine.conf && mine.roster){
        for(const c of cards) c.classList.toggle('mine',c.dataset.identity.split('|').includes(mine.conf+':'+mine.roster));
      }
    } catch(e){ console.warn('myTeam unavailable',e); }
  }
  myTeam();
})();
</script>"""
    js = js.replace("__MOVEMENT__", json.dumps(mv, ensure_ascii=False).replace("</", "<\\/"))
    js = js.replace("__LABELS__", json.dumps(short, ensure_ascii=False).replace("</", "<\\/"))
    html_out = page_head("Transactions — NCAA 180", CSS) + body + js + SECTIONS_JS + "</body></html>"
    Path(OUT).parent.mkdir(parents=True, exist_ok=True)
    Path(OUT).write_text(html_out, encoding="utf-8")
    print(f"Wrote {OUT}: {len(cards)} trades, {covered} graded, {len(weeks)} weeks, {len(lg)} conferences")


if __name__ == "__main__":
    main()
