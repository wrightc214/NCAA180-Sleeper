"""
announce_cards.py -- one-time "new page" announcement graphics for Discord (team-stats).

  python scripts/announce_cards.py render [managers|records|matchups|all] -> reports/announce/<page>.png
  python scripts/announce_cards.py post <page>     -> posts that PNG + message (short link in the text,
                                                      not on the card) to DISCORD_WEBHOOK_TEAM_STATS
  python scripts/announce_cards.py due             -> posts the next approved, due entry of
                                                      config/announce_queue.json (one per day = spaced out)

Numbers come from the live data files (Managers_AllTime.csv, Records_AllTime.csv), so the card
matches the page on the day it posts. Links come from config/short_links.json (Chris's short links).
Posting is manual (Announce page workflow) and happens once per page: data/Announcements.json
records what went out; FORCE=1 reposts. Needs Playwright for `render`. CWD must be repo root.
"""
import html
import json
import os
import re
import sys
from datetime import datetime, timezone

import pandas as pd
import requests

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import managers_page as mp  # noqa: E402
from site_common import page_head  # noqa: E402

OUT_DIR = "reports/announce"
STATE = "data/Announcements.json"
LINKS = json.load(open("config/short_links.json"))
e = html.escape

CSS = """
body{background:var(--bg)}
.card{width:1000px;padding:34px 38px 26px;background:var(--bg)}
.eyebrow{font:700 14px var(--num);letter-spacing:.12em;text-transform:uppercase;color:var(--accent)}
h1{margin:4px 0 6px;font-size:64px;line-height:1}
.lede{font-size:19px;color:var(--mute);margin:0 0 20px;max-width:880px}
.tiles{display:grid;grid-template-columns:repeat(3,1fr);gap:12px;margin:0 0 18px}
.tile{border:1px solid var(--line);border-radius:8px;padding:14px 16px;background:var(--panel)}
.tile .k{font:700 12px var(--num);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
.tile .v{font:800 34px var(--num);line-height:1.1;margin:4px 0 4px}
.tile .d{font-size:14px;line-height:1.35}
.board{border:1px solid var(--line);border-radius:8px;background:var(--panel);padding:10px 16px 6px}
.board h2{margin:2px 0 6px;font:700 13px var(--num);letter-spacing:.08em;text-transform:uppercase;color:var(--mute)}
.board ol{list-style:none;margin:0;padding:0;columns:2;column-gap:28px}
.board li{display:grid;grid-template-columns:26px 1fr auto;align-items:center;gap:8px;padding:6px 0;border-top:1px solid var(--line);break-inside:avoid}
.board li .r{font:700 15px var(--num);color:var(--mute)}
.board li .n{font:800 20px var(--num)}
.board li b{font-size:16px}
.pt{display:inline-block;padding:2px 8px;border-radius:3px;font-weight:700;font-size:12px;line-height:1.3;margin:0 2px 0 6px}
.tile .d .pt:first-child{margin-left:0}
.foot{display:flex;justify-content:space-between;align-items:center;margin-top:18px;font-size:16px}
.foot .link{font:800 22px var(--num);color:var(--accent)}
"""


def pill(team, label=None):
    if not team:
        return ""
    bg, fg = mp.chip(team)
    return f'<span class="pt" style="background:{bg};color:{fg}">{e(label or team)}</span>'


def tile(k, v, d):
    return f'<div class="tile"><div class="k">{e(k)}</div><div class="v">{v}</div><div class="d">{d}</div></div>'


def rec(r, lst):
    x = r[r["List"] == lst]
    return x.iloc[0] if len(x) else None


def managers_html():
    m = pd.read_csv(mp.OUT_MGR, dtype={"OwnerID": str})
    s = pd.read_csv(mp.OUT_SEASONS, dtype={"OwnerID": str})
    q = m[m["Qualified"]]
    champs = s[s["Finish"].fillna("").str.contains("National champion")]
    lis = []
    for i, r in enumerate(m.head(10).itertuples(), 1):
        t = " 🏆" * int(r.Titles)
        lis.append(f'<li><span class="r">{i}</span><span><b>{e(r.Manager)}</b>{t}{pill(r.Team)}</span>'
                   f'<span class="n">{r.Legend:g}</span></li>')
    best_wp = q.sort_values(["WinPct", "Games"], ascending=False).iloc[0]
    best_ls = q.sort_values("LineupSkill", ascending=False).iloc[0]
    tiles = "".join([
        tile("Managers tracked", f"{len(m)}", f"{len(q)} with 22+ games (two full seasons) qualify for the leaderboard"),
        tile("Best win %", f"{best_wp.WinPct:.3f}".lstrip("0"),
             f"<b>{e(best_wp.Manager)}</b>{pill(best_wp.Team)} · {int(best_wp.Wins)}-{int(best_wp.Losses)}"),
        tile("Best Lineup Skill", f"{best_ls.LineupSkill:.3f}".lstrip("0"),
             f"<b>{e(best_ls.Manager)}</b>{pill(best_ls.Team)} · how close lineups came to the best possible"),
    ])
    n_ch = champs["OwnerID"].nunique()
    return f"""<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>All-Time <em>Managers</em></h1>
<p class="lede">Every manager since 2019, ranked by <b>Legend Score</b>: points for wins, conference titles and playoff
runs, with a big bonus for a national title. {len(champs)} national titles, {n_ch} different champions 🏆.</p>
<div class="tiles">{tiles}</div>
<div class="board"><h2>Legend Score · top 10</h2><ol>{"".join(lis)}</ol></div>
<div class="foot"><span>Find your name, your seasons and your Lineup Skill on the new Managers page</span></div>
</div>"""


