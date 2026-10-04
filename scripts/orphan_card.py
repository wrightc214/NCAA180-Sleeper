"""
orphan_card.py -- shareable "Open teams" recruiting graphic for the LM.

  python scripts/orphan_card.py check   -> writes render=true/false to $GITHUB_OUTPUT
  python scripts/orphan_card.py render  -> writes reports/orphans.html + reports/orphans.png,
                                           saves the fingerprint with posted=false

Re-renders ONLY when the set of open orphan teams changes or a rookie draft completes
(picks turn into players) -- not when weekly player values move. Fingerprint = sorted
active orphan teams + completed draft IDs + CARD_VERSION (bump to force a redraw after
a design change). Stored in data/OrphanCard_Current.json. Missing file -> render.

Per team: logo, team, conference, top players by FantasyCalc dynasty value, and the
team's best owned future picks (own or acquired). Needs Playwright for `render`.
CWD must be repo root.
"""
import hashlib
import html
import json
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
from site_common import page_head  # noqa: E402

CARD_VERSION = 1
STATE = "data/OrphanCard_Current.json"
OUT_HTML = "reports/orphans.html"
OUT_PNG = "reports/orphans.png"
LOGO_DIR = "assets/logos/teams"
TOP_PLAYERS = 6
TOP_PICKS = 4
ORD = {1: "1st", 2: "2nd", 3: "3rd", 4: "4th", 5: "5th"}


def orphans():
    o = pd.read_csv("data/Orphans.csv", dtype=str)
    return o[o["Status"] == "Active"].sort_values("Team")


def fingerprint():
    teams = sorted(orphans()["Team"])
    try:
        d = pd.read_csv("data/Drafts_Season.csv", dtype=str)
        drafts = sorted(d.loc[d["Status"] == "complete", "DraftID"])
    except Exception:
        drafts = []
    raw = json.dumps({"v": CARD_VERSION, "teams": teams, "drafts": drafts})
    return hashlib.sha1(raw.encode()).hexdigest()[:16], teams


def check():
    fp, teams = fingerprint()
    try:
        old = json.load(open(STATE)).get("fingerprint")
    except Exception:
        old = None
    need = fp != old or not os.path.exists(OUT_PNG)
    print(f"render={'true' if need else 'false'}: orphans={teams}")
    gh = os.environ.get("GITHUB_OUTPUT")
    if gh:
        with open(gh, "a") as f:
            f.write(f"render={'true' if need else 'false'}\n")


def team_names():
    t = pd.read_csv("data/Teams.csv", dtype=str, encoding="utf-8-sig")
    return {(r.League, str(r._3)): r.Team for r in t.itertuples()}  # (league full name, roster id)


def assets(o, names):
    rp = pd.read_csv("data/Rosters_Players_Season.csv", dtype=str)
    pv = pd.read_csv("data/PlayerValues_Current.csv", dtype={"SleeperID": str})
    fp = pd.read_csv("data/FuturePicks_Current.csv", dtype=str)
    pk = pd.read_csv("data/PickValues_Current.csv")
    pick_val = {(int(r.Season), int(r.Round)): r.Value for r in pk.itertuples()}
    out = []
    for r in o.itertuples():
        mine = rp[(rp["LeagueName"] == r.LeagueName) & (rp["RosterID"] == str(r.RosterID))]
        pl = mine.merge(pv, left_on="PlayerID", right_on="SleeperID", how="inner")
        pl = pl.sort_values("DynastyValue", ascending=False).head(TOP_PLAYERS)
        players = [(p.Name, p.Position, p.NFLTeam if isinstance(p.NFLTeam, str) else "FA")
                   for p in pl.itertuples()]
        own = fp[(fp["LeagueName"] == r.LeagueName) & (fp["OwnerRosterID"] == str(r.RosterID))].copy()
        own["V"] = [pick_val.get((int(s), int(rd)), 0) for s, rd in zip(own["Season"], own["Round"])]
        own = own.sort_values(["V", "Season"], ascending=[False, True]).head(TOP_PICKS)
        picks = []
        for p in own.itertuples():
            label = f"{p.Season} {ORD.get(int(p.Round), p.Round)}"
            if p.OriginalRosterID != str(r.RosterID):
                label += f" (via {names.get((r.LeagueName, p.OriginalRosterID), 'trade')})"
            picks.append(label)
        n_picks = len(fp[(fp["LeagueName"] == r.LeagueName) & (fp["OwnerRosterID"] == str(r.RosterID))])
        out.append({"team": r.Team, "league": r.League, "players": players, "picks": picks,
                    "n_picks": n_picks})
    return out


def colors():
    tc = pd.read_csv("data/Colors - Teams.csv", dtype=str, encoding="utf-8-sig")
    fix = lambda c: c if isinstance(c, str) and c.startswith("#") else ("#" + c if isinstance(c, str) else None)
    return {r.Team: (fix(r.Background), fix(r.Font)) for r in tc.itertuples()}


