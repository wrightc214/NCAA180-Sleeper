"""
matchups_page.py -- reports/matchups.html: the upcoming week's games with projected scores and
pregame win chance, plus data/MatchupProjections_Current.csv.

Projected score = each roster's BEST projected lineup: every rostered player's Sleeper projection
(latest snapshot in data/projections/<season>/ for that week, scored with that league's own
scoring_settings), placed into the league's lineup slots with max_points.best_lineup. It ignores
who is actually in the lineup, so it is the roster's ceiling-by-projection, not the manager's call.

Win chance = Normal CDF of (projected A - projected B) / (SPREAD * sqrt(2)): each team's actual
score lands within about +/-24 points of its kickoff projection (backtest 2021-2025, 4,949 games:
residual sd 24.4; picks the winner 72.9%, calibrated within ~2 pts per bucket). Shown with the
same floor as the weekly report: never 0% or 100%.

Also flags each team's CURRENT Sleeper lineup: starters projected 0 (empty slot, bye, out).
Regular season only (postseason Sleeper pairings are fictional). CWD must be repo root.
"""
import glob
import html
import json
import math
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from max_points import ELIGIBLE, POS_ALIAS, best_lineup  # noqa: E402
from poll_page import colors, logo  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

OUT = "reports/matchups.html"
OUT_CSV = "data/MatchupProjections_Current.csv"
SPREAD = 24.0  # per-team sd around the projection (points); re-fit from history each season
LEAGUES = "data/LeagueIDs_AllYears.csv"
DEFAULT_SLOTS = ["QB", "RB", "RB", "WR", "WR", "WR", "TE", "FLEX", "FLEX", "K", "DEF"]
e = html.escape


def latest_snapshot(season):
    files = sorted(glob.glob(f"data/projections/{season}/wk*_proj.csv"))
    if not files:
        return None
    wk = max(int(re.search(r"wk(\d+)_", f).group(1)) for f in files)
    proj = sorted(f for f in files if f"/wk{wk:02d}_" in f)[-1]
    return wk, proj, proj.replace("_proj.csv", "_lineups.csv")


def slots_by_league(season):
    lg = pd.read_csv(LEAGUES, dtype=str)
    lg = lg[lg["Year"] == str(season)]
    out = {}
    for r in lg.itertuples():
        rp = getattr(r, "RosterPositions", "")
        if isinstance(rp, str) and rp:
            out[r.LeagueID] = [s for s in rp.split(",") if s not in ("BN", "IR", "TAXI")]
    return out


def score(stats, sc):
    return sum(float(v) * sc[k] for k, v in stats.items() if k in sc and isinstance(v, (int, float)))


def win_pct(a, b):
    p = 0.5 * (1 + math.erf((a - b) / (SPREAD * math.sqrt(2)) / math.sqrt(2)))
    return p * 100


def label(p):
    return "<1%" if p < 1 else (">99%" if p > 99 else f"{p:.0f}%")


