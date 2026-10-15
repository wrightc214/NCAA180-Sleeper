"""
managers_page.py -- reports/managers.html: All-Time Managers, default sort = Legend Score.

One row per manager (Sleeper OwnerID, shown under the latest username); tap a row for season
lines. Data files: data/Managers_AllTime.csv, data/ManagerSeasons_AllTime.csv.

LEGEND SCORE (Chris, 2026-10-14) -- points for outcomes, printed on the page so anyone can redo it:
  regular-season win 1 (tie 1/2) · unbeaten regular season (11-0) +5 · division title (CCG
  appearance) 3 · conference title (CCG win) +5 · bowl win 2 (2020 third-place game winner too)
  · NIT champion 4 / runner-up 2 · playoff appearance 5 · reached Sweet 16 +3 · Elite 8 +4 ·
  Final Four +6 · title game +8 · national title +25.
  One ladder for every year: 2019 (16-team field, starts at the Sweet 16) = appearance + Sweet 16;
  2020 group stage = that year's Sweet 16 step, earned as +3 x share of group rivals outscored
  (same rule as the poll's NIT/group bumps), group winners then reached the Elite 8; 2022
  "Second Round" (8 games) = Sweet 16.

Attribution: regular-season games go to the week's owner (current season corrected from the
orphan registry, as in manager_lineups.py); postseason goes to the roster's owner at the end of that
regular season. Historic seasons are stamped with the season's final owner (a mid-season departure
is credited to the successor). Orphan weeks/seasons excluded. Scores: one standard scoring system for
2019-2025 (ScoresStandard_Historic, decision 2026-10-08), official Sleeper scores for the current
season. Postseason outcomes stand as played. Lineup columns come from ManagerLineup_Career.csv.
Qualified = at least 22 regular-season games (two full seasons). CWD must be repo root.
"""
import html
import json
import os
import sys
from collections import defaultdict

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import manager_lineups as ml  # noqa: E402
import team_names as tn  # noqa: E402
from site_common import nav_html, page_head, team_colors  # noqa: E402

OUT = "reports/managers.html"
OUT_MGR = "data/Managers_AllTime.csv"
OUT_SEASONS = "data/ManagerSeasons_AllTime.csv"
POST = "data/Postseason_Historic.csv"
STANDARD = "data/ScoresStandard_Historic.csv"
LINEUP = "data/ManagerLineup_Career.csv"
LINEUP_SEASON = "data/ManagerLineup_Season.csv"
MIN_GAMES = ml.CAREER_MIN_GAMES
e = html.escape

POINTS = {"win": 1, "unbeaten": 5, "division": 3, "conference": 5, "bowl": 2, "nit_champ": 4, "nit_runner": 2,
          "playoff": 5, "s16": 3, "e8": 4, "f4": 6, "final": 8, "title": 25}
LADDER = {"First Round": 1, "Group Stage": 1, "Sweet 16": 2, "Second Round": 2, "Elite 8": 3,
          "Final Four": 4, "National Championship": 5}
FINISH = {5: "Title game", 4: "Final Four", 3: "Elite 8", 2: "Sweet 16", 1: "Playoffs"}


def split(v):
    return [x.strip() for x in str(v).split("|")] if isinstance(v, str) and v.strip() else []


def regular_season(current_year):
    frames = [ml.matchups(y, y == current_year) for y in range(2019, current_year + 1)]
    m = pd.concat(frames, ignore_index=True)
    m["LeagueName"] = m["LeagueName"].str.strip()
    m["Year"] = m["Year"].astype(int)
    m["PF"] = m["PointsFor"].astype(float)
    if os.path.exists(STANDARD):
        s = pd.read_csv(STANDARD, dtype={"LeagueID": str, "RosterID": str})
        s = s.rename(columns={"PointsStandard": "Std"})[["Year", "LeagueID", "Week", "RosterID", "Std"]]
        m = m.merge(s, on=["Year", "LeagueID", "Week", "RosterID"], how="left")
        m["PF"] = m["Std"].fillna(m["PF"])
    # all-play: share of every other team outscored that week (ties half)
    r = m.groupby(["Year", "Week"])["PF"].rank(method="average")
    n = m.groupby(["Year", "Week"])["PF"].transform("size")
    m["APW"], m["APG"] = r - 1, n - 1
    return m


