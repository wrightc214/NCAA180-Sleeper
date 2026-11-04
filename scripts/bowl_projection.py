"""
bowl_projection.py -- "if the season ended the way it's trending": projected bowl lineup.

Chris, 2026-11-03. Remaining regular-season games and the CCG are projected (each team scores
its season average under this season's scoring; the higher average wins), then the REAL
postseason code runs on the projected standings: conference_championships -> playoff_field ->
bowls (config postseason.bowls: poll-per-win order, division-leader Marquee seat, tie-ins).
Nothing real is written: Matchups/Postseason files are untouched (projection runs in memory and
in a scratch data dir). Bowl order uses the latest poll available (the real selection uses the
week-11 poll).

Shown (Chris, 2026-11-03): the projected playoff field (seeded by the latest poll; AQ = projected
conference champion) + Prestige and Marquee games (rule-driven, deterministic). Showcase and Opening
are random draws and are left out.

Approval flow (Chris: nothing public without his approval):
  python scripts/bowl_projection.py            build reports/bowl-projection.html + data JSON
  python scripts/bowl_projection.py --render   + screenshot cards to reports/bowl-projection/*.png
  python scripts/bowl_projection.py --shoot    screenshot the existing page only (workflow render step)
  python scripts/bowl_projection.py --preview  post the stored cards to lm-private-data (review);
                                               with projection.post_to_league also to the league
  python scripts/bowl_projection.py --publish  post the STORED cards (exactly what was previewed)
                                               to the league channel; never rebuilds
Config: postseason.bowls.projection (enabled, from_week, post_to_league = auto-post after preview).
"""
import argparse
import glob
import html
import json
import os
import random
import re
import sys
import tempfile
from contextlib import redirect_stdout
import io

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowls as B  # noqa: E402
import league_config as lcfg  # noqa: E402
from poll_page import colors, logo  # noqa: E402
from site_common import nav_html, page_head  # noqa: E402

OUT_HTML = "reports/bowl-projection.html"
OUT_DIR = "reports/bowl-projection"
META = os.path.join(OUT_DIR, "meta.json")
e = html.escape


# ------------------------------------------------------------------ projection
def project(year):
    """(after_week, games, tiers, notes, field) -- runs the real postseason code on projected results."""
    real_done = sorted(ps.completed_weeks(year))
    after = max(real_done, default=0)
    lr, ccg = ps.last_regular_week(), ps.ccg_week()
    reg = ps.regular_games(year)
    avg = reg.groupby(["LeagueID", "RosterID"])["PF"].mean().round(2).to_dict()

    m = ps._matchups(year).copy()
    m["PointsAgainst"] = pd.to_numeric(m["PointsAgainst"], errors="coerce")
    fut = m["Week"].between(after + 1, lr)
    key = list(zip(m["LeagueID"], m["RosterID"]))
    okey = list(zip(m["LeagueID"], m["OpponentRosterID"].astype(str).str.replace(".0", "", regex=False)))
    m.loc[fut, "PointsFor"] = [avg.get(k) for k, f in zip(key, fut) if f]
    m.loc[fut, "PointsAgainst"] = [avg.get(k) for k, f in zip(okey, fut) if f]
    m.loc[fut, "Outcome"] = ["Win" if (a or 0) > (b or 0) else "Loss" if (a or 0) < (b or 0) else "Tie"
                             for a, b in zip(m.loc[fut, "PointsFor"], m.loc[fut, "PointsAgainst"])]
    wk = m["Week"] == ccg
    m.loc[wk, "PointsFor"] = [avg.get(k) for k, f in zip(key, wk) if f]  # CCG: higher average wins

    real_matchups, real_completed = ps._matchups, ps.completed_weeks
    ps._matchups = lambda y, _m=m, _y=int(year): _m.copy() if int(y) == _y else real_matchups(y)
    ps.completed_weeks = lambda y: list(range(1, ccg + 1)) if int(y) == int(year) else real_completed(y)
    ps._cache.clear()
    notes = []
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
        _, field_path, _ = ps.paths(argparse.Namespace(data_dir=d))
        _, cfg = ps.config()
        bcfg = cfg["bowls"]
        pool, pnotes = B.build_pool(year, field_path, bcfg)
        notes += pnotes
        draw = B.Draw(year, pool, bcfg, random.Random(0))
        games, unfilled, left = draw.run()
        field = pd.read_csv(field_path, dtype=str)
        rem = {}  # projected remaining W/L per team (weeks after+1..lr + CCG): seeds
        for r in m[fut].itertuples():
            k = (str(r.LeagueID), str(r.RosterID))
            w, l = rem.get(k, (0, 0))
            rem[k] = (w + (r.Outcome == "Win"), l + (r.Outcome == "Loss"))
        sp, _, _ = ps.paths(argparse.Namespace(data_dir=d))
        s_ = ps.read_season(sp)
        for r in s_[s_["Round"] == "CCG"].itertuples():
            k = (str(r.LeagueID), str(r.RosterID))
            w, l = rem.get(k, (0, 0))
            rem[k] = (w + (r.Outcome == "Win"), l + (r.Outcome == "Loss"))
        field.attrs["rem"] = rem
        in_pool = {name: [t["Team"] for t in pool if draw.in_pool(t, name)] for name in draw.pools}
    finally:
        ps._matchups, ps.completed_weeks = real_matchups, real_completed
        ps._cache.clear()
    return after, pool, games, draw, field, notes, in_pool