def build():
    season = max(pc.seasons())
    snap = latest_snapshot(season)
    if snap is None:
        print("No projection snapshot; nothing to build.")
        return False
    wk, proj_f, line_f = snap
    if wk > int(pc.config().get("last_regular_week", 11)):
        print(f"Week {wk} is postseason; matchups page skipped (pairings are fictional).")
        return False
    proj = pd.read_csv(proj_f, dtype={"PlayerID": str})
    stamp = str(proj["SnapshotUTC"].iloc[0]) if "SnapshotUTC" in proj.columns else ""
    stats = {r.PlayerID: json.loads(r.Stats) if isinstance(r.Stats, str) and r.Stats else {} for r in proj.itertuples()}
    pos = {r.PlayerID: POS_ALIAS.get(str(r.Position), str(r.Position)) for r in proj.itertuples()}
    scoring = json.load(open(f"data/projections/{season}/scoring.json"))
    scoring = {k: {s: float(v) for s, v in d.items() if isinstance(v, (int, float))} for k, d in scoring.items()}
    slots = slots_by_league(season)
    lines = pd.read_csv(line_f, dtype=str).fillna("")

    teams = {(r.LeagueID, r.RosterID): r.Team for r in pc.teams(season).itertuples()}
    short = pc.league_short()
    rows = {}
    for r in lines.itertuples():
        sc = scoring.get(r.LeagueID, {})
        pts = {p: score(stats.get(p, {}), sc) for p in r.Players.split("|") if p}
        best = best_lineup([(v, pos.get(p, "")) for p, v in pts.items() if pos.get(p) in set().union(*ELIGIBLE.values())],
                           slots.get(r.LeagueID, DEFAULT_SLOTS))
        starters = [p for p in r.Starters.split("|")]
        zero = sum(1 for p in starters if p in ("", "0") or pts.get(p, 0) <= 0)
        cur = round(sum(pts.get(p, 0) for p in starters if p not in ("", "0")), 2)
        rows[(r.LeagueID, r.RosterID)] = {"Best": best, "Current": cur, "ZeroStarters": zero,
                                          "League": short.get(r.LeagueName.strip().upper(), r.LeagueName)}

    rk = {}
    if os.path.exists(pc.RANKS_CURRENT):
        rr = pd.read_csv(pc.RANKS_CURRENT, dtype=str)
        rk = {(r.LeagueID, r.RosterID): int(r.Rank) for r in rr.itertuples()}
    st = standings(season, wk)
    ws = weekly_scores(season, wk)

    m = pc.matchups(season)
    m = m[m["Week"] == wk]
    games, done = [], set()
    for r in m.itertuples():
        a, b = (r.LeagueID, r.RosterID), (r.LeagueID, r.OpponentRosterID)
        if frozenset((a, b)) in done or a not in rows or b not in rows:
            continue
        done.add(frozenset((a, b)))
        if rows[b]["Best"] > rows[a]["Best"]:
            a, b = b, a  # projected favorite first
        p = win_pct(rows[a]["Best"], rows[b]["Best"])
        games.append({"Year": season, "Week": wk, "LeagueID": a[0], "League": rows[a]["League"],
                      "RosterID": a[1], "Team": teams.get(a, ""), "Rank": rk.get(a, ""), "Rec": st.get(a, ""),
                      "Proj": rows[a]["Best"], "CurLineup": rows[a]["Current"], "ZeroStarters": rows[a]["ZeroStarters"],
                      "OpponentRosterID": b[1], "OppTeam": teams.get(b, ""), "OppRank": rk.get(b, ""), "OppRec": st.get(b, ""),
                      "OppProj": rows[b]["Best"], "OppCurLineup": rows[b]["Current"], "OppZeroStarters": rows[b]["ZeroStarters"],
                      "WinPct": round(p, 1), "Snapshot": stamp,
                      "EveryWeek": "-".join(str(x) for x in every_week(ws.get(a, {}), ws.get(b, {}))).removesuffix("-0")})
    g = pd.DataFrame(games)
    g.to_csv(OUT_CSV, index=False)
    write_page(g, wk, stamp)
    print(f"Wrote {OUT} and {OUT_CSV}: week {wk}, {len(g)} games (snapshot {stamp})")
    return True


