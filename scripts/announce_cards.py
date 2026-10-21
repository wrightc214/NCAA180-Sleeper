"""
announce_cards.py -- one-time "new page" announcement graphics for Discord (team-stats).

  python scripts/announce_cards.py render [managers|records|matchups|scoreboard|all] -> reports/announce/<page>.png
  python scripts/announce_cards.py post <page>     -> posts that PNG + message (short link in the text,
                                                      not on the card) to DISCORD_WEBHOOK_TEAM_STATS

Numbers come from the live data files (Managers_AllTime.csv, Records_AllTime.csv), so the card
matches the page on the day it posts. Links come from config/short_links.json (Chris's short links).
Posting is manual (Announce page workflow, run when Chris says so) and happens once per page: data/Announcements.json
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
.tl{display:flex;align-items:center;gap:8px;margin:3px 0;font-size:15px}
.tl .pt{margin-left:0;font-size:13px}
.tl .rc{color:var(--mute);font:600 14px var(--num)}
.tl .pj{margin-left:auto;font:700 16px var(--num)}
.gm{margin-top:6px;padding-top:6px;border-top:1px solid var(--line);font-size:14px;color:var(--mute);line-height:1.5}
.gm span{display:block}
.gm b{color:var(--ink)}
.tile.wide{grid-column:span 2}
.ml{display:flex;align-items:center;gap:8px;margin:5px 0;font-size:14px;flex-wrap:wrap}
.ml .pt{margin-left:0;font-size:12px}
.ml .mk{font:800 14px var(--num);min-width:118px}
.ml span{color:var(--mute)}
.foot{display:flex;justify-content:space-between;align-items:center;margin-top:18px;font-size:16px}
.foot .link{font:800 22px var(--num);color:var(--accent)}
.shot{display:block;width:100%;border:1px solid var(--line);border-radius:8px}
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
        tile("Managers tracked", f"{len(m)}", f"{len(q)} with {mp.MIN_GAMES}+ games qualify for the leaderboard"),
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

    def pills(team):
        return "".join(pill(t) for t in str(team).split("|") if t and t != "nan")

    def who(x):
        return f"<b>{e(str(x.Owner))}</b>{pills(x.Team) if isinstance(x.Team, str) else ''}"

    def game(x):  # "Beat Iowa 253.72–118.78 · Week 2" -> keep as is, plus the year
        return f"{e(str(x.Detail))}, {int(x.Year)}"

    hi, bl = rec(r, "Highest score"), rec(r, "Biggest blowout")
    ws_list = r[r["List"] == "Longest winning streak"]
    ws = ws_list.iloc[0]
    act = ws_list[ws_list["Live"] == True]  # noqa: E712
    ls = rec(r, "Longest losing streak")
    per = r[r["List"] == "Perfect seasons (12-0)"].sort_values("Year")
    cin = rec(r, "Cinderella · National Champion")
    miles = r[(r["List"] == "Milestones") & (r["Owner"] != "Nobody yet")]

    def span(x):
        return e(str(x.Detail).split(" · ")[0])

    def ended(x):
        d = str(x.Detail).split(" · ")
        return e(d[-1]) if len(d) > 1 else ""

    per_html = "".join(f'<div class="ml">{pill(t.Team)}<span>{e(str(t.Owner))} · {int(t.Year)}</span></div>'
                       for t in per.itertuples())
    mile_html = "".join(f'<div class="ml"><span class="mk">{e(str(m.Value))}</span>{pills(m.Team)}'
                        f'<b>{e(str(m.Owner))}</b><span>{e(str(m.Detail).split(" · ")[0])}</span></div>'
                        for m in miles.itertuples())
    tiles = [
        tile("Highest score", f"{float(hi.Value):.2f}", f"{who(hi)}<br>{game(hi)}"),
        tile("Biggest blowout", e(bl.Value), f"{who(bl)}<br>{game(bl)}"),
        tile("Perfect seasons · 12-0", f"{len(per)}", per_html),
        tile("Longest win streak", e(ws.Value), f"{who(ws)}<br>{span(ws)}<br>{ended(ws)}"),
    ]
    if len(act):
        a = act.iloc[0]
        tiles.append(tile("Longest active win streak", e(a.Value), f"{who(a)}<br>{span(a)} · still going"))
    tiles.append(tile("Longest losing streak", e(ls.Value),
                      f"{who(ls)}<br>{span(ls)}" + (" · still going" if ls.Live else f"<br>{ended(ls)}")))
    if cin is not None:
        tiles.append(tile("Cinderella champion", e(str(cin.Value)), f"{who(cin)}<br>{int(cin.Year)} national champion"))
    tiles.append(f'<div class="tile wide"><div class="k">First to the mark</div>{mile_html}</div>')
    return f"""<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>All-Time <em>Records</em></h1>