def records_html():
    r = pd.read_csv("data/Records_AllTime.csv")

    def who(x):
        return f"<b>{e(str(x.Owner))}</b>{pill(x.Team) if isinstance(x.Team, str) else ''}"

    hi, bl, ws = rec(r, "Highest score"), rec(r, "Biggest blowout"), rec(r, "Longest winning streak")
    per = r[r["List"] == "Perfect seasons (12-0)"]
    per_titles = per["Detail"].fillna("").str.contains("National champion").sum()
    cin = rec(r, "Cinderella · National Champion")
    el = r[r["List"].str.startswith("Highest score eliminated")].sort_values("Value", key=lambda v: v.astype(float),
                                                                                ascending=False).iloc[0]
    miles = r[r["List"] == "Milestones"]
    nxt = miles[miles["Owner"] == "Nobody yet"]
    nxt_w = nxt[nxt["Value"].str.contains("wins")]
    first = miles[(miles["Owner"] != "Nobody yet") & miles["Value"].str.contains("wins")].iloc[-1]
    tiles = [
        tile("Highest score", f"{float(hi.Value):.2f}", f"{who(hi)} · {int(hi.Year)}"),
        tile("Biggest blowout", e(bl.Value), f"{who(bl)} · {int(bl.Year)}"),
        tile("Longest win streak", e(ws.Value), f"{who(ws)}<br>{e(ws.Detail.split(' · ')[-1])}"),
        tile("Perfect seasons", f"{len(per)}", f"Teams that went 12-0 (11-0 + conference title) · "
                                               f"{'none' if per_titles == 0 else per_titles} won the national title"),
        tile("Cinderella champion", e(str(cin.Value)) if cin is not None else "–",
             f"{who(cin)} · {int(cin.Year)} national champion" if cin is not None else ""),
        tile("Highest score eliminated", f"{float(el.Value):.2f}", f"{who(el)} · {int(el.Year)}<br>{e(el.Detail)}"),
    ]
    race = ""
    if len(nxt_w):
        x = nxt_w.iloc[0]
        race = (f"<b>Race to {e(x.Value)}:</b> nobody yet · {e(x.Detail.replace('Nearest: ', 'nearest: '))}. "
                f"First to {e(first.Value)}: <b>{e(str(first.Owner))}</b> ({int(first.Year)}).")
    return f"""<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>All-Time <em>Records</em></h1>
<p class="lede">Every real game since 2019: champions, single-game records, perfect seasons, playoff heartbreaks,
Cinderella runs and streaks. {race}</p>
<div class="tiles">{"".join(tiles)}</div>
<div class="foot"><span>Single-game records update live with this season's games</span></div>
</div>"""


def pct(p):
    return "<1%" if p < 1 else (">99%" if p > 99 else f"{p:.0f}%")