def postseason(current_year):
    """{(Year, LeagueName, RosterID): dict of season postseason facts}."""
    if not os.path.exists(POST):
        return {}, []
    p = pd.read_csv(POST, dtype=str)
    out = defaultdict(lambda: defaultdict(float))
    unmatched = set()
    cache = {}

    def key(year, team):
        if (year, team) not in cache:
            cache[(year, team)] = tn.slot(year, team)
        s = cache[(year, team)]
        if s is None:
            unmatched.add((year, team))
            return None
        return (year, s[0].strip(), str(s[1]))

    for r in p.itertuples():
        y = int(r.Season)
        if y >= current_year:
            continue
        teams = split(r.TeamA) + split(r.TeamB)
        win = str(r.Winner).strip() if isinstance(r.Winner, str) else ""
        if r.Event == "CCG":
            for t in teams:
                k = key(y, t)
                if k:
                    out[k]["division"] = 1
            k = key(y, win) if win else None
            if k:
                out[k]["conference"] = 1
        elif r.Event == "Bowl" or (r.Event == "Playoff" and r.RoundName == "Third Place"):
            k = key(y, win) if win else None
            if k:
                out[k]["bowl"] += 1
        elif r.Event == "NIT" and r.RoundName == "Final":
            for t in teams:
                k = key(y, t)
                if k:
                    out[k]["nit"] = max(out[k]["nit"], 2 if t == win else 1)
        elif r.Event == "Playoff" and r.RoundName in LADDER:
            step = LADDER[r.RoundName]  # 2019's Sweet 16 start = appearance + Sweet 16 (step 2)
            group = r.RoundName == "Group Stage"
            scores = [float(x) for x in split(r.ScoreA)] if group else []
            for i, t in enumerate(teams):
                k = key(y, t)
                if not k:
                    continue
                out[k]["reached"] = max(out[k]["reached"], step)
                if group and len(scores) == len(teams):
                    beat = sum(1 for j, s in enumerate(scores) if j != i and scores[i] > s)
                    out[k]["group_share"] = beat / (len(teams) - 1)
            if r.RoundName == "National Championship":
                k = key(y, win) if win else None
                if k:
                    out[k]["title"] = 1
    return out, sorted(unmatched)


def season_points(row, ps):
    """Legend points for one manager-season and the finish label."""
    pts = POINTS["win"] * row["W"]
    if row["Unbeaten"]:
        pts += POINTS["unbeaten"]
    if not ps:
        return pts, ""
    pts += POINTS["division"] * ps.get("division", 0) + POINTS["conference"] * ps.get("conference", 0)
    pts += POINTS["bowl"] * ps.get("bowl", 0)
    nit = ps.get("nit", 0)
    pts += POINTS["nit_champ"] if nit == 2 else POINTS["nit_runner"] if nit == 1 else 0
    reached = int(ps.get("reached", 0))
    if reached >= 1:
        pts += POINTS["playoff"]
        if "group_share" in ps:  # 2020: group stage is the Sweet 16 step, earned by share
            pts += POINTS["s16"] * ps["group_share"]
        elif reached >= 2:
            pts += POINTS["s16"]
        pts += POINTS["e8"] * (reached >= 3) + POINTS["f4"] * (reached >= 4) + POINTS["final"] * (reached >= 5)
        pts += POINTS["title"] * ps.get("title", 0)
    finish = []
    if ps.get("title"):
        finish.append("National champion")
    elif reached:
        finish.append(FINISH[reached])
    if ps.get("conference"):
        finish.append("Conference champion")
    elif ps.get("division"):
        finish.append("Division champion")
    if nit == 2:
        finish.append("NIT champion")
    elif nit == 1:
        finish.append("NIT runner-up")
    if ps.get("bowl"):
        finish.append("Bowl win")
    return round(pts, 2), " · ".join(finish)


