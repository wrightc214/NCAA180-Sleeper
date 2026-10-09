"""
poll_bot_cards.py -- every bot's rank for every team, as shareable cards.

Builds reports/poll-bots.html: one Top 25 card + one card per league (12 teams), each row =
overall poll rank, team (team colors), record, the 8 bot ranks (rank out of all teams, shaded
green = top to red = bottom; best and worst struck = dropped, as in the poll), Spread (worst
bot rank minus best) and Score. Then screenshots each card to reports/poll-bots/NN-<slug>.png
(600px wide, 2x, light theme). Uses the latest week of BotConsensus in data/Poll_Season.csv.

  python scripts/poll_bot_cards.py            build page + images
  python scripts/poll_bot_cards.py --post     also post the Top 25 card to lm-private-data
                                              (DISCORD_WEBHOOK_LM_PRIVATE_DATA)
League cards are saved for sharing; only the Top 25 card is posted. CWD must be repo root.
"""
import glob
import html
import os
import re
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import poll_common as pc  # noqa: E402
from poll_page import colors, logo  # noqa: E402
from site_common import page_head  # noqa: E402

OUT_HTML = "reports/poll-bots.html"
OUT_DIR = "reports/poll-bots"
e = html.escape

CSS = """
.card{margin:0 0 18px}
.card table{border-collapse:separate;border-spacing:0 3px;width:100%}
.card th{font:600 9px var(--num);color:var(--mute);text-align:center;padding:2px 1px;letter-spacing:0}
.card td{vertical-align:middle;border:none;padding:3px 1px}
.card td.rk{font:700 12px var(--num);text-align:center;width:28px;color:#111 !important;border-radius:3px}
.card td.lg{width:22px;padding:1px}
.card td.lg img{width:22px;height:22px;object-fit:contain;display:block}
.card td.tm{padding:4px 7px;border-radius:5px;font-weight:700;font-size:13px;line-height:1.15;max-width:150px}
.card td.tm small{display:block;font-weight:500;opacity:.9;font-size:10px;color:inherit;margin:0}
.card td.b{font:700 11px var(--num);text-align:center;border-radius:3px;min-width:24px;color:#111}
.card td.b.drop{text-decoration:line-through;opacity:.55}
.card th img.bi{display:block;width:30px;height:30px;object-fit:contain;margin:0 auto 2px}
.card td.sp,.card td.sc{font:600 11px var(--num);text-align:right;padding:3px 3px}
.card h2{font-size:18px}
.card .note{font-size:11px}
"""


def shade(rank, n):
    """Green (rank 1) -> pale yellow (middle) -> red (last), light enough for dark text."""
    t = (rank - 1) / max(n - 1, 1)
    hue = 130 * (1 - t)
    return f"hsl({hue:.0f},65%,{80 - 8 * abs(0.5 - t):.0f}%)"


def load():
    cfg = pc.config()
    p = pd.read_csv(pc.POLL_SEASON, dtype=str).fillna("")
    year = str(p["Year"].astype(int).max())
    c = p[(p["Year"] == year) & (p["PollType"] == pc.CONSENSUS)]
    week = int(c["ThroughWeek"].astype(int).max())
    c = c[c["ThroughWeek"] == str(week)].copy()
    c["_r"] = c["Rank"].astype(int)
    top = p[(p["Year"] == year) & (p["PollType"] == "Top25") & (p["ThroughWeek"] == str(week))
            & (p["Status"] == "Ranked")]
    b = pd.read_csv(pc.BOTS_SEASON, dtype=str).fillna("")
    b = b[(b["Year"] == year) & (b["ThroughWeek"] == str(week))]
    ranks = {(r.Bot, r.LeagueID, r.RosterID): int(r.Rank) for r in b.itertuples()}
    return cfg, year, week, c, top, ranks, len(c)