<p class="lede">Every real game since 2019 · champions, single games, seasons, playoffs, streaks</p>
<div class="tiles">{"".join(tiles)}</div>
</div>"""


def pct(p):
    return "<1%" if p < 1 else (">99%" if p > 99 else f"{p:.0f}%")


def matchups_html():
    g = pd.read_csv("data/MatchupProjections_Current.csv").reset_index(drop=True)
    wk = int(g["Week"].iloc[0])
    g["W"] = g["Rec"].str.split("-").str[0].astype(float)
    g["OW"] = g["OppRec"].str.split("-").str[0].astype(float)
    g["Hi"] = g[["Proj", "OppProj"]].max(axis=1)
    used = set()

    def pick(idx):
        for i in idx:
            if i not in used:
                used.add(i)
                return g.loc[i]
        return None

    def team_line(team, rec, proj, rank):
        rk = f"#{int(rank)} " if pd.notna(rank) else ""
        return f'<div class="tl">{pill(team, rk + team)}<span class="rc">{e(str(rec))}</span><span class="pj">{proj:.2f}</span></div>'

    def game(r):
        ew = ""
        if isinstance(r.EveryWeek, str) and r.EveryWeek:
            ew = (f"{e(r.EveryWeekLeader)} {e(r.EveryWeek)}" if isinstance(r.EveryWeekLeader, str) and r.EveryWeekLeader
                  else e(r.EveryWeek))
        return (team_line(r.Team, r.Rec, r.Proj, r.Rank) + team_line(r.OppTeam, r.OppRec, r.OppProj, r.OppRank)
                + f'<div class="gm"><span>Win chance: <b>{e(r.Team)} {pct(r.WinPct)}</b></span>'
                + (f'<span>Every week: <b>{ew}</b></span>' if ew else "") + "</div>")

    tiles = []
    r = pick(g.iloc[(g["WinPct"] - 50).abs().argsort()].index)
    tiles.append(tile("Coin flip", pct(r.WinPct), game(r)))
    ranked = g[g["Rank"].notna() & g["OppRank"].notna()]
    if len(ranked):
        r = pick(ranked.assign(S=ranked["Rank"] + ranked["OppRank"]).sort_values("S").index)
        tiles.append(tile("Ranked vs ranked", f"#{int(min(r.Rank, r.OppRank))} v #{int(max(r.Rank, r.OppRank))}", game(r)))
    r = pick(g.assign(S=g["W"] + g["OW"]).sort_values(["S", "WinPct"], ascending=[False, True]).index)
    tiles.append(tile("Best records", f"{e(r.Rec)} v {e(r.OppRec)}", game(r)))
    hist = g[g["EveryWeekLeader"].notna() & (g["EveryWeekLeader"] == g["OppTeam"])].sort_values("WinPct", ascending=False)
    r = pick(hist.index)
    if r is not None:
        tiles.append(tile("History says upset", e(r.OppTeam), game(r)))
    r = pick(g.sort_values("WinPct", ascending=False).index)
    tiles.append(tile("Biggest favorite", pct(r.WinPct), game(r)))
    r = pick(g.sort_values("Hi", ascending=False).index)
    tiles.append(tile("Top projection", f"{r.Hi:.2f}", game(r)))
    return f"""<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>Weekly <em>Matchups</em></h1>