def build():
    year = int(pd.read_csv(ml.LEAGUES, dtype=str)["Year"].astype(int).max())
    m = regular_season(year)
    m = m[~m["Orphan"]]
    post, unmatched = postseason(year)
    if unmatched:
        print(f"WARNING: {len(unmatched)} postseason names match no roster slot: {unmatched[:10]}")

    g = m.groupby(["Year", "LeagueName", "RosterID", "OwnerID"])
    s = g.agg(OwnerName=("OwnerName", "last"), LastWeek=("Week", "max"),
              W=("Outcome", lambda x: (x == "Win").sum() + 0.5 * (x == "Tie").sum()),
              Wn=("Outcome", lambda x: (x == "Win").sum()), L=("Outcome", lambda x: (x == "Loss").sum()),
              T=("Outcome", lambda x: (x == "Tie").sum()), G=("Outcome", "size"), PF=("PF", "sum"),
              APW=("APW", "sum"), APG=("APG", "sum")).reset_index()
    s["Unbeaten"] = (s["L"] == 0) & (s["T"] == 0) & (s["G"] == 11)
    # postseason goes to the owner of the slot's last regular-season week
    last = m.sort_values("Week").groupby(["Year", "LeagueName", "RosterID"])["OwnerID"].last()
    s["SeasonOwner"] = [last.get((y, l, r)) == o for y, l, r, o in zip(s.Year, s.LeagueName, s.RosterID, s.OwnerID)]
    pts, fin, flags = [], [], []
    for r in s.to_dict("records"):
        ps = post.get((r["Year"], r["LeagueName"], r["RosterID"])) if r["SeasonOwner"] else None
        p, f = season_points(r, ps)
        pts.append(p)
        fin.append(f)
        ps = ps or {}
        flags.append({"Playoff": int(ps.get("reached", 0) >= 1), "FinalFour": int(ps.get("reached", 0) >= 4),
                      "Title": int(ps.get("title", 0)), "Conf": int(ps.get("conference", 0)),
                      "Bowl": int(ps.get("bowl", 0))})
    s["Legend"], s["Finish"] = pts, fin
    s = pd.concat([s, pd.DataFrame(flags)], axis=1)
    s["Team"] = [tn.season_name(y, l, r) or "" for y, l, r in zip(s.Year, s.LeagueName, s.RosterID)]
    import poll_common as pc
    short = pc.league_short()
    s["League"] = [short.get(n.upper(), n) for n in s["LeagueName"]]

    ls = pd.read_csv(LINEUP_SEASON, dtype={"OwnerID": str}) if os.path.exists(LINEUP_SEASON) else pd.DataFrame()
    if len(ls):
        s = s.merge(ls[["Year", "OwnerID", "LineupSkill"]], on=["Year", "OwnerID"], how="left")
    else:
        s["LineupSkill"] = float("nan")

    seasons = s.sort_values(["Year", "LastWeek"])
    mg = seasons.groupby("OwnerID").agg(
        Manager=("OwnerName", "last"), Team=("Team", "last"), TeamLeague=("LeagueName", "last"),
        TeamRoster=("RosterID", "last"), Seasons=("Year", "nunique"), Legend=("Legend", "sum"),
        Wins=("Wn", "sum"), Losses=("L", "sum"), Ties=("T", "sum"), Games=("G", "sum"), PF=("PF", "sum"),
        APW=("APW", "sum"), APG=("APG", "sum"), Conf=("Conf", "sum"), Playoffs=("Playoff", "sum"),
        FinalFours=("FinalFour", "sum"), Titles=("Title", "sum"), BowlWins=("Bowl", "sum")).reset_index()
    mg["Legend"] = mg["Legend"].round(1)
    mg["WinPct"] = ((mg["Wins"] + 0.5 * mg["Ties"]) / mg["Games"]).round(3)
    mg["PPG"] = (mg["PF"] / mg["Games"]).round(2)
    mg["AllPlayPct"] = (mg["APW"] / mg["APG"]).round(3)
    mg["Qualified"] = mg["Games"] >= MIN_GAMES
    if os.path.exists(LINEUP):
        lc = pd.read_csv(LINEUP, dtype={"OwnerID": str})
        mg = mg.merge(lc[["OwnerID", "LineupSkill", "PtsLeftPerGame", "PerfectWeeks", "BeatProjPerGame",
                          "BeatProjGames"]], on="OwnerID", how="left")
    mg = mg.sort_values(["Legend", "Titles", "Wins"], ascending=False).reset_index(drop=True)
    mg.drop(columns=["APW", "APG", "PF"]).to_csv(OUT_MGR, index=False)
    seasons[["Year", "OwnerID", "OwnerName", "LeagueName", "RosterID", "Team", "Wn", "L", "T", "G", "PF", "Legend",
             "Finish", "LineupSkill"]].rename(columns={"Wn": "W", "OwnerName": "Manager"}).round(
        {"PF": 2, "Legend": 2, "LineupSkill": 3}).to_csv(OUT_SEASONS, index=False)
    write_page(mg, seasons, year)
    print(f"Wrote {OUT}, {OUT_MGR} ({len(mg)} managers, {int(mg['Qualified'].sum())} qualified), {OUT_SEASONS}")
    return mg