def weekly_scores(season, wk):
    """{(LeagueID, RosterID): {week: points}} for regular-season weeks before `wk`."""
    m = pc.matchups(season)
    m = m[(m["Week"] < wk) & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    out = {}
    for r in m.itertuples():
        out.setdefault((r.LeagueID, r.RosterID), {})[int(r.Week)] = float(r.PointsFor)
    return out


def every_week(a, b):
    """A's record vs B if they had played every week so far: compare the two scores week by week."""
    w = l = t = 0
    for k in sorted(set(a) & set(b)):
        if a[k] > b[k]:
            w += 1
        elif a[k] < b[k]:
            l += 1
        else:
            t += 1
    return w, l, t


def standings(season, wk):
    m = pc.matchups(season)
    m = m[(m["Week"] < wk) & m["Outcome"].isin(["Win", "Loss", "Tie"])]
    out = {}
    for k, gg in m.groupby(["LeagueID", "RosterID"]):
        w, l, t = (gg["Outcome"] == "Win").sum(), (gg["Outcome"] == "Loss").sum(), (gg["Outcome"] == "Tie").sum()
        out[k] = f"{w}-{l}" + (f"-{t}" if t else "")
    return out


CSS = """
.tools{display:flex;gap:10px;align-items:center;flex-wrap:wrap}
.tools select{font:600 14px var(--num);padding:5px 8px;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink)}
.callouts{display:grid;grid-template-columns:repeat(auto-fit,minmax(220px,1fr));gap:10px}
.callouts div{border:1px solid var(--line);border-radius:6px;padding:10px 12px;background:var(--panel)}
.callouts b{display:block;font:700 12px var(--num);letter-spacing:.06em;text-transform:uppercase;color:var(--mute);margin-bottom:4px}
ul.mu{list-style:none;margin:0;padding:0;display:grid;gap:8px}
ul.mu li{border:1px solid var(--line);border-radius:6px;padding:8px 10px;background:var(--panel)}
ul.mu li.rvr{border-left:5px solid var(--gold,#c9a227)}
.side{display:grid;grid-template-columns:30px 1fr auto;align-items:center;gap:8px;margin:2px 0}
.side img{width:28px;height:28px;object-fit:contain}
.side .pt{display:inline-block;padding:3px 9px;border-radius:3px;font-weight:700;line-height:1.25;max-width:100%}
.side small{display:block;color:var(--mute);font-size:12px;margin-top:2px}
.side .n{font:700 18px var(--num);text-align:right}
.bar{display:flex;height:8px;border-radius:4px;overflow:hidden;margin:6px 0 2px;background:var(--line)}
.bar i{display:block}
.ew{font-size:12px;color:var(--mute);margin-top:3px}
.meta{display:flex;justify-content:space-between;font:600 12px var(--num);color:var(--mute)}
"""


def write_page(g, wk, stamp):
    col = colors()
    rvr = g[(g["Rank"] != "") & (g["OppRank"] != "")]
    ranked = g[((g["Rank"] != "") | (g["OppRank"] != "")) & ~g.index.isin(rvr.index)]
    rest = g[~g.index.isin(rvr.index) & ~g.index.isin(ranked.index)]

    def side(team, rank, rec, lg, projv, zero, cur):
        bg, fg = col.get(team, ("#14213a", "#ffffff"))
        r = f"#{rank} " if rank != "" else ""
        return (f'<div class="side">{logo(team)}<div><span class="pt" style="background:{bg};color:{fg}">{e(r)}{e(team)}</span>'
                f'<small>{e(rec)} · {e(lg)}</small></div><span class="n">{projv:.1f}</span></div>')

    def item(r, cls=""):
        ca = col.get(r.Team, ("#14213a", "#fff"))[0]
        cb = col.get(r.OppTeam, ("#14213a", "#fff"))[0]
        p = float(r.WinPct)
        return (f'<li class="{cls}" data-lg="{e(r.League)}">'
                + side(r.Team, r.Rank, r.Rec, r.League, r.Proj, int(r.ZeroStarters), r.CurLineup)
                + side(r.OppTeam, r.OppRank, r.OppRec, r.League, r.OppProj, int(r.OppZeroStarters), r.OppCurLineup)
                + f'<div class="bar"><i style="width:{p:.1f}%;background:{ca}"></i><i style="width:{100 - p:.1f}%;background:{cb}"></i></div>'
                + f'<div class="meta"><span>{e(r.Team)} {label(p)}</span><span>{e(r.OppTeam)} {label(100 - p)}</span></div>'
                + (f'<div class="ew">If they\'d played every week: {e(r.Team)} {e(r.EveryWeek)}</div>' if r.EveryWeek not in ("", "0-0") else "")
                + '</li>')

    def sec(title, d, note="", cls=""):
        if d.empty:
            return ""
        return f'<section><h2>{title} <small>{len(d)} game{"s" if len(d) != 1 else ""}</small></h2>{note}<ul class="mu">{"".join(item(r, cls) for r in d.itertuples())}</ul></section>'

    g2 = g.assign(gap=(g["Proj"] - g["OppProj"]).abs())
    close = g2.nsmallest(1, "gap").iloc[0]
    blow = g2.nlargest(1, "gap").iloc[0]
    gap = lambda x: f"{x:.2f}" if x < 1 else f"{x:.1f}"
    top = rvr.iloc[0] if len(rvr) else (ranked.iloc[0] if len(ranked) else None)
    calls = (f'<div><b>Closest projected game</b>{e(close.Team)} vs {e(close.OppTeam)} · {gap(close.gap)} pts · {label(float(close.WinPct))}</div>'
             f'<div><b>Biggest mismatch</b>{e(blow.Team)} over {e(blow.OppTeam)} by {blow.gap:.1f} · {label(float(blow.WinPct))}</div>'
             + (f'<div><b>Game of the week</b>{e(top.Team)} vs {e(top.OppTeam)} · {label(float(top.WinPct))} / {label(100 - float(top.WinPct))}</div>' if top is not None else ""))
    lgs = sorted(set(g["League"]))
    opts = "".join(f'<option>{e(x)}</option>' for x in lgs)
    when = ""
    mt = re.match(r"(\d{4})(\d{2})(\d{2})T(\d{2})(\d{2})", stamp or "")
    if mt:
        when = pd.Timestamp(f"{mt[1]}-{mt[2]}-{mt[3]} {mt[4]}:{mt[5]}", tz="UTC").tz_convert("America/New_York").strftime("%a %b %-d, %-I:%M %p ET")
    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("matchups")}</nav>
