"""
bowl_projection.py -- the Postseason page while the season is on: projected playoff field + bowls.

Chris, 2026-11-03. Remaining regular-season games and the CCG are projected (each team scores
its season average under this season's scoring; the higher average wins), then the REAL
postseason code runs on the projected standings: conference_championships -> playoff_field ->
bowls (config postseason.bowls: poll-per-win order, division-leader Marquee seat, tie-ins).
Nothing real is written: Matchups/Postseason files are untouched (the projection runs in memory
and in a scratch data dir).

Page reports/postseason.html (+ one archive page per week, reports/postseason-proj-wkNN.html):
  playoff field as first-round pairings (1 v 32 ... 16 v 17; AQ = projected conference champion,
  movement vs last week's projection) + last 4 in / first 4 out; Prestige + Marquee games (each
  Marquee team tagged league seat / at-large); "Other teams projected to go bowling" (Showcase +
  Opening: random draws, so no matchups).
Projected seeds (background only, never shown): latest consensus poll Score + seed_per_win per
projected remaining win (CCG included) - seed_per_loss per loss. The real seeds come from the
bots' Seeding ballot after the CCG.

Posting (Chris approved the format 2026-11-03; it now posts weekly with the awards and poll):
  python scripts/bowl_projection.py            build the page + data
  python scripts/bowl_projection.py --render   + screenshot the Discord cards (playoff, Prestige, Marquee)
  python scripts/bowl_projection.py --shoot    screenshot the existing page only (workflow render step)
  python scripts/bowl_projection.py --publish  post the STORED cards to the league channel (never
                                               rebuilds). The weekly job does this with the other
                                               weekly posts (Chris, 2026-11-03: no LM preview step)
  python scripts/bowl_projection.py --preview  optional: the same post to lm-private-data
Config: postseason.bowls.projection (enabled, from_week, seed_per_win/loss).
"""
import argparse
import glob
import html
import io
import json
import os
import random
import re
import sys
import tempfile
from contextlib import redirect_stdout

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowls as B  # noqa: E402
import league_config as lcfg  # noqa: E402
from poll_page import colors, logo  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

PAGE = "reports/postseason.html"
ARCHIVE = "reports/postseason-proj-wk{:02d}.html"
OUT_DIR = "reports/postseason"            # Discord cards + per-week data (movement)
META = os.path.join(OUT_DIR, "meta.json")
LINK = json.load(open(os.path.join(os.path.dirname(os.path.abspath(__file__)), "..", "config", "short_links.json")))["postseason"]
BUBBLE = 4
e = html.escape


def pcfg():
    return lcfg.cfg()["postseason"]["bowls"].get("projection", {})


def key(t):
    return (str(t["LeagueID"]), str(t["RosterID"]).replace(".0", ""))


# ------------------------------------------------------------------ projection
def poll_scores(year):
    """{(LeagueID, RosterID): (consensus Score, rank)} from the latest BotConsensus poll through the
    last regular week, and that week."""
    frames = [pd.read_csv(f, dtype=str) for f in ("data/Poll_Season.csv", "data/Poll_Historic.csv") if os.path.exists(f)]
    p = pd.concat(frames)
    p = p[(p["Year"] == str(year)) & (p["PollType"] == "BotConsensus")]
    p = p[pd.to_numeric(p["ThroughWeek"]) <= ps.last_regular_week()]
    wk = int(pd.to_numeric(p["ThroughWeek"]).max())
    p = p[pd.to_numeric(p["ThroughWeek"]) == wk]
    return {(str(r.LeagueID), str(r.RosterID)): (float(r.Score), int(float(r.Rank))) for r in p.itertuples()}, wk


