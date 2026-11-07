"""
postseason_preview.py -- show Chris the postseason drafts waiting for his approval (lm-private-data).

Chris, 2026-11-03: the real selections after CCG week are approved by him before anything is public.
Each selection script writes a DRAFT (data/postseason_drafts/) instead of publishing; this renders
every draft that isn't published yet as cards and posts them to lm-private-data with the script
that approves it:
  playoff field (+ seeds / first-round pairings once the bracket draft exists) + bubble
      -> playoff_publish
  bowls (every tier, with matchups)                     -> bowls_publish  (new draw: bowls_redraw)
  NIT group draws (Qualifier / second group stage)      -> nit_publish    (new draw: nit_redraw)
Nothing here writes data or posts to the league.

  python scripts/postseason_preview.py [--year Y]          build work/postseason_preview.html + cards
  python scripts/postseason_preview.py [--year Y] --post   + post the cards to lm-private-data
"""
import argparse
import glob
import os
import sys

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bowl_projection as bp  # noqa: E402
import bowls as B  # noqa: E402
import league_config as lcfg  # noqa: E402
from poll_page import colors  # noqa: E402
from site_common import page_head  # noqa: E402

OUT_HTML = "work/postseason_preview.html"
OUT_DIR = "work/postseason_preview"
e = bp.e


def key(r):
    return (str(r["LeagueID"]), str(r["RosterID"]).replace(".0", ""))


def pending(year):
    """{name: data} for every draft that isn't published yet."""
    _, field_live, drafts = ps.SEASON_FILE, ps.FIELD_FILE, ps.DRAFT_DIR
    season = ps.read_season(ps.SEASON_FILE)
    yr = season[season["Year"].astype(str) == str(year)]
    out = {}
    live_field = os.path.exists(field_live) and (pd.read_csv(field_live, dtype=str)["Year"].astype(str) == str(year)).any()
    fd = os.path.join(drafts, f"PlayoffField_{year}.csv")
    bd = os.path.join(drafts, f"Playoff_{year}.csv")
    if not (yr["Round"] == "Playoff").any():
        if not live_field and os.path.exists(fd):
            out["field"] = pd.read_csv(fd, dtype=str)
        if os.path.exists(bd):
            out["bracket"] = ps.read_season(bd)
            if "field" not in out and live_field:
                lf = pd.read_csv(field_live, dtype=str)
                out["field"] = lf[lf["Year"].astype(str) == str(year)]
    wd = os.path.join(drafts, f"Bowls_{year}.csv")
    if os.path.exists(wd) and not (yr["Round"] == "Bowl").any():
        out["bowls"] = ps.read_season(wd)
    for tag in ("GS1", "GS2"):
        nd = os.path.join(drafts, f"NIT_{tag}_{year}.csv")
        if os.path.exists(nd):
            d = ps.read_season(nd)
            stage = d["Stage"].iloc[0] if len(d) else ""
            if not ((yr["Round"] == "NIT") & (yr["Stage"] == stage)).any():
                out[f"nit_{tag}"] = d
    return out


def cards(year, P):
    col = colors()
    short = {v: k for k, v in ps.league_short().items()}
    st = {key(r): r for r in ps.standings(year).to_dict("records")}
    T = lambda k: st[k]  # noqa: E731
    secs, actions = [], []

    if "field" in P and len(P["field"]):
        f = P["field"]
        auto = {key(r) for r in f.to_dict("records") if str(r["BidType"]).startswith("Auto")}
        n_at = int((f["BidType"] == "At-Large").sum())
        rest = ps.standings(year)
        rest = rest[[key(r) not in auto for r in rest.to_dict("records")]]
        order, _, _ = ps.rank_ties(rest)
        last_in = order.iloc[max(n_at - bp.BUBBLE, 0):n_at].to_dict("records")
        first_out = order.iloc[n_at:n_at + bp.BUBBLE].to_dict("records")
        bub = (f'<h3>On the bubble</h3><div class="bub"><div><p class="sub">Last {len(last_in)} in</p>'
               + "".join(bp.team(t, col, short) for t in last_in) + f'</div><div><p class="sub">First {len(first_out)} out</p>'
               + "".join(bp.team(t, col, short) for t in first_out) + '</div></div>')
        badge = lambda k: "AQ" if k in auto else ""  # noqa: E731
        if "bracket" in P:
            r1 = P["bracket"][P["bracket"]["PlayoffRound"].astype(str) == "1"]
            seeds = {key(r): int(r["Seed"]) for r in r1.to_dict("records")}
            games = sorted((sorted(g.to_dict("records"), key=lambda r: int(r["Seed"])) for _, g in r1.groupby("GameID")),
                           key=lambda g: int(g[0]["Seed"]))

            def cell(r):
                k = key(r)
                return f'<div class="sd"><span class="n">{seeds[k]}</span>{bp.team(T(k), col, short, badge(k))}</div>'
            body = "".join(f'<div class="pr">{cell(a)}<span class="v">v</span>{cell(b)}</div>' for a, b in games)
            sub = "Seeds from the bots' seeding ballot. AQ = conference champion."
        else:
            rows = sorted(f.to_dict("records"), key=lambda r: (not str(r["BidType"]).startswith("Auto"), -int(float(r["Wins"]))))
            body = f'<div class="chips">{"".join(bp.team(T(key(r)), col, short, badge(key(r))) for r in rows)}</div>'
            sub = "Seeds pending (bots' seeding ballot, then playoff_bracket). AQ = conference champion."
        secs.append(f'<section class="card shot" id="playoff"><h2>Playoff field <small>DRAFT · {len(f)} teams</small></h2>'
                    f'<p class="sub">{e(sub)}</p>{body}{bub}</section>')
        actions.append("**Playoff field" + (" + seeds" if "bracket" in P else "") + "** → approve: script `playoff_publish`"
                       + ("" if "bracket" in P else " (or wait for the seeds: `playoff_bracket` after the seeding ballot)"))

    if "bowls" in P:
        _, cfg = ps.config()
        tier_of = {b["name"]: (i, b) for i, b in enumerate(B.bowl_list(cfg["bowls"]))}
        games = {}
        for gid, g in P["bowls"].groupby("GameID", sort=False):
            i, b = tier_of.get(g.iloc[0]["BowlName"], (99, {"name": g.iloc[0]["BowlName"], "tier": "Other"}))
            games.setdefault(b["tier"], []).append((i, b, [T(key(r)) for r in g.to_dict("records")]))
        for tier, gs in games.items():
            rows = "".join(f'<div class="g"><div class="bl">{bp.bowl_logo(b["name"])}</div><div>'
                           f'<p class="bn">{e(b["name"])}<span>{e(bp.where(b))}</span></p>'
                           f'<div class="vs">{"".join(bp.team(t, col, short) for t in ts)}</div></div></div>'
                           for _, b, ts in sorted(gs, key=lambda x: x[0]))
            slug = tier.split()[0].lower()
            secs.append(f'<section class="card shot" id="bowls-{slug}"><h2>{e(tier)} <small>DRAFT</small></h2>{rows}</section>')
        seed = P["bowls"]["DrawSeed"].iloc[0]
        actions.append(f"**Bowls** (draw seed {seed}) → approve: script `bowls_publish` · new draw: `bowls_redraw`")

    for tag in ("GS1", "GS2"):
        d = P.get(f"nit_{tag}")
        if d is None:
            continue
        stage = d["Stage"].iloc[0]
        groups = "".join(f'<div class="grp"><p class="bn">{e(gid.split("-")[-1])}</p>'
                         f'{"".join(bp.team(T(key(r)), col, short) for r in g.to_dict("records"))}</div>'
                         for gid, g in d.groupby("GameID", sort=True))
        secs.append(f'<section class="card shot" id="nit-{tag.lower()}"><h2>NIT · {e(stage)} <small>DRAFT</small></h2>'
                    f'<div class="grps">{groups}</div></section>')
        actions.append(f"**NIT {stage}** (draw seed {d['DrawSeed'].iloc[0]}) → approve: script `nit_publish` · new draw: `nit_redraw`")
    return secs, actions