# ------------------------------------------------------------------ page
CSS = """
.card{margin:0 0 18px;padding:14px 14px 10px}
.card h2{font-size:20px;margin:0 0 2px}
.card h2 small{font-size:12px}
.card .sub{font-size:11px;color:var(--mute);margin:0 0 10px}
.g{display:grid;grid-template-columns:44px 1fr;gap:8px;align-items:center;padding:7px 0;border-top:1px solid var(--line)}
.g:first-of-type{border-top:0}
.g .bl img{width:44px;height:44px;object-fit:contain;display:block}
.g .bn{font:700 13px var(--num);margin:0 0 4px}
.g .bn span{font:500 10px var(--sans,sans-serif);color:var(--mute);margin-left:4px}
.vs{display:grid;grid-template-columns:1fr 1fr;gap:5px}
.tm{display:flex;align-items:center;gap:6px;border-radius:5px;padding:4px 7px;font-weight:700;font-size:13px;line-height:1.15;min-width:0}
.tm img{width:22px;height:22px;object-fit:contain;flex:none;background:#fff;border-radius:3px}
.tm small{display:block;font-weight:500;font-size:10px;opacity:.9;color:inherit!important;margin:0}
.pr{display:grid;grid-template-columns:1fr 12px 1fr;gap:4px;align-items:center;margin:0 0 4px}
.pr .v{font:600 10px var(--num);color:var(--mute);text-align:center}
.sd{display:grid;grid-template-columns:18px 1fr;gap:3px;align-items:center;min-width:0}
.sd .n{font:700 12px var(--num);text-align:right}
.sd .tm{padding:3px 6px;font-size:12px}
.tm .nm{flex:1;min-width:0}
.aq{font:800 9px var(--num);letter-spacing:.04em;border:1.5px solid;border-radius:3px;padding:1px 3px;flex:none}
.foot{font-size:10px;color:var(--mute);margin:8px 0 0}
"""


def team(t, col, short, badge=""):
    bg, fg = col.get(t["Team"], ("#14213a", "#ffffff"))
    lg = short.get(str(t["LeagueName"]).strip(), str(t["LeagueName"]).strip())
    b = f'<span class="aq" style="border-color:{fg};color:{fg}">{e(badge)}</span>' if badge else ""
    return (f'<div class="tm" style="background:{bg};color:{fg}">{logo(t["Team"])}<div class="nm">{e(t["Team"])}'
            f'<small>{int(float(t["Wins"]))}-{int(float(t["Losses"]))} · {e(lg)}</small></div>{b}</div>')


def poll_scores(year):
    """{(LeagueID, RosterID): (consensus Score, rank)} from the latest BotConsensus poll through the
    last regular week, and that week."""
    import league_config as L
    frames = [pd.read_csv(f, dtype=str) for f in ("data/Poll_Season.csv", "data/Poll_Historic.csv") if os.path.exists(f)]
    p = pd.concat(frames)
    p = p[(p["Year"] == str(year)) & (p["PollType"] == "BotConsensus")]
    p = p[pd.to_numeric(p["ThroughWeek"]) <= L.last_regular_week()]
    wk = int(pd.to_numeric(p["ThroughWeek"]).max())
    p = p[pd.to_numeric(p["ThroughWeek"]) == wk]
    return {(str(r.LeagueID), str(r.RosterID)): (float(r.Score), int(float(r.Rank))) for r in p.itertuples()}, wk