<header><div><div class="eyebrow">15 conferences · 180 teams · regular season</div>
<h1>NCAA 180 <em>Week {wk} matchups</em></h1></div>
<div class="kpis"><div class="kpi"><b>{len(g)}</b><span>Games</span></div><div class="kpi"><b>{len(rvr)}</b><span>Ranked vs ranked</span></div></div></header>
<section><div class="callouts">{calls}</div></section>
<section class="tools"><label for="lg">League</label><select id="lg"><option value="">All leagues</option>{opts}</select></section>
{sec("Ranked vs ranked", rvr, cls="rvr")}
{sec("Ranked teams in action", ranked)}
{sec("All other games", rest.sort_values(["League", "Team"]))}
<p class="note"><b>Big number = lineup projection:</b> each roster's best projected lineup (Sleeper projections, each league's scoring), not necessarily the lineup the manager starts. <b>If they'd played every week</b> = each team's weekly scores compared head to head for every week so far. Win chance uses the lineup projection and assumes each team scores within about ±{SPREAD:.0f} points of its projection (backtest 2021–2025: picks the winner 73% of the time). Projections as of {e(when)}; updated each Tuesday. <a href="../{OUT_CSV}">Raw CSV</a></p>
</div>
<script>
document.getElementById('lg').addEventListener('change', function () {{
  var v = this.value;
  document.querySelectorAll('ul.mu li').forEach(function (li) {{ li.hidden = !!v && li.dataset.lg !== v; }});
  document.querySelectorAll('section').forEach(function (s) {{
    var ul = s.querySelector('ul.mu'); if (!ul) return;
    s.hidden = !Array.from(ul.children).some(function (li) {{ return !li.hidden; }});
  }});
}});
</script>
</body></html>
"""
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page_head(f"NCAA 180 Week {wk} Matchups", CSS) + body)


if __name__ == "__main__":
    build()