def _lum(h):
    h = h.lstrip("#")
    c = [int(h[i:i + 2], 16) / 255 for i in (0, 2, 4)]
    c = [x / 12.92 if x <= 0.03928 else ((x + 0.055) / 1.055) ** 2.4 for x in c]
    return 0.2126 * c[0] + 0.7152 * c[1] + 0.0722 * c[2]


def _contrast(a, b):
    la, lb = sorted((_lum(a), _lum(b)), reverse=True)
    return (la + 0.05) / (lb + 0.05)


def readable(bg, fg):
    """Team font color if it reads on the team background, else white or black."""
    try:
        if fg and _contrast(bg, fg) >= 3:
            return fg
        return "#ffffff" if _contrast(bg, "#ffffff") >= _contrast(bg, "#000000") else "#000000"
    except Exception:
        return "#ffffff"


def build_html(cards):
    col = colors()
    css = """
    .wrap{max-width:1100px;margin:0 auto;padding:24px}
    .grid{display:grid;grid-template-columns:repeat(auto-fit,minmax(320px,1fr));gap:16px;margin-top:16px}
    .oc{background:var(--panel);border:1px solid var(--line);border-radius:8px;overflow:hidden}
    .oc .top{display:flex;align-items:center;gap:12px;padding:12px 14px}
    .oc .top img{width:64px;height:64px;object-fit:contain;background:#fff;border-radius:50%;padding:4px}
    .oc .top b{display:block;font:800 26px/1 var(--disp);text-transform:uppercase}
    .oc .top span{font:600 12px var(--num);letter-spacing:.12em;text-transform:uppercase;opacity:.85}
    .oc .body{padding:10px 14px 14px}
    .oc h3{font:700 12px var(--num);letter-spacing:.14em;text-transform:uppercase;color:var(--mute);margin:8px 0 4px}
    .oc ul{list-style:none;margin:0;padding:0}
    .oc li{display:flex;justify-content:space-between;gap:8px;padding:3px 0;border-bottom:1px solid var(--line);font-size:15px}
    .oc li small{font:600 12px var(--num);letter-spacing:.06em}
    .cta{margin-top:16px;font:700 18px var(--num);letter-spacing:.06em;text-transform:uppercase;text-align:center;color:var(--accent)}
    """
    parts = []
    for c in cards:
        bg, fg = col.get(c["team"], ("#14213a", "#ffffff"))
        bg = bg or "#14213a"
        fg = readable(bg, fg)
        logo = os.path.join("..", LOGO_DIR, c["team"] + ".png")
        players = "".join(f"<li>{html.escape(n)}<small>{html.escape(p)} · {html.escape(t)}</small></li>"
                          for n, p, t in c["players"]) or "<li>—</li>"
        picks = "".join(f"<li>{html.escape(p)}</li>" for p in c["picks"]) or "<li>None</li>"
        parts.append(f"""<div class="oc"><div class="top" style="background:{bg};color:{fg}">
<img src="{html.escape(logo)}" alt=""><div><b>{html.escape(c['team'])}</b><span>{html.escape(c['league'])}</span></div></div>
<div class="body"><h3>Key players</h3><ul>{players}</ul>
<h3>Top draft picks <small>({c['n_picks']} owned)</small></h3><ul>{picks}</ul></div></div>""")
    n = len(cards)
    return (page_head("NCAA 180 · Open Teams", css)
            + f"""<div class="wrap"><header><div><div class="eyebrow">Dynasty · now recruiting</div>
<h1>NCAA 180 <em>Open Teams</em></h1></div><div class="kpi"><b>{n}</b><span>team{'s' if n != 1 else ''} available</span></div></header>
<div class="grid">{''.join(parts) or '<p>No open teams right now.</p>'}</div>
<div class="cta">Interested? Message the league manager.</div></div></body></html>""")


def render():
    cards = assets(orphans(), team_names())
    open(OUT_HTML, "w", encoding="utf-8").write(build_html(cards))
    from playwright.sync_api import sync_playwright
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1100, "height": 800}, device_scale_factor=2, color_scheme="light")
        pg.goto("file://" + os.path.abspath(OUT_HTML), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        pg.locator(".wrap").screenshot(path=OUT_PNG)
        b.close()
    fp, teams = fingerprint()
    # posted=false until inactivity_report.py delivers it to the LM channel
    json.dump({"fingerprint": fp, "teams": teams, "posted": False}, open(STATE, "w"))
    print(f"Wrote {OUT_PNG} ({len(cards)} teams)")


if __name__ == "__main__":
    {"check": check, "render": render}[sys.argv[1] if len(sys.argv) > 1 else "check"]()