CSS = bp.CSS + """
.grps{display:grid;grid-template-columns:1fr 1fr;gap:8px}
.grp .bn{font:700 12px var(--num);margin:0 0 3px}
.grp .tm{margin:0 0 3px;padding:3px 6px;font-size:12px}
"""


def build(year):
    P = pending(year)
    secs, actions = cards(year, P)
    if not secs:
        return [], []
    os.makedirs(OUT_DIR, exist_ok=True)
    doc = (page_head(f"{lcfg.brand()} postseason review", CSS) + '<div class="wrap">' + "".join(secs) + "</div></body></html>")
    with open(OUT_HTML, "w", encoding="utf-8") as fh:
        fh.write(doc)  # work/ sits next to reports/, so the ../assets image paths still resolve
    return secs, actions


def shoot():
    from playwright.sync_api import sync_playwright
    for f in glob.glob(os.path.join(OUT_DIR, "*.png")):
        os.remove(f)
    made = []
    with sync_playwright() as p:
        b = p.chromium.launch()
        pg = b.new_page(viewport={"width": 600, "height": 900}, device_scale_factor=2, color_scheme="light")
        pg.goto("file://" + os.path.abspath(OUT_HTML), wait_until="networkidle")
        pg.add_style_tag(content=".totop,.snap-btn,.fold-bar{display:none!important}")
        pg.evaluate("document.fonts.ready")
        for i, s in enumerate(pg.query_selector_all("section.card.shot")):
            path = os.path.join(OUT_DIR, f"{i:02d}-{s.get_attribute('id')}.png")
            s.screenshot(path=path)
            made.append(path)
        b.close()
    return made


def post(year, actions, files):
    import poll_discord as pdisc
    from discord_post import note, valid
    url = os.environ.get("DISCORD_WEBHOOK_LM_PRIVATE_DATA", "")
    if not valid(url):
        note("warning", "Postseason review not posted: DISCORD_WEBHOOK_LM_PRIVATE_DATA not set")
        return 1
    contact = os.environ.get("DISCORD_CONTACT_ID", "").strip()
    msg = (f"{f'<@{contact}> ' if contact else ''}**{lcfg.brand()} postseason review · {year}** — DRAFT, nothing is public yet.\n"
           + "\n".join(f"• {a}" for a in actions)
           + "\nRun from Actions → Weekly League Update → Run workflow → script.")
    for i in range(0, len(files), 10):
        pdisc.send(url, msg if i == 0 else "(continued)", mentions=[contact] if contact else [], files=files[i:i + 10])
    note("notice", f"Postseason review posted: {len(files)} card(s)")
    return 0


if __name__ == "__main__":
    ap = argparse.ArgumentParser(description=__doc__, formatter_class=argparse.RawDescriptionHelpFormatter)
    ap.add_argument("--year", type=int)
    ap.add_argument("--post", action="store_true")
    a = ap.parse_args()
    os.chdir(lcfg.ROOT)
    year = a.year or ps.current_season()
    secs, actions = build(year)
    if not secs:
        print(f"Postseason review {year}: no unpublished drafts")
        sys.exit(0)
    made = shoot()
    print(f"Postseason review {year}: {len(made)} card(s) in {OUT_DIR}/")
    for x in actions:
        print("  " + x)
    if a.post:
        sys.exit(post(year, actions, made))