def chip(name, fallback=None):
    row = tn.colors_row(name) or (tn.colors_row(fallback) if fallback else None)
    if row is None:
        return "#14213a", "#ffffff"
    return team_colors(row["Primary"], row["Secondary"], row.get("Background", ""), row.get("Text", ""), name=name)


CSS = """
.tools{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between}
.tools input[type=search]{font:600 14px var(--num);padding:6px 9px;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink);min-width:200px}
.tools label{display:flex;gap:6px;align-items:center}
.tools a{color:var(--accent);font-weight:600}
th button{all:unset;cursor:pointer;white-space:nowrap}
th button:focus-visible{outline:2px solid var(--accent)}
th[aria-sort=ascending] button::after{content:" \\25B2"}th[aria-sort=descending] button::after{content:" \\25BC"}
td,th{white-space:nowrap}
#t tbody tr.m{cursor:pointer}
#t tbody tr.m:hover{background:var(--line)}
#t tbody tr.m td:first-child{color:inherit;font-weight:inherit}
#t td.mg b{display:inline}
#t td.mg .tr{font-size:13px;margin-left:3px;letter-spacing:1px;cursor:help}
.pt{display:inline-block;padding:2px 8px;border-radius:3px;font-weight:700;font-size:12px;line-height:1.3}
tr.x td{background:var(--panel);white-space:normal;padding:6px 10px 12px}
table.sx{width:100%;border-collapse:collapse;font-size:13px}
table.sx td,table.sx th{padding:3px 6px;border-bottom:1px solid var(--line);white-space:nowrap}
table.sx td.f{white-space:normal}
table.sx tr td:first-child{color:inherit!important;font-weight:inherit!important}
.legend{display:grid;grid-template-columns:repeat(auto-fit,minmax(230px,1fr));gap:4px 18px;margin:8px 0 0;padding:0;list-style:none;font-size:14px}
.legend li{display:flex;justify-content:space-between;border-bottom:1px dotted var(--line);padding:2px 0}
.legend b{font-family:var(--num)}
"""


