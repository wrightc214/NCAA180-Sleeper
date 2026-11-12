"""
standings_page.py -- reports/standings.html: the OverallStandings_Season.csv table
(the poll-sheet export, columns A:K) as a sortable page, with a link to the raw CSV.

Click a column header to sort; click again to reverse. Conference filter included.
CWD must be repo root. Run after standings.py.
"""
import glob
import html
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import SECTIONS_JS, nav_html, page_head  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

SRC = "data/OverallStandings_Season.csv"
OUT = "reports/standings.html"
CSV_URL = "../data/OverallStandings_Season.csv"
HIST = "data/standings"

CSS = """
.tools{display:flex;flex-wrap:wrap;gap:10px 16px;align-items:center;justify-content:space-between}
.tools select{font:600 14px var(--num);padding:5px 8px;border:1px solid var(--line);border-radius:3px;background:var(--panel);color:var(--ink)}
.tools a{color:var(--accent);font-weight:600}
th button{all:unset;cursor:pointer;white-space:nowrap}
th button:focus-visible{outline:2px solid var(--accent)}
th[aria-sort=ascending] button::after{content:" ▲"}th[aria-sort=descending] button::after{content:" ▼"}
td,th{white-space:nowrap}
#t tr td:first-child{color:inherit;font-weight:inherit}
"""


def extra_columns(df):
    """Page-only columns (Chris, 2026-11-08); the CSV stays the poll-sheet export.
    Max PF: the best possible lineup's points, regular season to date (MaxPoints_Season.csv).
    Playoff %: from the postseason odds (postseason_odds.py) while they are current; Clinched/Out
    only when proven. Returns (df, {column: display texts})."""
    disp = {}
    try:
        m = pd.read_csv("data/MaxPoints_Season.csv")
        last = int(lcfg.cfg()["schedule"]["ccg_week"]) - 1
        m = m[(m["Year"] == m["Year"].max()) & (m["Week"] <= last)]
        tot = m.groupby(["LeagueName", "RosterID"])["MaxPoints"].sum().round(2)
        t = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
        name = {(r["League"].strip(), int(float(r["Roster ID"]))): r["Team"] for _, r in t.iterrows()}
        mx = {name.get((l.strip(), int(r))): v for (l, r), v in tot.items()}
        if "Points" in df and mx:
            df.insert(list(df.columns).index("Points") + 1, "Max PF", df["Team"].map(mx))
    except (OSError, KeyError, ValueError) as ex:
        print(f"Standings: Max PF skipped ({ex})")
    try:
        o = json.load(open("reports/postseason/odds.json"))
        sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
        from bowl_projection import pct
        T = {(x["Team"], x["League"]): x for x in o["teams"]}
        hit = [T.get((a, b)) for a, b in zip(df["Team"], df["League"])]
        if sum(h is not None for h in hit) >= len(df) * 0.9:
            df["Playoff %"] = [round(h["Playoff"] * 100, 1) if h else None for h in hit]
            disp["Playoff %"] = [pct(h["Playoff"], h["flags"].get("Playoff", "")) if h else "" for h in hit]
    except (OSError, KeyError, ValueError) as ex:
        print(f"Standings: playoff odds skipped ({ex})")
    return df, disp


def main():
    if not os.path.exists(SRC):
        print(f"{SRC} missing; skipping standings page.")
        return
    # Past seasons (Chris, 2026-11-11): one page + CSV per finished season (standings.py --history).
    past = sorted((int(os.path.basename(f)[17:21]), f) for f in glob.glob(os.path.join(HIST, "OverallStandings_*.csv")))
    cur = int(pd.read_csv("data/Matchups_Season.csv", usecols=["Year"])["Year"].max())
    years = [y for y, _ in past]
    for y, f in past:
        write(pd.read_csv(f), {}, y, years, cur, f"standings-{y}.html", "../" + f.replace(os.sep, "/"),
              "All 180 teams · final regular season", f"{y} final regular season. Names, conferences and divisions as played that season.")
    df = pd.read_csv(SRC)
    df, disp = extra_columns(df)
    write(df, disp, cur, years, cur, "standings.html", CSV_URL, "All 180 teams · regular season to date",
          "Max PF: points the best possible lineup would have scored. Playoff %: <a href=\"postseason.html\">postseason projection</a> odds "
          "(Clinched / Out only when proven; not official). The Raw CSV has the standings columns only.")
    print(f"Wrote {OUT}: {len(df)} teams; past seasons {years}")