def field_card(year, field, col, short):
    """Projected playoff field as first-round pairings (1 v 32 ... 16 v 17). Seeds (Chris, 2026-11-03):
    the latest consensus poll Score, plus seed_per_win for each projected remaining win (CCG
    included) and minus seed_per_loss per projected loss. Not shown -- only the pairings. The real
    seeds come from the bots' Seeding ballot after the CCG. AQ = projected conference champion."""
    pc = lcfg.cfg()["postseason"]["bowls"].get("projection", {})
    pw, pl = float(pc.get("seed_per_win", 0.1)), float(pc.get("seed_per_loss", 0.1))
    sc, wk = poll_scores(year)
    rem = field.attrs.get("rem", {})
    f = field.copy().reset_index(drop=True)
    keys = list(zip(f["LeagueID"].astype(str), f["RosterID"].astype(str)))
    f["_s"] = [sc.get(k, (-99, 999))[0] + pw * rem.get(k, (0, 0))[0] - pl * rem.get(k, (0, 0))[1] for k in keys]
    f["_r"] = [sc.get(k, (-99, 999))[1] for k in keys]
    f = f.sort_values(["_s", "_r"], ascending=[False, True]).reset_index(drop=True)
    f["Seed"] = range(1, len(f) + 1)
    rows_ = f.to_dict("records")

    def cell(t):
        return (f'<div class="sd"><span class="n">{t["Seed"]}</span>'
                f'{team(t, col, short, "AQ" if str(t["BidType"]).startswith("Auto") else "")}</div>')
    n = len(rows_)
    pairs = "".join(f'<div class="pr">{cell(rows_[i])}<span class="v">v</span>{cell(rows_[n - 1 - i])}</div>'
                    for i in range(n // 2))
    n_aq = sum(str(t["BidType"]).startswith("Auto") for t in rows_)
    return (f'<section class="card"><h2>Playoff field <small>first round</small></h2>'
            f'<p class="sub">AQ = projected conference champion ({n_aq} auto bids); the rest are at-large. '
            f'Projected seeds: week-{wk} poll, adjusted for projected wins and losses.</p>{pairs}</section>')


def bowl_logo(name):
    p = os.path.join("assets/logos/Bowls", f"{name}.png")
    return f'<img src="../{e(p)}" alt="">' if os.path.exists(p) else ""


def where(b):
    loc = b.get("location") or {}
    return ", ".join(x for x in (loc.get("city"), loc.get("state") if loc.get("country", "USA") == "USA" else loc.get("country")) if x)


def build(year):
    after, pool, games, draw, field, notes, in_pool = project(year)
    col = colors()
    short = {v: k for k, v in ps.league_short().items()}
    by_tier = {}
    for b, x, y in games:
        by_tier.setdefault(b["tier"], []).append((b, x, y))
    lr = ps.last_regular_week()
    sub = (f"Projection, not official · {year} after week {after} · weeks {after + 1}–{lr} + CCG projected "
           f"(each team scores its season average)")
    secs = []

    def games_card(tier, label):
        rows = []
        for b, x, y in by_tier.get(tier, []):
            rows.append(f'<div class="g"><div class="bl">{bowl_logo(b["name"])}</div><div>'
                        f'<p class="bn">{e(b["name"])}<span>{e(where(b))}</span></p>'
                        f'<div class="vs">{team(x, col, short)}{team(y, col, short)}</div></div></div>')
        return (f'<section class="card"><h2>{e(tier)} <small>week {e(str(by_tier[tier][0][0]["week"]))}</small></h2>'
                f'<p class="sub">{e(label)}</p>{"".join(rows)}</section>') if rows else ""

    secs.append(field_card(year, field, col, short))
    secs.append(games_card("Prestige Bowls", "Top of the bowl order."))
    secs.append(games_card("Marquee Bowls", "One seat per league, topped up by bowl order; placed by tie-ins."))

    n_po = len(field)
    method = draw.cfg.get("rank", {})
    foot = (f'Projection, not official. Remaining games: each team scores its season average (higher average wins), '
            f'CCG included. Then the real rules run: {n_po}-team playoff field, then bowls in order of poll rank '
            f'minus {method.get("poll_spots_per_win", 25)} per win (latest poll; the real selection uses the week-{lr} poll). '
            f'Records shown are projected final records.')
    doc = (page_head(f"{lcfg.brand()} bowl projection", CSS) +
           f'<div class="wrap"><nav class="weeks" aria-label="Pages">{nav_html("bowl-projection")}</nav>'
           f'<header><h1>{lcfg.brand()} <em>Bowl projection</em></h1><p class="sub">{e(sub)}</p></header>'
           + "".join(s.replace('</section>', f'<p class="foot">{e(sub)}</p></section>', 1) for s in secs if s)
           + f'<p class="note">{e(foot)}</p></div></body></html>')
    os.makedirs(OUT_DIR, exist_ok=True)
    with open(OUT_HTML, "w", encoding="utf-8") as f:
        f.write(doc)
    meta = {"year": int(year), "after_week": after, "playoff_field": n_po, "notes": notes,
            "games": {t: [[b["name"], x["Team"], y["Team"]] for b, x, y in g] for t, g in by_tier.items()}}
    with open(META, "w") as f:
        json.dump(meta, f, indent=1)
    return meta


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
        pg.add_style_tag(content=".totop{display:none!important}")
        pg.evaluate("document.fonts.ready")
        for i, s in enumerate(pg.query_selector_all("section.card")):
            t = s.query_selector("h2").inner_text().split("\n")[0]
            slug = re.sub(r"[^a-z0-9]+", "-", t.lower()).strip("-")
            path = os.path.join(OUT_DIR, f"{i:02d}-{slug}.png")
            s.screenshot(path=path)
            made.append(path)
        b.close()
    return made


# ------------------------------------------------------------------ discord
def stored():
    if not os.path.exists(META):
        sys.exit("No stored projection (reports/bowl-projection/meta.json); build + render first")
    files = sorted(glob.glob(os.path.join(OUT_DIR, "*.png")))
    if not files:
        sys.exit("No stored projection images; run with --render first")
    return json.load(open(META)), files


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
    head = f"**{lcfg.brand()} bowl projection · after week {meta['after_week']}**"
    if where_to == "preview":
        msg = (head + " — PREVIEW (not posted to the league).\nTo release exactly these images: Actions → "
               "Weekly League Update → Run workflow → script `bowl_projection_publish`.")
        mentions = [contact] if contact else []
        if contact:
            msg = f"<@{contact}> " + msg
    else:
        msg = head + "\nIf the season ended the way it's trending. Projection, not official."
        mentions = [contact] if contact else []
        if contact:
            msg += f"\n<@{contact}>"
    pdisc.send(url, msg, mentions=mentions, files=files[:10])
    note("notice", f"Bowl projection (after week {meta['after_week']}) posted: {where_to}")
    return 0


def should_run(year):
    pc = lcfg.cfg()["postseason"]["bowls"].get("projection", {})
    if not pc.get("enabled", True):
        return False, "projection disabled in config"
    done = max(ps.completed_weeks(year), default=0)
    if done < int(pc.get("from_week", 8)):
        return False, f"only {done} week(s) played (from_week {pc.get("from_week", 8)})"
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
        if not os.path.exists(OUT_HTML):
            sys.exit("No reports/bowl-projection.html to screenshot")
        print(f"Rendered {len(shoot())} card(s) in {OUT_DIR}/")
        sys.exit(0)
    if a.preview and not a.render:
        rc = post("preview")
        if not rc and lcfg.cfg()["postseason"]["bowls"].get("projection", {}).get("post_to_league"):
            rc = post("league")
        sys.exit(rc)
    year = a.year or ps.current_season()
    ok, why = should_run(year)
    if not ok and not a.force:
        print(f"Bowl projection skipped: {why}")
        sys.exit(0)
    meta = build(year)
    os.makedirs("work", exist_ok=True)
    open("work/bowl_projection.built", "w").write(str(meta["after_week"]))
    print(f"Wrote {OUT_HTML} (after week {meta['after_week']}): " + ", ".join(f"{t}: {len(g)}" for t, g in meta["games"].items()))
    for n in meta["notes"]:
        print("  note:", n)
    if a.render:
        made = shoot()
        print(f"Rendered {len(made)} card(s) in {OUT_DIR}/")
        if a.preview:
            sys.exit(post("preview"))