<p class="lede">Week {wk} · all {len(g)} games · projected lineup, win chance, every-week head-to-head</p>
<div class="tiles">{"".join(tiles)}</div>
</div>"""


# Scoreboard card = a screenshot of the real game page (served locally, live Sleeper/ESPN data at render time).
# Game chosen by Chris for the launch post: week 7 Top 25 matchup, #2 Hawaii vs #10 BYU (Mountain West).
SCOREBOARD_GAME = {"league": "1331774599196585984", "week": 7, "roster": 1}
SHOT_ROWS = 6  # starter rows kept in the screenshot


SITE = "https://wrightc214.github.io/NCAA180-Sleeper/reports/"  # real origin: ESPN refuses cross-origin calls from localhost


def scoreboard_shot(browser, out_png):
    g = SCOREBOARD_GAME
    pg = browser.new_page(viewport={"width": 900, "height": 1400}, device_scale_factor=2, color_scheme="light")
    msgs = []
    pg.on("console", lambda m: msgs.append(m.text) if m.type == "error" else None)
    pg.on("pageerror", lambda ex: msgs.append(str(ex)))
    pg.goto(f"{SITE}scoreboard.html?league={g['league']}&week={g['week']}&roster={g['roster']}")
    try:
        pg.wait_for_function("document.getElementById('updated').textContent.startsWith('Updated')", timeout=60000)
    except Exception:
        info = pg.evaluate("[document.getElementById('updated').textContent, document.getElementById('error').textContent]")
        print(f"::error::Scoreboard did not load: {info} {msgs[:5]}")
        raise
    pg.evaluate("document.fonts.ready")
    top = pg.locator("#board .eyebrow").bounding_box()["y"]
    rows = pg.locator(".board .pr")
    last = rows.nth(min(SHOT_ROWS, rows.count()) - 1).bounding_box()
    box = pg.locator(".top").bounding_box()
    pg.screenshot(path=out_png, clip={"x": box["x"] - 2, "y": top - 4, "width": box["width"] + 4,
                                      "height": last["y"] + last["height"] - top + 8})
    pg.close()


def scoreboard_html():
    return """<div class="card">
<div class="eyebrow">New on the NCAA 180 site</div>
<h1>Live <em>Scoreboard</em></h1>
<p class="lede">Every game, player by player · live score, live win chance, minutes left · open any game from Matchups</p>
<img class="shot" src="scoreboard-shot.png" alt="">
</div>"""


BUILD = {"managers": managers_html, "records": records_html, "matchups": matchups_html, "scoreboard": scoreboard_html}
TEXT = {"managers": ("**New: All-Time Managers** 🏆\nEvery NCAA 180 manager since 2019, ranked by Legend Score. "
                     "Find your seasons, record and Lineup Skill: {link}"),
        "records": ("**New: All-Time Records** 📈\nChampions, single-game records, perfect seasons, Cinderella runs "
                    "and streaks: {link}"),
        "matchups": ("**New: Weekly Matchups** 🏈\nEvery game this week with projected lineups, pregame win chance and "
                     "the every-week head-to-head: {link}"),
        "scoreboard": ("**New: Live Scoreboard** 📺\nEvery game, player by player: live score, live win chance and minutes left. "
                       "Open it from any Matchups card or here: {link}\n"
                       "It's in a validation phase. If a score looks off, ping @Wrightc214 with the matchup.")}


def render(which):
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT_DIR, exist_ok=True)
    pages = list(BUILD) if which == "all" else [which]
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 1076, "height": 900}, device_scale_factor=2, color_scheme="light")
        for k in pages:
            if k == "scoreboard":
                scoreboard_shot(b, os.path.join(OUT_DIR, "scoreboard-shot.png"))
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


if __name__ == "__main__":
    cmd, which = (sys.argv[1:3] + ["all"])[:2] if len(sys.argv) > 1 else ("render", "all")
    {"render": render, "post": post}[cmd](which)