def matchups_html():
    g = pd.read_csv("data/MatchupProjections_Current.csv")
    wk = int(g["Week"].iloc[0])

    def side(team, proj, rank):
        rk = f"#{int(rank)} " if pd.notna(rank) else ""
        return f"{pill(team, rk + team)} {proj:.2f}"

    close = g.iloc[(g["WinPct"] - 50).abs().argsort().iloc[0]]
    fav = g.sort_values("WinPct", ascending=False).iloc[0]
    hi = g.assign(M=g[["Proj", "OppProj"]].max(axis=1)).sort_values("M", ascending=False).iloc[0]
    hi_team, hi_p = (hi.Team, hi.Proj) if hi.Proj >= hi.OppProj else (hi.OppTeam, hi.OppProj)
    ranked = g[g["Rank"].notna() & g["OppRank"].notna()]
    if len(ranked):
        rg = ranked.sort_values(["OppRank"]).iloc[0]
        top = tile("Ranked vs ranked", f"#{int(rg.Rank)} v #{int(rg.OppRank)}",
                   f"{side(rg.Team, rg.Proj, rg.Rank)} vs {side(rg.OppTeam, rg.OppProj, rg.OppRank)}<br>"
                   f"{e(rg.Team)} {pct(rg.WinPct)} to win")
    else:
        top = tile("Highest projection", f"{hi_p:.2f}", f"{pill(hi_team)} · best projected lineup this week")
    tiles = "".join([
        tile("Coin flip of the week", pct(close.WinPct),
             f"{side(close.Team, close.Proj, close.Rank)} vs {side(close.OppTeam, close.OppProj, close.OppRank)}"
             + (f"<br>If they'd played every week: {e(close.EveryWeekLeader)} {e(close.EveryWeek)}"
                if isinstance(close.EveryWeekLeader, str) and close.EveryWeekLeader else
                (f"<br>If they'd played every week: {e(close.EveryWeek)}" if isinstance(close.EveryWeek, str) else ""))),
        top,
        tile("Biggest favorite", pct(fav.WinPct),
             f"{side(fav.Team, fav.Proj, fav.Rank)} vs {side(fav.OppTeam, fav.OppProj, fav.OppRank)}"),
    ])
    return f"""<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>Weekly <em>Matchups</em></h1>
<p class="lede">All {len(g)} games every week: each roster's best projected lineup (Sleeper projections, your league's
scoring), the pregame win chance, and how the two teams would stand if they'd played each other every week so far.
Set each Tuesday; the odds don't move once posted.</p>
<div class="tiles">{tiles}</div>
<div class="foot"><span>Week {wk} is up now · find your game</span></div>
</div>"""


BUILD = {"managers": managers_html, "records": records_html, "matchups": matchups_html}
TEXT = {"managers": ("**New: All-Time Managers** 🏆\nEvery NCAA 180 manager since 2019, ranked by Legend Score. "
                     "Find your seasons, record and Lineup Skill: {link}"),
        "records": ("**New: All-Time Records** 📈\nChampions, single-game records, perfect seasons, Cinderella runs "
                    "and streaks: {link}"),
        "matchups": ("**New: Weekly Matchups** 🏈\nEvery game this week with projected lineups, pregame win chance and "
                     "the every-week head-to-head: {link}")}


def render(which):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT_DIR, exist_ok=True)
    pages = list(BUILD) if which == "all" else [which]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1076, "height": 900}, device_scale_factor=2, color_scheme="light")
        for k in pages:
            path = os.path.join(OUT_DIR, f"{k}.html")
            open(path, "w", encoding="utf-8").write(page_head(f"NCAA 180 {k}", CSS, totop=False) + BUILD[k]() + "</body></html>")
            pg.goto("file://" + os.path.abspath(path), wait_until="networkidle")
            pg.evaluate("document.fonts.ready")
            pg.locator(".card").screenshot(path=os.path.join(OUT_DIR, f"{k}.png"))
            print(f"Wrote {OUT_DIR}/{k}.png")
        b.close()


def post(which):
    hook = os.environ.get("DISCORD_WEBHOOK_TEAM_STATS", "").strip()
    if not re.match(r"^https://(discord|discordapp)\.com/api/webhooks/\d+/[\w-]+$", hook):
        print("::error::DISCORD_WEBHOOK_TEAM_STATS missing or not a Discord webhook")
        sys.exit(1)
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    if which in state and os.environ.get("FORCE") != "1":
        print(f"::notice::{which} was already announced on {state[which]}; nothing posted (FORCE=1 to repost)")
        return
    png = os.path.join(OUT_DIR, f"{which}.png")
    payload = {"content": TEXT[which].format(link=LINKS[which]), "allowed_mentions": {"parse": []}}
    r = requests.post(hook + "?wait=true", data={"payload_json": json.dumps(payload)},
                      files={"files[0]": (f"ncaa180-{which}.png", open(png, "rb"), "image/png")}, timeout=60)
    if r.status_code >= 300:
        print(f"::error::Discord did not accept the post (HTTP {r.status_code}): {r.text[:200]}")
        sys.exit(1)
    state[which] = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
    json.dump(state, open(STATE, "w"), indent=1)
    print(f"::notice::Announced {which} in team-stats")


QUEUE = "config/announce_queue.json"


def due(_=None):
    """Post the first approved queue entry whose date has come and that hasn't posted. One per run."""
    from zoneinfo import ZoneInfo
    today = datetime.now(ZoneInfo("America/New_York")).date().isoformat()
    state = json.load(open(STATE)) if os.path.exists(STATE) else {}
    for q in json.load(open(QUEUE))["queue"]:
        if q.get("approved") and q.get("post_on") and q["post_on"] <= today and q["page"] not in state:
            render(q["page"])
            post(q["page"])
            return
    print("::notice::No approved announcement due today")


if __name__ == "__main__":
    cmd, which = (sys.argv[1:3] + ["all"])[:2] if len(sys.argv) > 1 else ("render", "all")
    {"render": render, "post": post, "due": due}[cmd](which)