def project(year):
    """Runs the real postseason code on projected results. Returns a dict (see the end)."""
    real_done = sorted(ps.completed_weeks(year))
    after = max(real_done, default=0)
    lr, ccg = ps.last_regular_week(), ps.ccg_week()
    reg = ps.regular_games(year)
    avg = reg.groupby(["LeagueID", "RosterID"])["PF"].mean().round(2).to_dict()

    m = ps._matchups(year).copy()
    m["PointsAgainst"] = pd.to_numeric(m["PointsAgainst"], errors="coerce")
    fut = m["Week"].between(after + 1, lr)
    k_ = list(zip(m["LeagueID"], m["RosterID"]))
    ok_ = list(zip(m["LeagueID"], m["OpponentRosterID"].astype(str).str.replace(".0", "", regex=False)))
    m.loc[fut, "PointsFor"] = [avg.get(k) for k, f in zip(k_, fut) if f]
    m.loc[fut, "PointsAgainst"] = [avg.get(k) for k, f in zip(ok_, fut) if f]
    m.loc[fut, "Outcome"] = ["Win" if (a or 0) > (b or 0) else "Loss" if (a or 0) < (b or 0) else "Tie"
                             for a, b in zip(m.loc[fut, "PointsFor"], m.loc[fut, "PointsAgainst"])]
    wk = m["Week"] == ccg
    m.loc[wk, "PointsFor"] = [avg.get(k) for k, f in zip(k_, wk) if f]  # CCG: higher average wins

    real_matchups, real_completed = ps._matchups, ps.completed_weeks
    ps._matchups = lambda y, _m=m, _y=int(year): _m.copy() if int(y) == _y else real_matchups(y)
    ps.completed_weeks = lambda y: list(range(1, ccg + 1)) if int(y) == int(year) else real_completed(y)
    ps._cache.clear()
    try:
        d = tempfile.mkdtemp(prefix="bowlproj_")
        import conference_championships as cc
        import playoff_field as pf
        for mod, args in ((cc, ["--force"]), (pf, [])):
            sys.argv = [mod.__file__, "--year", str(year), "--data-dir", d] + args
            buf = io.StringIO()
            try:
                with redirect_stdout(buf):
                    mod.main()
            except SystemExit as ex:
                if ex.code not in (0, None):
                    raise RuntimeError(f"{os.path.basename(mod.__file__)} failed in projection:\n{buf.getvalue()[-800:]}")
        season_path, field_path, _ = ps.paths(argparse.Namespace(data_dir=d))
        _, cfg = ps.config()
        bcfg = cfg["bowls"]
        pool, notes = B.build_pool(year, field_path, bcfg)
        draw = B.Draw(year, pool, bcfg, random.Random(0))
        games, _, _ = draw.run()
        field = pd.read_csv(field_path, dtype=str)

        # bubble: the at-large order the real playoff_field.py uses
        st = ps.standings(year)
        auto = {key(r) for r in field.to_dict("records") if str(r["BidType"]).startswith("Auto")}
        rest = st[[key(r) not in auto for r in st.to_dict("records")]]
        order, _, _ = ps.rank_ties(rest)
        n_at = int((field["BidType"] == "At-Large").sum())
        last_in = order.iloc[max(n_at - BUBBLE, 0):n_at].to_dict("records")
        first_out = order.iloc[n_at:n_at + BUBBLE].to_dict("records")

        # Marquee league seats (same rule as bowls.Draw.marquee, after the Prestige picks)
        d2 = B.Draw(year, pool, bcfg, random.Random(0))
        for tier in bcfg["tiers"]:
            if tier["fill"] == "rank":
                d2.prestige([{**b, "tier": tier["name"], "week": tier["week"]} for b in tier["bowls"]][:len(d2.left) // 2])
                break
        seats, seen = set(), set()
        for t in d2.seat_order():
            if t["LeagueID"] not in seen:
                seen.add(t["LeagueID"])
                seats.add(key(t))

        # projected remaining W/L (weeks after+1..lr + CCG) for the seeds
        rem = {}
        for r in m[fut].itertuples():
            k = (str(r.LeagueID), str(r.RosterID))
            w, l = rem.get(k, (0, 0))
            rem[k] = (w + (r.Outcome == "Win"), l + (r.Outcome == "Loss"))
        s_ = ps.read_season(season_path)
        for r in s_[s_["Round"] == "CCG"].itertuples():
            k = (str(r.LeagueID), str(r.RosterID))
            w, l = rem.get(k, (0, 0))
            rem[k] = (w + (r.Outcome == "Win"), l + (r.Outcome == "Loss"))
    finally:
        ps._matchups, ps.completed_weeks = real_matchups, real_completed
        ps._cache.clear()

    # projected seeds (background only)
    pc = pcfg()
    pw, pl = float(pc.get("seed_per_win", 0.1)), float(pc.get("seed_per_loss", 0.1))
    sc, poll_wk = poll_scores(year)
    f = field.copy().reset_index(drop=True)
    ks = [key(r) for r in f.to_dict("records")]
    f["_s"] = [sc.get(k, (-99, 999))[0] + pw * rem.get(k, (0, 0))[0] - pl * rem.get(k, (0, 0))[1] for k in ks]
    f["_r"] = [sc.get(k, (-99, 999))[1] for k in ks]
    f = f.sort_values(["_s", "_r"], ascending=[False, True]).reset_index(drop=True)
    f["Seed"] = range(1, len(f) + 1)
    return dict(year=int(year), after=after, poll_week=poll_wk, pool=pool, games=games, draw=draw,
                field=f.to_dict("records"), last_in=last_in, first_out=first_out, seats=seats, notes=notes)


# ------------------------------------------------------------------ page
CSS = """
.card{margin:0 0 18px;padding:14px 14px 10px}
.card h2{font-size:20px;margin:0 0 2px}
.card h2 small{font-size:12px}
.card h3{font-size:13px;margin:12px 0 6px;text-transform:uppercase;letter-spacing:.04em}
.card .sub{font-size:11px;color:var(--mute);margin:0 0 10px}
.g{display:grid;grid-template-columns:44px 1fr;gap:8px;align-items:center;padding:7px 0;border-top:1px solid var(--line)}
.g:first-of-type{border-top:0}
.g .bl img{width:44px;height:44px;object-fit:contain;display:block}
.g .bn{font:700 13px var(--num);margin:0 0 4px}
.g .bn span{font:500 10px var(--sans,sans-serif);color:var(--mute);margin-left:4px}
.vs{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.tm{display:flex;align-items:center;gap:6px;border-radius:5px;padding:4px 7px;font-weight:700;font-size:13px;line-height:1.15;min-width:0}
.tm img{width:22px;height:22px;object-fit:contain;flex:none;background:#fff;border-radius:3px}
.tm .nm{flex:1;min-width:0}
.tm small{display:block;font-weight:500;font-size:10px;opacity:.9;color:inherit!important;margin:0}
.aq{font:800 9px var(--num);letter-spacing:.04em;border:1.5px solid;border-radius:3px;padding:1px 3px;flex:none}
.pr{display:grid;grid-template-columns:1fr 12px 1fr;gap:4px;align-items:center;margin:0 0 4px}
.pr .v{font:600 10px var(--num);color:var(--mute);text-align:center}
.sd{display:grid;grid-template-columns:18px 1fr;gap:3px;align-items:center;min-width:0}
.sd .n{font:700 12px var(--num);text-align:right}
.sd .tm{padding:3px 6px;font-size:12px}
.mv{font:700 9px var(--num);display:block;text-align:right}
.mv.up{color:#16743b}.mv.dn{color:#b42318}.mv.nw{color:var(--mute)}
.bub{display:grid;grid-template-columns:1fr 1fr;gap:10px}
.bub .tm{margin:0 0 4px;padding:3px 6px;font-size:12px}
.chips{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.foot{font-size:10px;color:var(--mute);margin:8px 0 0}
.status{font-size:13px;margin:0 0 8px}
details.how{font-size:12px;margin:0 0 16px}
details.how summary{cursor:pointer;font-weight:700}
@media(max-width:560px){.pr{grid-template-columns:1fr;gap:2px;margin:0 0 8px}.pr .v{display:none}.chips,.bub,.vs{grid-template-columns:1fr}}
"""


def team(t, col, short, badge="", tag=""):
    bg, fg = col.get(t["Team"], ("#14213a", "#ffffff"))
    lg = short.get(str(t["LeagueName"]).strip(), str(t["LeagueName"]).strip())
    b = f'<span class="aq" style="border-color:{fg};color:{fg}">{e(badge)}</span>' if badge else ""
    lg_txt = e(lg) + (" seat" if tag == "seat" else f" · {e(tag)}" if tag else "")
    return (f'<div class="tm" style="background:{bg};color:{fg}">{logo(t["Team"])}<div class="nm">{e(t["Team"])}'
            f'<small>{int(float(t["Wins"]))}-{int(float(t["Losses"]))} · {lg_txt}</small></div>{b}</div>')


def bowl_logo(name):
    """Only logos Chris approved (postseason.bowls.approved_logos: no sponsor branding); else none."""
    if name not in lcfg.cfg()["postseason"]["bowls"].get("approved_logos", []):
        return ""
    for folder in ("assets/logos/Bowls", "assets/logos/Playoffs"):  # playoff bowls + National Championship
        p = os.path.join(folder, f"{name}.png")
        if os.path.exists(p):
            return f'<img src="../{e(p)}" alt="">'
    return ""


def where(b):
    loc = b.get("location") or {}
    return ", ".join(x for x in (loc.get("city"), loc.get("state") if loc.get("country", "USA") == "USA" else loc.get("country")) if x)


def previous(after):
    """Last week's projected seeds {key: seed} (movement), or None."""
    p = os.path.join(OUT_DIR, f"proj-wk{after - 1:02d}.json")
    if not os.path.exists(p):
        return None
    return {tuple(k.split("|")): v for k, v in json.load(open(p)).get("seeds", {}).items()}


def field_card(P, col, short, prev, foot):
    rows = P["field"]
    n = len(rows)

    def mv(t):
        if prev is None:
            return ""
        was = prev.get(key(t))
        if was is None:
            return '<span class="mv nw">NEW</span>'
        d = was - t["Seed"]
        return f'<span class="mv up">▲{d}</span>' if d > 0 else f'<span class="mv dn">▼{-d}</span>' if d < 0 else ""

    def cell(t):
        return (f'<div class="sd"><span class="n">{t["Seed"]}{mv(t)}</span>'
                f'{team(t, col, short, "AQ" if str(t["BidType"]).startswith("Auto") else "")}</div>')
    pairs = "".join(f'<div class="pr">{cell(rows[i])}<span class="v">v</span>{cell(rows[n - 1 - i])}</div>'
                    for i in range(n // 2))
    n_aq = sum(str(t["BidType"]).startswith("Auto") for t in rows)
    bub = (f'<h3>On the bubble</h3><div class="bub"><div><p class="sub">Last {len(P["last_in"])} in</p>'
           + "".join(team(t, col, short) for t in P["last_in"]) +
           f'</div><div><p class="sub">First {len(P["first_out"])} out</p>'
           + "".join(team(t, col, short) for t in P["first_out"]) + '</div></div>')
    return (f'<section class="card shot" id="playoff"><h2>Playoff field <small>first round</small></h2>'
            f'<p class="sub">AQ = projected conference champion ({n_aq} auto bids); the rest are at-large. '
            f'Projected seeds: week-{P["poll_week"]} poll, adjusted for projected wins and losses.</p>'
            f'{pairs}{bub}<p class="foot">{e(foot)}</p></section>')


def build(year):
    P = project(year)
    col = colors()
    short = {v: k for k, v in ps.league_short().items()}
    by_tier = {}
    for b, x, y in P["games"]:
        by_tier.setdefault(b["tier"], []).append((b, x, y))
    after, lr = P["after"], ps.last_regular_week()
    foot = (f"Projection, not official · {year} after week {after} · weeks {after + 1}–{lr} + CCG projected "
            f"(each team scores its season average)")
    prev = previous(after)

    def games_card(tier, label, tags=False):
        rows = []
        for b, x, y in by_tier.get(tier, []):
            def tg(t):
                if not tags:
                    return ""
                return "seat" if key(t) in P["seats"] else "at-large"
            rows.append(f'<div class="g"><div class="bl">{bowl_logo(b["name"])}</div><div>'
                        f'<p class="bn">{e(b["name"])}<span>{e(where(b))}</span></p>'
                        f'<div class="vs">{team(x, col, short, tag=tg(x))}{team(y, col, short, tag=tg(y))}</div></div></div>')
        if not rows:
            return ""
        slug = tier.split()[0].lower()
        return (f'<section class="card shot" id="{slug}"><h2>{e(tier)} <small>week {by_tier[tier][0][0]["week"]}</small></h2>'
                f'<p class="sub">{e(label)}</p>{"".join(rows)}<p class="foot">{e(foot)}</p></section>')

    others = [t for tier in ("Showcase Bowls", "Opening Bowls") for b, x, y in by_tier.get(tier, []) for t in (x, y)]
    others.sort(key=lambda t: P["draw"].order[B.slot(t)])
    other_card = (f'<section class="card" id="others"><h2>Other teams projected to go bowling <small>{len(others)} teams</small></h2>'
                  f'<p class="sub">Bowls and opponents for these teams are drawn at random after selection. Listed in bowl order.</p>'
                  f'<div class="chips">{"".join(team(t, col, short) for t in others)}</div></section>') if others else ""

    rk = P["draw"].cfg.get("rank", {})
    how = (f'<details class="how"><summary>How the projection works</summary>'
           f'<p>Every remaining regular-season game (weeks {after + 1}–{lr}) and every conference championship game goes to '
           f'the team with the higher season scoring average. Then the real postseason rules run on those results: '
           f'conference champions get automatic bids (AQ), at-large spots go by record and the tiebreakers, and bowl teams '
           f'are ordered by poll rank adjusted for wins ({rk.get("poll_spots_per_win", 25)} poll spots per win). '
           f'Projected seeds use the latest poll, adjusted for projected wins and losses; the real seeds come from the '
           f'bots\' seeding ballot after championship week. Marquee Bowls give each league a seat (the better of its '
           f'two division leaders still available), then fill by bowl order. Records shown are projected final records.</p></details>')
    body = (f'<p class="status"><b>Projection after week {after}</b> · not official · updates every Tuesday until selection</p>'
            + how + field_card(P, col, short, prev, foot)
            + games_card("Prestige Bowls", "Top of the bowl order.")
            + games_card("Marquee Bowls", "One seat per league (its better division leader still available), then at-large by bowl order; "
                         "placed by tie-ins.", tags=True)
            + other_card)
    doc = (page_head(f"{lcfg.brand()} postseason", CSS) +
           f'<div class="wrap"><nav class="weeks" aria-label="Pages">{nav_html("postseason")}</nav>'
           f'{seasons_row(year)}{ARCH_MARK}<header><h1>{lcfg.brand()} <em>Postseason</em></h1></header>{body}</div></body></html>')
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(ARCHIVE.format(after), "w", encoding="utf-8") as fh:
        fh.write(doc)
    with open(PAGE, "w", encoding="utf-8") as fh:
        fh.write(doc)
    refresh_archive_rows(after)
    meta = {"year": int(year), "after_week": after, "playoff_field": len(P["field"]), "notes": P["notes"],
            "seeds": {"|".join(key(t)): t["Seed"] for t in P["field"]},
            "games": {t: [[b["name"], x["Team"], y["Team"]] for b, x, y in g] for t, g in by_tier.items()},
            "last_in": [t["Team"] for t in P["last_in"]], "first_out": [t["Team"] for t in P["first_out"]]}
    for path in (META, os.path.join(OUT_DIR, f"proj-wk{after:02d}.json")):
        with open(path, "w") as fh:
            json.dump(meta, fh, indent=1)
    return meta


def seasons_row(year):
    """Links to past seasons' real postseason pages (postseason_page.py); this season = the projection."""
    try:
        import postseason_page
        return postseason_page.season_row_html(current=year)
    except Exception as ex:  # the projection must never fail over a nav row
        print(f"WARNING: season row skipped ({ex})")
        return ""


ARCH_MARK = "<!--projection-archive-->"
ARCH_RE = re.compile(r'(<!--projection-archive-->)(<nav class="weeks sub" aria-label="Projection archive">.*?</nav>)?', re.S)


def archive_row(weeks, current):
    """Point-in-time picker (like the Weekly Awards archive): one link per projection week."""
    if len(weeks) < 2:
        return ""
    cur = ' aria-current="page"'
    links = "".join(f'<a href="{ARCHIVE.format(w).split("/")[-1]}"{cur if w == current else ""}>After wk {w}</a>' for w in weeks)
    return f'<nav class="weeks sub" aria-label="Projection archive"><span>Projection</span>{links}</nav>'


def refresh_archive_rows(latest):
    """Every projection page (current + archive) gets the full, current week list."""
    weeks = sorted(int(m.group(1)) for f in glob.glob(ARCHIVE.replace("{:02d}", "*"))
                   if (m := re.search(r"wk(\d+)\.html$", f)))
    pages = [(PAGE, latest)] + [(ARCHIVE.format(w), w) for w in weeks]
    for path, w in pages:
        doc = open(path, encoding="utf-8").read()
        doc = ARCH_RE.sub(lambda mm: ARCH_MARK + archive_row(weeks, w), doc, count=1)
        with open(path, "w", encoding="utf-8") as fh:
            fh.write(doc)


def shoot():
    """Discord cards = the page sections marked .shot (playoff field, Prestige, Marquee)."""
    from playwright.sync_api import sync_playwright
    os.makedirs(OUT_DIR, exist_ok=True)
    for f in glob.glob(os.path.join(OUT_DIR, "*.png")):
        os.remove(f)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 600, "height": 900}, device_scale_factor=2, color_scheme="light")
        pg.goto("file://" + os.path.abspath(PAGE), wait_until="networkidle")
        pg.add_style_tag(content=".totop{display:none!important}")
        pg.evaluate("document.fonts.ready")
        for i, s in enumerate(pg.query_selector_all("section.card.shot")):
            path = os.path.join(OUT_DIR, f"{i:02d}-{s.get_attribute('id')}.png")
            s.screenshot(path=path)
            made.append(path)
        b.close()
    return made


# ------------------------------------------------------------------ discord
def stored():
    if not os.path.exists(META):
        sys.exit(f"No stored projection ({META}); build + render first")
    files = sorted(glob.glob(os.path.join(OUT_DIR, "*.png")))
    if not files:
        sys.exit("No stored projection images; run with --render first")
    return json.load(open(META)), files


WORDS = {1: "One week", 2: "Two weeks", 3: "Three weeks", 4: "Four weeks", 5: "Five weeks", 6: "Six weeks"}


def league_message(meta, contact=""):
    """The league post (wording locked with Chris, 2026-11-03): three cards + the short link (Discord
    link preview on, like the other weekly posts) + "Questions? Ask @Chris" like the awards post."""
    left = ps.last_regular_week() - int(meta["after_week"])
    lead = f"{WORDS.get(left, f'{left} weeks')} left. " if left > 0 else ""
    return (f"\U0001F3C8 **{lcfg.brand()} Playoff & Bowl Projection · After Week {meta['after_week']}**\n"
            f"{lead}Here's where you're headed.\n"
            f"Full projection, the bubble and every bowl team: {LINK}\n"
            f"Questions? Ask {f'<@{contact}>' if contact else 'the data manager'}.")


def post(where_to):
    import poll_discord as pdisc
    from discord_post import note, valid
    meta, files = stored()
    hook = "DISCORD_WEBHOOK_LM_PRIVATE_DATA" if where_to == "preview" else "DISCORD_WEBHOOK_TEAM_STATS"
    url = os.environ.get(hook, "")
    if not valid(url):
        note("warning", f"Bowl projection not posted: {hook} not set")
        return 1
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    mentions = [contact] if contact else []
    msg = league_message(meta, contact)
    if where_to == "preview":
        msg = "PREVIEW (not posted to the league):\n" + msg
    pdisc.send(url, msg, mentions=mentions, files=files[:10])
    note("notice", f"Bowl projection (after week {meta['after_week']}) posted: {where_to}")
    return 0


def should_run(year):
    pc = pcfg()
    if not pc.get("enabled", True):
        return False, "projection disabled in config"
    done = max(ps.completed_weeks(year), default=0)
    if done < int(pc.get("from_week", 8)):
        return False, f"only {done} week(s) played (from_week {pc.get('from_week', 8)})"
    if done >= ps.last_regular_week():
        return False, "regular season over: real bowl selection takes over"
    return True, ""


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--render", action="store_true")
    ap.add_argument("--shoot", action="store_true", help="screenshot the existing page only")
    ap.add_argument("--preview", action="store_true", help="post stored cards to lm-private-data")
    ap.add_argument("--publish", action="store_true", help="post stored cards to the league channel")
    ap.add_argument("--force", action="store_true", help="build even outside the projection window")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    if a.publish:
        sys.exit(post("league"))
    if a.shoot:
        if not os.path.exists(PAGE):
            sys.exit(f"No {PAGE} to screenshot")
        print(f"Rendered {len(shoot())} card(s) in {OUT_DIR}/")
        sys.exit(0)
    if a.preview and not a.render:
        sys.exit(post("preview"))
    year = a.year or ps.current_season()
    ok, why = should_run(year)
    if not ok and not a.force:
        print(f"Bowl projection skipped: {why}")
        sys.exit(0)
    meta = build(year)
    os.makedirs("work", exist_ok=True)
    open("work/bowl_projection.built", "w").write(str(meta["after_week"]))
    print(f"Wrote {PAGE} (after week {meta['after_week']}): " + ", ".join(f"{t}: {len(g)}" for t, g in meta["games"].items())
          + f"; bubble in {meta['last_in']}, out {meta['first_out']}")
    for n in meta["notes"]:
        print("  note:", n)
    if a.render:
        made = shoot()
        print(f"Rendered {len(made)} card(s) in {OUT_DIR}/")
        if a.preview:
            sys.exit(post("preview"))