def write_page(mg, seasons, year):
    def pill(name, fb=None):
        bg, fg = chip(name, fb)
        return f'<span class="pt" style="background:{bg};color:{fg}">{e(name)}</span>'

    lines = defaultdict(list)
    title_years = seasons[seasons["Title"] == 1].groupby("OwnerID")["Year"].apply(lambda y: sorted(int(v) for v in y)).to_dict()

    def trophies(oid):
        yrs = title_years.get(oid, [])
        if not yrs:
            return ""
        label = "National champion " + ", ".join(str(y) for y in yrs)
        return f' <span class="tr" title="{label}" aria-label="{label}">{"🏆" * len(yrs)}</span>'
    for r in seasons.sort_values("Year", ascending=False).itertuples():
        rec = f"{r.Wn}-{r.L}" + (f"-{r.T}" if r.T else "")
        ls = "" if pd.isna(r.LineupSkill) else f"{r.LineupSkill:.3f}"
        lines[r.OwnerID].append([int(r.Year), pill(r.Team) if r.Team else "", e(r.League), rec,
                                 f"{r.Legend:g}", ("🏆 " if r.Title else "") + e(r.Finish) + (" (in progress)" if r.Year == year else ""), ls])

    def fmt(v, d, pct=False):
        if v is None or pd.isna(v):
            return "–", None
        v = round(float(v), d)
        txt = f"{v:.{d}f}"
        return (txt[1:] if pct and txt.startswith("0") else txt), v

    # (header, numeric?, sort direction on first click, value(row) -> (display, sort key))
    cols = [
        ("#", True, -1, None),
        ("Manager", False, 1, lambda r: (f"<b>{e(r.Manager)}</b>{trophies(r.OwnerID)}", r.Manager.lower())),
        ("Legend", True, -1, lambda r: (f"{r.Legend:g}", float(r.Legend))),
        ("Current team", False, 1, lambda r: (pill(r.Team) if r.Team else "", (r.Team or "").lower())),
        ("Seasons", True, -1, lambda r: (str(int(r.Seasons)), int(r.Seasons))),
        ("W-L", True, -1, lambda r: (f"{int(r.Wins)}-{int(r.Losses)}" + (f"-{int(r.Ties)}" if r.Ties else ""),
                                     float(r.Wins) + 0.5 * float(r.Ties))),
        ("Win %", True, -1, lambda r: fmt(r.WinPct, 3, True)),
        ("PPG", True, -1, lambda r: fmt(r.PPG, 2)),
        ("All-play %", True, -1, lambda r: fmt(r.AllPlayPct, 3, True)),
        ("Conf titles", True, -1, lambda r: (str(int(r.Conf)), int(r.Conf))),
        ("Playoffs", True, -1, lambda r: (str(int(r.Playoffs)), int(r.Playoffs))),
        ("Final Fours", True, -1, lambda r: (str(int(r.FinalFours)), int(r.FinalFours))),
        ("Titles", True, -1, lambda r: (str(int(r.Titles)), int(r.Titles))),
        ("Lineup Skill", True, -1, lambda r: fmt(getattr(r, "LineupSkill", None), 3, True)),
        ("Left on bench / g", True, 1, lambda r: fmt(getattr(r, "PtsLeftPerGame", None), 2)),
        ("Beat proj / g", True, -1, lambda r: fmt(getattr(r, "BeatProjPerGame", None), 2)),
    ]
    rows = []
    for r in mg.itertuples():
        vals = [("", None)] + [c[3](r) for c in cols[1:]]
        rows.append({"id": r.OwnerID, "q": bool(r.Qualified), "c": [v[0] for v in vals], "s": [v[1] for v in vals],
                     "x": lines.get(r.OwnerID, [])})
    meta = [{"n": c[1], "d": c[2]} for c in cols]
    head = "".join(f'<th{" class=r" if c[1] else ""}><button type="button" data-i="{i}">{e(c[0])}</button></th>'
                   for i, c in enumerate(cols))
    P = POINTS
    legend_items = [
        ("Regular-season win (tie = ½)", P["win"]), ("Unbeaten regular season (11-0)", f'+{P["unbeaten"]}'),
        ("Division title (CCG appearance)", P["division"]), ("Conference title (CCG win)", f'+{P["conference"]}'),
        ("Bowl win (incl. 2020 third-place game)", P["bowl"]), ("NIT champion / runner-up", f'{P["nit_champ"]} / {P["nit_runner"]}'),
        ("Playoff appearance", P["playoff"]), ("Reached Sweet 16", f'+{P["s16"]}'), ("Reached Elite 8", f'+{P["e8"]}'),
        ("Reached Final Four", f'+{P["f4"]}'), ("Reached title game", f'+{P["final"]}'), ("National title", f'+{P["title"]}')]
    leg = "".join(f"<li><span>{e(a)}</span><b>{b}</b></li>" for a, b in legend_items)
    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("managers")}</nav>
<header><div><div class="eyebrow">Every NCAA 180 manager · 2019–{year}</div><h1>All-Time <em>Managers</em></h1></div></header>
<section>
  <div class="tools">
    <input type="search" id="q" placeholder="Find a manager or team" aria-label="Find a manager or team">
    <label><input type="checkbox" id="qual" checked> Qualified only ({MIN_GAMES}+ games)</label>
    <a href="../{OUT_MGR}">Raw CSV</a>
  </div>
  <div class="tbl"><table id="t"><thead><tr>{head}</tr></thead><tbody></tbody></table></div>
  <p class="note">Tap a manager for season-by-season lines. Records, points and all-play are regular season.
  {year} counts as played so far.</p>