def picker(year, years, cur):
    here = ' aria-current="page"'
    links = "".join(f'<a href="standings-{y}.html"{here if y == year else ""}>{y}</a>' for y in years)
    links += f'<a href="standings.html"{here if year == cur else ""}>{cur or "Current"}</a>'
    return f'<nav class="weeks sub" aria-label="Seasons"><span>Season</span>{links}</nav>'


def write(df, disp, year, years, cur, out, csv_url, eyebrow, extra_note):
    cols = list(df.columns)
    num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    rows = df.where(df.notna(), "").values.tolist()
    leagues = sorted(df["League"].dropna().unique()) if "League" in df else []
    opts = "".join(f'<option>{html.escape(str(l))}</option>' for l in leagues)
    head = "".join(f'<th{" class=r" if c in num else ""}><button type="button" data-i="{i}">{html.escape(c)}</button></th>'
                   for i, c in enumerate(cols))
    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("standings")}</nav>{picker(year, years, cur)}
<header><div><div class="eyebrow">{eyebrow}</div><h1>{lcfg.brand()} <em>{f"{year} " if year != cur else ""}Standings</em></h1></div></header>
<section>
  <h2>All teams</h2>
  <div class="tools">
    <label>Conference <select id="lg"><option value="">All</option>{opts}</select></label>
    <a href="{csv_url}">Raw CSV{f" ({year})" if year else ""}</a>
  </div>
  <div class="tbl"><table id="t"><thead><tr>{head}</tr></thead><tbody></tbody></table></div>
  <p class="note">Playoff Rank: wins then total points, ties count as half a win, exact ties share a rank.
  Exp Wins: share of all 179 other teams outscored each week, summed. Luck: wins minus Exp Wins.
  {extra_note}</p>
</section>
</div>
<script>
const C = {json.dumps(cols)}, R = {json.dumps(rows, default=str)}, D = {json.dumps({cols.index(k): v for k, v in disp.items()})}, NUM = new Set({json.dumps([cols.index(c) for c in num])});
const tb = document.querySelector('#t tbody'), sel = document.getElementById('lg'), li = C.indexOf('League');
let key = 0, dir = 1;
function render() {{
  const f = sel.value, rs = R.filter(r => !f || r[li] === f).sort((a, b) =>
    (NUM.has(key) ? (a[key] - b[key]) : String(a[key]).localeCompare(String(b[key]))) * dir);
  tb.innerHTML = rs.map(r => '<tr>' + r.map((v, i) => (D[i] ? (v = D[i][R.indexOf(r)], 0) : 0, v)).map((v, i) => `<td${{NUM.has(i) ? ' class="n"' : ''}}>${{String(v).replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]))}}</td>`).join('') + '</tr>').join('');
  document.querySelectorAll('th').forEach((th, i) => th.setAttribute('aria-sort', i === key ? (dir > 0 ? 'ascending' : 'descending') : 'none'));
}}
document.querySelectorAll('th button').forEach(b => b.onclick = () => {{ const i = +b.dataset.i; dir = i === key ? -dir : (NUM.has(i) && i !== 0 ? -1 : 1); key = i; render(); }});
sel.onchange = render;
render();
</script>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(os.path.join("reports", out), "w", encoding="utf-8") as f:
        f.write((page_head(f"{lcfg.brand()} {str(year) + ' ' if year != cur else ''}Standings", CSS) + body).replace("</body></html>", SECTIONS_JS + "</body></html>"))


if __name__ == "__main__":
    main()
