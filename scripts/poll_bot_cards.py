"""
poll_bot_cards.py -- every bot's rank for every team, as shareable cards.

Builds reports/poll-bots.html: one Top 25 card + one card per league (12 teams), each row =
overall poll rank, team (team colors), record, the 8 bot ranks (rank out of all teams, shaded
best (1) -> worst (n, all teams) on the shared good/bad colour tokens, NCAA180.colors.scale, so the viewer's
Accessibility colour mode applies; best and worst struck = dropped, as in the poll), Spread (worst
bot rank minus best) and Score. Page shading runs over the full field (1 .. n). Then screenshots each
card to reports/poll-bots/NN-<slug>.png (600px wide, 2x, light theme); the screenshots keep the
hard-coded Standard green -> red shading (shade(), applied only in shoot()), since PNGs have no viewer. Uses the latest week of BotConsensus in data/Poll_Season.csv.

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
from site_common import menu_html, page_head  # noqa: E402
import league_config as lcfg  # noqa: E402 (shared settings: config/league.json)

OUT_HTML = "reports/poll-bots.html"
OUT_DIR = "reports/poll-bots"
e = html.escape

CSS = """
.card{margin:0 0 18px}
.card table{border-collapse:separate;border-spacing:0 3px;width:100%}
.card th{font:600 9px var(--num);color:var(--mute);text-align:center;padding:2px 1px;letter-spacing:0}
.card td{vertical-align:middle;border:none;padding:3px 1px}
.card td.rk{font:700 12px var(--num);text-align:center;width:28px;color:var(--ink) !important;border-radius:3px}
.card td.lg{width:22px;padding:1px}
.card td.lg img{width:22px;height:22px;object-fit:contain;display:block}
.card td.tm{padding:4px 7px;border-radius:5px;font-weight:700;font-size:13px;line-height:1.15;max-width:150px}
.card td.tm small{display:block;font-weight:500;opacity:.9;font-size:10px;color:inherit;margin:0}
.card td.b{font:700 11px var(--num);text-align:center;border-radius:3px;min-width:24px;color:var(--ink)}
.card td.b.drop{text-decoration:line-through;opacity:.55}
.card th img.bi{display:block;width:30px;height:30px;object-fit:contain;margin:0 auto 2px}
.card td.sp,.card td.sc{font:600 11px var(--num);text-align:right;padding:3px 3px}
.card h2{font-size:18px}
.card .note{font-size:11px}
"""


def shade(rank, n):
    """PNG cards only (shoot()): green (rank 1) -> pale yellow (middle) -> red (last), light enough for
    dark text. Hard-coded Standard on purpose (Discord images have no viewer); the page itself paints
    from the colour tokens (PAINT_JS). Allowlisted in tests/test_color_literals.py."""
    t = (rank - 1) / max(n - 1, 1)
    hue = 130 * (1 - t)
    return f"hsl({hue:.0f},65%,{80 - 8 * abs(0.5 - t):.0f}%)"


# Bot-vote cells: good -> bad diverging scale from the viewer's tokens, read at draw time and redrawn on
# an Accessibility change. Softened toward the panel so numbers stay readable; text is black or white,
# whichever contrasts more with the cell (always >= 4.5:1).
PAINT_JS = """<script>(function(){
function hex(c){var m=String(c).match(/\\d+/g);return m?"#"+m.slice(0,3).map(function(x){return(+x).toString(16).padStart(2,"0");}).join(""):c;}
function lum(c){var m=String(c).match(/\\d+/g).slice(0,3).map(function(x){x=x/255;return x<=0.04045?x/12.92:Math.pow((x+0.055)/1.055,2.4);});return .2126*m[0]+.7152*m[1]+.0722*m[2];}
function paint(){var C=window.NCAA180&&window.NCAA180.colors;if(!C)return;var t=C.tokens(),cs=getComputedStyle(document.body),
panel=hex(cs.backgroundColor),card=document.querySelector(".card");if(card)panel=hex(getComputedStyle(card).backgroundColor)||panel;
document.querySelectorAll(".card td[data-p]").forEach(function(td){
var c=C.mix(hex(C.scale(+td.getAttribute("data-p"),t)),panel,.45),L=lum(c);td.style.background=c;td.style.setProperty("color",(L+.05)/.05>=1.05/(L+.05)?"#000":"#fff","important");});}
paint();window.addEventListener("ncaa180:accesschange",paint);
var mq=window.matchMedia&&window.matchMedia("(prefers-color-scheme: dark)");if(mq&&mq.addEventListener)mq.addEventListener("change",paint);
})();</script>"""


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
    """Page colours: every rank (overall and bot) on the good -> bad scale over the FULL field, 1 (best) .. n (worst),
    so a Top 25 card doesn't stretch 1-25 across the whole good/bad range (CW, 5.12.2). The PNG keeps its
    card-relative Standard shading (shade(), applied in shoot())."""
    meta = [m for m in cfg["bots"] if m.get("enabled", True)]
    # PNG only: shade() spans this card's COUNTED votes (each row minus its best and worst); dropped votes
    # outside that range clip to full green/red. The page uses the full 1..n field instead (absp()).
    counted = []
    for r in rows.itertuples():
        v = sorted(x for x in (ranks.get((m["id"], r.LeagueID, r.RosterID)) for m in meta) if x is not None)
        counted += v[1:-1] if drop and len(v) >= 3 else v
    c_lo, c_hi = (min(counted), max(counted)) if counted else (1, n)

    def absp(v):  # page scale: 1 = rank 1, 0 = rank n (all teams)
        return f"{1 - (min(max(v, 1), n) - 1) / max(n - 1, 1):.4f}"

    def cell(v):  # data-p: 1 = best counted vote on this card, 0 = worst (clipped); data-r: shade() input
        x = min(max(v, c_lo), c_hi)
        r = 1 + (x - c_lo) * (n - 1) / max(c_hi - c_lo, 1)
        return f'data-p="{absp(v)}" data-r="{r:.4f}"' 
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
            (f'<td class="b{" drop" if i in (hi, lo) else ""}" {cell(v)}>{v}</td>'
             if v is not None else '<td class="b">–</td>') for i, v in enumerate(vals))
        bg, fg = col.get(r.Team, ("#14213a", "#ffffff"))
        rec = f"{int(float(r.Wins or 0))}-{int(float(r.Losses or 0))}" + (f"-{int(float(r.Ties))}" if float(r.Ties or 0) else "")
        spread = (max(ok) - min(ok)) if ok else ""
        body.append(
            f'<tr><td class="rk" data-p="{absp(int(r.Rank))}" data-r="{int(r.Rank)}">{int(r.Rank)}</td><td class="lg">{logo(r.Team)}</td>'
            f'<td class="tm" style="background:{bg};color:{fg}">{e(r.Team)}<small>{rec}{(" · " + e(r.League)) if show_lg else ""}</small></td>'
            f'{cells}<td class="sp">{spread}</td><td class="sc">{float(r.Score):+.2f}</td></tr>')
    return (f'<section class="card"><h2>{e(title)} <small>{e(sub)}</small></h2>'
            f'<div class="tbl"><table><thead><tr><th>Rk</th><th></th><th style="text-align:left">Team</th>{head}'
            f'<th>Sprd</th><th>Score</th></tr></thead><tbody>{"".join(body)}</tbody></table></div>'
            f'<p class="note">Bot ranks are out of all {n} teams. <span class="web">Colours run over all {n} teams: rank 1 = best, {n} = worst.</span>'
            f'<span class="png" hidden>Colors span the counted votes on this card: green = {c_lo}, red = {c_hi}+.</span> Struck = dropped '
            f'(each team\'s best and worst bot). Sprd = worst bot rank minus best.</p></section>')


def build():
    global N
    cfg, year, week, c, top, ranks, n = load()
    N = n
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
    legend = " · ".join(f'<b>{e(m.get("short", ""))}</b> {e(m["name"])}' for m in cfg["bots"] if m.get("enabled", True))
    doc = (page_head(f"{lcfg.brand()} bot ballots wk {week}", CSS) +
           f'<div class="wrap">{menu_html("poll-bots", ["poll"])}'
           f'<header><h1>{lcfg.brand()} <em>Bot ballots</em></h1></header>'
           + "".join(secs) + f'<p class="note">{legend}</p></div>' + PAINT_JS + '</body></html>')
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    return week


N = 0  # teams in the poll (set by build(); shade() needs it in shoot())


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
        pg.add_style_tag(content=".totop{display:none!important}")  # never in a screenshot
        pg.evaluate("document.fonts.ready")
        # Discord PNGs stay hard-coded Standard (shade()), whatever the page's token colours are.
        rs = sorted(set(pg.eval_on_selector_all(".card td[data-r]", "els => els.map(e => e.getAttribute('data-r'))")))
        pg.evaluate("""m => { document.querySelectorAll('.card td[data-r]').forEach(td => {
            td.style.background = m[td.getAttribute('data-r')]; td.style.color = '#111'; });
            document.querySelectorAll('.note .web').forEach(x => x.remove());
            document.querySelectorAll('.note .png').forEach(x => x.replaceWith(x.textContent));
            document.querySelectorAll('.note').forEach(x => x.normalize()); }""",
                    {r: shade(float(r), N) for r in rs})
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