</section>
<section>
  <h2>How Legend Score works</h2>
  <p>Points for what a manager's teams achieved, added up over every season.</p>
  <ul class="legend">{leg}</ul>
  <p class="note">Playoff steps add up: a national champion earns 5 + 3 + 4 + 6 + 8 + 25 = 51 from the playoffs.
  2019 started at the Sweet 16, so every 2019 playoff team gets appearance + Sweet 16. 2020's group stage counts as the
  Sweet 16 step, earned as 3 × the share of group rivals outscored; group winners then reached the Elite 8.</p>
  <h2>Other columns</h2>
  <p class="note"><b>All-play %</b>: share of every other team in NCAA 180 outscored each week.
  <b>Lineup Skill</b>: how close each lineup came to the best possible, from 0 (worst lineup you could have started)
  to 1 (best possible), pooled over every game; the worst lineup only counts players who actually scored.
  <b>Left on bench / g</b>: best possible lineup minus points started, per game.
  <b>Beat proj / g</b> ({year} on): points started minus what the lineup Sleeper's kickoff projections said to start
  would have scored.</p>
  <p class="note">Managers are tracked by Sleeper account, shown under their latest username. Regular-season games count
  for whoever owned the team that week; postseason results go to the owner at the end of that regular season.
  Before {year}, each season is credited to the owner at season's end. Orphaned (caretaker or vacant) teams are
  excluded. 2019–{year - 1} points use one standard scoring system; results stand as played.</p>
</section>
</div>
<script>
const R = {json.dumps(rows)}, M = {json.dumps(meta)}, LEGEND = 2;
const tb = document.querySelector('#t tbody'), q = document.getElementById('q'), qual = document.getElementById('qual');
let key = LEGEND, dir = -1, open = null;
function cmp(a, b) {{
  const x = a.s[key], y = b.s[key];
  if (x === null || x === undefined) return 1; if (y === null || y === undefined) return -1;
  return (typeof x === 'string' ? x.localeCompare(y) : x - y) * dir;
}}
function render() {{
  const f = q.value.trim().toLowerCase();
  const rs = R.filter(r => (!qual.checked || r.q || f) && (!f || r.s[1].includes(f) || r.s[3].includes(f))).sort(cmp);
  tb.innerHTML = rs.map((r, n) => {{
    const cells = r.c.map((v, i) => i === 0 ? `<td class="n">${{n + 1}}</td>` : `<td${{M[i].n ? ' class="n"' : (i === 1 ? ' class="mg"' : '')}}>${{v}}</td>`).join('');
    let x = '';
    if (open === r.id) x = `<tr class="x"><td colspan="${{M.length}}"><table class="sx"><thead><tr><th>Year</th><th>Team</th><th>League</th><th class="r">W-L</th><th class="r">Legend</th><th>Finish</th><th class="r">Lineup Skill</th></tr></thead><tbody>` +
      r.x.map(l => `<tr><td class="n">${{l[0]}}</td><td>${{l[1]}}</td><td>${{l[2]}}</td><td class="n">${{l[3]}}</td><td class="n">${{l[4]}}</td><td class="f">${{l[5]}}</td><td class="n">${{l[6] ? l[6].replace(/^0/, '') : '–'}}</td></tr>`).join('') + '</tbody></table></td></tr>';
    return `<tr class="m" data-id="${{r.id}}" tabindex="0" aria-expanded="${{open === r.id}}">${{cells}}</tr>${{x}}`;
  }}).join('');
  document.querySelectorAll('#t > thead th').forEach((th, i) => th.setAttribute('aria-sort', i === key ? (dir > 0 ? 'ascending' : 'descending') : 'none'));
}}
document.querySelectorAll('#t > thead th button').forEach(b => b.onclick = () => {{
  const i = +b.dataset.i; if (i === 0) {{ key = LEGEND; dir = -1; }}
  else {{ dir = i === key ? -dir : M[i].d; key = i; }} render(); }});
tb.addEventListener('click', ev => {{ const tr = ev.target.closest('tr.m'); if (!tr) return; open = open === tr.dataset.id ? null : tr.dataset.id; render(); }});
tb.addEventListener('keydown', ev => {{ if (ev.key === 'Enter' && ev.target.matches('tr.m')) ev.target.click(); }});
q.oninput = render; qual.onchange = render;
render();
</script>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page_head("NCAA 180 All-Time Managers", CSS) + body)


if __name__ == "__main__":
    build()