def card(title, sub, rows, cfg, ranks, n, col, drop, show_lg=True):
    meta = cfg["bots"]
    def icon(m):
        p = f"assets/bots/{m['id']}.png"
        return f'<img class="bi" src="../{p}" alt="">' if os.path.exists(p) else ""
    head = "".join(f'<th title="{e(m["name"])}">{icon(m)}{e(m.get("short", m["name"]))}</th>' for m in meta)
    body = []
    for r in rows.itertuples():
        k = (r.LeagueID, r.RosterID)
        vals = [ranks.get((m["id"],) + k) for m in meta]
        ok = [v for v in vals if v is not None]
        hi = vals.index(min(ok)) if drop and len(ok) >= 3 else -1
        lo = len(vals) - 1 - vals[::-1].index(max(ok)) if drop and len(ok) >= 3 else -1
        cells = "".join(
            (f'<td class="b{" drop" if i in (hi, lo) else ""}" style="background:{shade(v, n)}">{v}</td>'
             if v is not None else '<td class="b">–</td>') for i, v in enumerate(vals))
        bg, fg = col.get(r.Team, ("#14213a", "#ffffff"))
        rec = f"{int(float(r.Wins or 0))}-{int(float(r.Losses or 0))}" + (f"-{int(float(r.Ties))}" if float(r.Ties or 0) else "")
        spread = (max(ok) - min(ok)) if ok else ""
        body.append(
            f'<tr><td class="rk" style="background:{shade(int(r.Rank), n)}">{int(r.Rank)}</td><td class="lg">{logo(r.Team)}</td>'
            f'<td class="tm" style="background:{bg};color:{fg}">{e(r.Team)}<small>{rec}{(" · " + e(r.League)) if show_lg else ""}</small></td>'
            f'{cells}<td class="sp">{spread}</td><td class="sc">{float(r.Score):+.2f}</td></tr>')
    return (f'<section class="card"><h2>{e(title)} <small>{e(sub)}</small></h2>'
            f'<div class="tbl"><table><thead><tr><th>Rk</th><th></th><th style="text-align:left">Team</th>{head}'
            f'<th>Sprd</th><th>Score</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
            f'<p class="note">Bot ranks are out of all {n} teams (green = top, red = bottom). Struck = dropped '
            f'(each team\'s best and worst bot). Sprd = worst bot rank minus best.</p></section>')


def build():
    cfg, year, week, c, top, ranks, n = load()
    col = colors()
    drop = bool(cfg.get("consensus", {}).get("drop_high_low", True))
    sub = f"{year} · through week {week}"
    keys = set(zip(top["LeagueID"], top["RosterID"]))
    t25 = c[[k in keys for k in zip(c["LeagueID"], c["RosterID"])]].copy()
    if not len(t25):
        t25 = c[c["_r"] <= 25].copy()
    t25 = t25.assign(_p=t25.apply(lambda r: next((int(x.Rank) for x in top.itertuples()
                                                   if (x.LeagueID, x.RosterID) == (r.LeagueID, r.RosterID)), r._r), axis=1))
    t25 = t25.sort_values("_p").assign(Rank=lambda d: d["_p"].astype(str))
    secs = [card("Top 25 · bot ballots", sub, t25, cfg, ranks, n, col, drop)]
    for lg, g in sorted(c.groupby("League"), key=lambda x: x[0]):
        secs.append(card(f"{lg} · bot ballots", sub, g.sort_values("_r"), cfg, ranks, n, col, drop, show_lg=False))
    legend = " · ".join(f'<b>{e(m.get("short", ""))}</b> {e(m["name"])}' for m in cfg["bots"])
    doc = (page_head(f"NCAA 180 bot ballots wk {week}", CSS) +
           f'<div class="wrap"><header><h1>NCAA 180 <em>Bot ballots</em></h1></header>'
           + "".join(secs) + f'<p class="note">{legend}</p></div></body></html>')
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    return week


def shoot():
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(OUT_DIR, "*.png")):
        os.remove(f)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 600, "height": 900}, device_scale_factor=2, color_scheme="light")
        pg.goto("file://" + os.path.abspath(OUT_HTML), wait_until="networkidle")
        pg.evaluate("document.fonts.ready")
        for i, s in enumerate(pg.query_selector_all("section.card")):
            t = s.query_selector("h2").inner_text().split("\n")[0].split("·")[0]
            slug = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
            path = os.path.join(OUT_DIR, f"{i:02d}-{slug}.png")
            s.screenshot(path=path)
            made.append(path)
        b.close()
    return made


def post(week, made):
    import poll_discord as pdisc
    from discord_post import note, valid
    url = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "")
    if not valid(url):
        note("warning", "Bot ballot card not posted: DISCORD_WEBHOOK_LM_PRIVATE_DATA not set")
        return
    first = [m for m in made if os.path.basename(m).startswith("00-")]
    if first:
        pdisc.send(url, f"**Bot ballots · week {week}** (Top 25). League cards: `{OUT_DIR}/` in the repo.", files=first)


if __name__ == "__main__":
    if not os.path.exists(pc.POLL_SEASON) or not os.path.exists(pc.BOTS_SEASON):
        print("No poll data; skipping bot cards.")
        sys.exit(0)
    wk = build()
    made = shoot()
    print(f"Wrote {OUT_HTML} and {len(made)} card(s) in {OUT_DIR}/")
    if "--post" in sys.argv:
        post(wk, made)
