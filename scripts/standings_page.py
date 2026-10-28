"""
standings_page.py -- reports/standings.html: the OverallStandings_Season.csv table
(the poll-sheet export, columns A:K) as a sortable page, with a link to the raw CSV.

Click a column header to sort; click again to reverse. Conference filter included.
CWD must be repo root. Run after standings.py.
"""
import html
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import nav_html, page_head  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

SRC = "data/OverallStandings_Season.csv"
OUT = "reports/standings.html"
CSV_URL = "../data/OverallStandings_Season.csv"

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


def main():
    if not os.path.exists(SRC):
        print(f"{SRC} missing; skipping standings page.")
        return
    df = pd.read_csv(SRC)
    cols = list(df.columns)
    num = [c for c in cols if pd.api.types.is_numeric_dtype(df[c])]
    rows = df.where(df.notna(), "").values.tolist()
    leagues = sorted(df["League"].dropna().unique()) if "League" in df else []
    opts = "".join(f'<option>{html.escape(str(l))}</option>' for l in leagues)
    head = "".join(f'<th{" class=r" if c in num else ""}><button type="button" data-i="{i}">{html.escape(c)}</button></th>'
                   for i, c in enumerate(cols))
    body = f"""
<div class="wrap">
<nav class="weeks" aria-label="Pages">{nav_html("standings")}</nav>
<header><div><div class="eyebrow">All 180 teams · regular season to date</div><h1>{lcfg.brand()} <em>Standings</em></h1></div></header>
<section>
  <div class="tools">
    <label>Conference <select id="lg"><option value="">All</option>{opts}</select></label>
    <a href="{CSV_URL}">Raw CSV</a>
  </div>
  <div class="tbl"><table id="t"><thead><tr>{head}</tr></thead><tbody></tbody></table></div>
  <p class="note">Playoff Rank: wins then total points, ties count as half a win, exact ties share a rank.
  Exp Wins: share of all 179 other teams outscored each week, summed. Luck: wins minus Exp Wins.</p>
</section>
</div>
<script>
const C = {json.dumps(cols)}, R = {json.dumps(rows, default=str)}, NUM = new Set({json.dumps([cols.index(c) for c in num])});
const tb = document.querySelector('#t tbody'), sel = document.getElementById('lg'), li = C.indexOf('League');
let key = 0, dir = 1;
function render() {{
  const f = sel.value, rs = R.filter(r => !f || r[li] === f).sort((a, b) =>
    (NUM.has(key) ? (a[key] - b[key]) : String(a[key]).localeCompare(String(b[key]))) * dir);
  tb.innerHTML = rs.map(r => '<tr>' + r.map((v, i) => `<td${{NUM.has(i) ? ' class="n"' : ''}}>${{String(v).replace(/[&<>]/g, c => ({{'&':'&amp;','<':'&lt;','>':'&gt;'}}[c]))}}</td>`).join('') + '</tr>').join('');
  document.querySelectorAll('th').forEach((th, i) => th.setAttribute('aria-sort', i === key ? (dir > 0 ? 'ascending' : 'descending') : 'none'));
}}
document.querySelectorAll('th button').forEach(b => b.onclick = () => {{ const i = +b.dataset.i; dir = i === key ? -dir : (NUM.has(i) && i !== 0 ? -1 : 1); key = i; render(); }});
sel.onchange = render;
render();
</script>
</body></html>
"""
    os.makedirs("reports", exist_ok=True)
    with open(OUT, "w", encoding="utf-8") as f:
        f.write(page_head(f"{lcfg.brand()} Standings", CSS) + body)
    print(f"Wrote {OUT}: {len(df)} teams")


if __name__ == "__main__":
    main()
