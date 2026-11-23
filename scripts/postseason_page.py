"""
postseason_page.py -- the Postseason page: every season's real postseason (2019 on), one page each.

Chris, 2026-10-28 (display decisions) / 2026-11-04 (build): one page per season with a season
picker; champions on top; then the Playoff (latest round first), Bowls by tier (Prestige first),
the NIT and the conference championships. Past seasons come from data/Postseason_Historic.csv
(names as played); the current season from data/Postseason_Season.csv (published rows only --
drafts never show). Display names follow the agreed conventions (NIT: Opening Groups ->
Qualifier Groups -> Quarterfinal -> Semifinal -> Stagg Bowl; 2020's playoff group stage is
"Playoff Group Stage"; bowl weeks are tiered from each season's last bowl week = Prestige).

Writes reports/postseason-<year>.html for every season with data. reports/postseason.html (the
tab) becomes the current season's page once it has published postseason rows (CCG pairings on);
before that bowl_projection.py owns it (the weekly projection). Logos: approved list only.

  python scripts/postseason_page.py
"""
import glob
import html
import os
import re
import sys
import urllib.parse

import pandas as pd

sys.path.insert(0, os.path.dirname(os.path.abspath(__file__)))
import _postseason_common as ps  # noqa: E402
import bracket as BK  # noqa: E402
import bowl_projection as bp  # noqa: E402
import bowls as B  # noqa: E402
import league_config as lcfg  # noqa: E402
import team_names as tn  # noqa: E402
import trophies as TR  # noqa: E402
from poll_page import colors, logo  # noqa: E402
from site_common import logo_html, menu_html, page_head  # noqa: E402

HIST = "data/Postseason_Historic.csv"
PAGE = "reports/postseason.html"
SEASON_PAGE = "reports/postseason-{}.html"
TIERS = ["Prestige Bowls", "Marquee Bowls", "Showcase Bowls", "Opening Bowls"]  # last bowl week first
e = html.escape


# ------------------------------------------------------------------ data
def num(x):
    try:
        return float(x)
    except (TypeError, ValueError):
        return None


def display_round(year, event, name, nit_rounds):
    """Agreed display names; history files keep the names used then."""
    cfg = ps.config()[1]
    if event == "NIT":
        g1, g2 = cfg["nit"]["group_stage_1"], cfg["nit"]["group_stage_2"]
        if "Pod Stage" in nit_rounds:  # 2021: Pod Stage, then Group Stage
            if name == "Pod Stage":
                return g1["name"]
            if name == "Group Stage":
                return g2["name"]
        if name in g1.get("history_names", []) or name == "Group Stage":  # 2019: the single group stage
            return g1["name"]
        if name in g2.get("history_names", []):
            return g2["name"]
        return {"Elite 8": "Quarterfinal", "Final Four": "Semifinal",
                "Final": cfg["bowls"].get("nit_final_label", "Final")}.get(name, name)
    if event == "Playoff" and name == "Group Stage":
        return "Playoff Group Stage"
    if event == "Playoff" and name == "Third Place":
        return "Third Place Game"
    return name


def history_games(year):
    h = pd.read_csv(HIST, dtype=str, keep_default_na=False)
    h = h[h["Season"] == str(year)]
    nit_rounds = set(h[h["Event"] == "NIT"]["RoundName"])
    out = []
    for r in h.to_dict("records"):
        names = [x.strip() for x in r["TeamA"].split("|") if x.strip()] + ([r["TeamB"].strip()] if r["TeamB"].strip() else [])
        scores = [num(x) for x in r["ScoreA"].split("|")] + ([num(r["ScoreB"])] if r["TeamB"].strip() else [])
        seeds = [r["SeedA"], r["SeedB"]] if r["TeamB"].strip() else [""] * len(names)
        teams = []
        for i, n in enumerate(names):
            sl = tn.slot(year, n) or (None, None)
            teams.append({"Team": n, "LeagueName": (sl[0] or "").strip(), "RosterID": sl[1], "Seed": seeds[i] if i < len(seeds) else "",
                          "Points": scores[i] if i < len(scores) else None, "Win": r["Winner"].strip() == n})
        out.append({"year": int(year), "event": r["Event"], "round": int(r["Round"] or 0), "name": display_round(year, r["Event"], r["RoundName"], nit_rounds),
                    "week": int(r["Week"]) if str(r["Week"]).isdigit() else 0, "bowl": r["Bowl"] if r["Event"] in ("Bowl", "Playoff") else "",
                    "group": re.sub(r"^Group\s+", "", r["Bowl"]) if r["Event"] == "NIT" else "", "teams": teams,
                    "final": any(t["Win"] for t in teams), "note": r["Notes"]})
    return out


def season_games(year):
    s = ps.read_season(ps.SEASON_FILE)
    s = s[s["Year"].astype(str) == str(year)]
    out = []
    for gid, g in s.groupby("GameID", sort=False):
        r0 = g.iloc[0]
        ev = r0["Round"]
        teams = [{"Team": r["Team"], "LeagueName": str(r["LeagueName"]).strip(), "RosterID": r["RosterID"], "Seed": r["Seed"],
                  "Points": num(r["Points"]), "Win": r["Outcome"] == "Win", "Rec": f'{r["RegularSeasonWins"]}'}
                 for r in g.to_dict("records")]
        rnd = int(num(r0["PlayoffRound"]) or 0) if ev == "Playoff" else 0
        name = {"CCG": "Conference Championship", "Bowl": "Bowl"}.get(ev, r0["Stage"])
        out.append({"year": int(year), "event": ev, "round": rnd, "name": display_round(year, ev, name, set()), "week": int(num(r0["Week"]) or 0),
                    "bowl": r0["BowlName"] if ev in ("Bowl", "Playoff") else "",
                    "group": gid.split("-")[-1] if ev == "NIT" and len(teams) > 2 else "",
                    "teams": teams, "final": (g["Status"] == "Final").all(), "note": "", "id": gid})
    return out


def seasons():
    h = pd.read_csv(HIST, dtype=str, keep_default_na=False)
    years = sorted({int(y) for y in h["Season"] if y.isdigit()})
    cur = ps.current_season()
    s = ps.read_season(ps.SEASON_FILE)
    if len(s) and (s["Year"].astype(str) == str(cur)).any():
        years.append(cur)
    return sorted(set(years))


def games_for(year):
    return season_games(year) if int(year) == ps.current_season() else history_games(year)


# ------------------------------------------------------------------ page
CSS = bp.CSS + """
.champs{display:grid;grid-template-columns:1fr 1fr;gap:10px;margin:0 0 18px}
.champ{display:flex;gap:10px;align-items:center;padding:10px 12px}
.champ img.ev{width:64px;height:64px;object-fit:contain;flex:none}
.champ h3{margin:0 0 4px;font-size:12px;text-transform:uppercase;letter-spacing:.04em}
.gm{padding:7px 0;border-top:1px solid var(--line)}
.gm:first-of-type{border-top:0}
.gm .hd{display:flex;align-items:center;gap:6px;font:700 12px var(--num);margin:0 0 4px}
.gm .hd img{width:26px;height:26px;object-fit:contain}
.gm .hd span{font:500 10px var(--sans,sans-serif);color:var(--mute)}
.row{display:grid;grid-template-columns:1fr 52px;gap:5px;align-items:center;margin:0 0 3px}
.row .pts{font:700 14px var(--num);text-align:right}
.row.lose{opacity:.55}
.row.lose .pts{font-weight:500}
.two{display:grid;grid-template-columns:1fr 1fr;gap:6px 14px}
.grid2{display:grid;grid-template-columns:1fr 1fr;gap:4px 14px}
.sd2{font:700 11px var(--num);color:var(--mute);margin-right:4px}
.pending{font-size:11px;color:var(--mute)}
@media(max-width:560px){.two,.grid2,.champs{grid-template-columns:1fr}}
.gm.tr{display:grid;grid-template-columns:minmax(0,1fr) auto;gap:4px 10px;align-items:center}
.gm.tr>.hd{grid-column:1/-1}.gm.tr>.rows{min-width:0}
.gm.tr>.trophy{width:min(var(--tw),26vw)}
@media(max-width:400px){.gm.tr{grid-template-columns:minmax(0,1fr)}.gm.tr>.trophy{width:min(var(--tw),50vw);justify-self:center}}
.bk-champ .trophy{width:min(var(--tw),100%)}
""" + TR.CSS + BK.CSS


def chip(t, col, short, seed=""):
    bg, fg = col.get(t["Team"], ("#14213a", "#ffffff"))
    lg = short.get(t["LeagueName"], t["LeagueName"])
    s = f'<span class="sd2" style="color:{fg}">{e(str(seed))}</span>' if seed not in ("", None) else ""
    return (f'<div class="tm" style="background:{bg};color:{fg}">{s}{logo(t["Team"], bg)}<div class="nm">{e(t["Team"])}'
            f'<small>{e(lg)}</small></div></div>')


def game_html(g, col, short, label=None, logo_name="", trophy=""):
    """trophy: the winner's engraved trophy (shown only once the game is final)."""
    rows = []
    teams = g["teams"]
    if g["event"] == "NIT" and len(teams) > 2:
        teams = sorted(teams, key=lambda t: -(t["Points"] or -1))
    for t in teams:
        lose = g["final"] and not t["Win"]
        pts = f'{t["Points"]:.2f}' if t["Points"] is not None and (g["final"] or t["Points"]) else ""
        rows.append(f'<div class="row{" lose" if lose else ""}">{chip(t, col, short, t.get("Seed", "") if g["event"] == "Playoff" else "")}'
                    f'<span class="pts">{pts}</span></div>')
    head = label if label is not None else (g["bowl"] or (("Group " + g["group"]) if g["group"] else ""))
    lg = bp.bowl_logo(logo_name or g["bowl"]) if (logo_name or g["bowl"]) else ""
    loc = ""
    if logo_name == "National Championship":
        site = ps.config()[1]["playoff"].get("championship_sites", {}).get(str(g.get("year", "")))
        loc = bp.where({"location": site}) if site else ""
    elif g["bowl"]:
        b = next((x for x in B.bowl_list(ps.config()[1]["bowls"]) if x["name"] == g["bowl"]), None)
        loc = bp.where(b) if b else ""
    hd = f'<p class="hd">{lg}{e(head)}{f"<span>{e(loc)}</span>" if loc else ""}</p>' if (head or lg) else ""
    if trophy and g["final"]:
        return f'<div class="gm tr">{hd}<div class="rows">{"".join(rows)}</div>{trophy}</div>'
    return f'<div class="gm">{hd}{"".join(rows)}{"" if g["final"] else "<p class=pending>Upcoming</p>"}</div>'


def trophy_index(year):
    """{(EventType, Event, Round): [ledger rows]} for a season, from both trophy files."""
    L = TR.ledger()
    out = {}
    for r in L[L["Season"].astype(str) == str(year)].to_dict("records"):
        out.setdefault((r["EventType"], r["Event"], r["Round"]), []).append(r)
    return out


def trophy_for(T, key, g, width=None, lazy=True):
    """The engraved trophy for a finished game's winner ('' when the ledger has none or it isn't final)."""
    if not g.get("final"):
        return ""
    w = next((t["Team"] for t in g["teams"] if t["Win"]), None)
    rows = [r for r in T.get(key, []) if r["Team"] == w] or T.get(key, [])[:1]
    return "".join(TR.trophy_html(r, width=width, lazy=lazy) for r in rows)


ROUND_BY_GAMES = {16: "First Round", 8: "Sweet 16", 4: "Elite 8", 2: "Final Four", 1: "National Championship"}
TROPHY = "assets/trophies/special/National Championship.png"


def bowl_src(name):
    """Approved bowl / National Championship logo path ('' when none; legacy names only)."""
    m = re.search(r'src="([^"]+)"', bp.bowl_logo(name) or "")
    return html.unescape(m.group(1)) if m else ""


def bracket_html(po, col, year, short, current=None, T=None):
    """The Playoff bracket (Chris, 2026-11-20, task 5.13; scripts/bracket.py draws it): desktop board,
    phone round-by-round view and Save image exports. '' when the playoff isn't a clean knockout."""
    cfg = ps.config()[1]
    pc, dcfg = cfg["playoff"], cfg["display"].get("bracket", {})
    ko = [dict(g, round_key=(g["week"], g["round"])) for g in po
          if len(g["teams"]) == 2 and g["name"] not in ("Third Place", "Third Place Game", "Group Stage", "Playoff Group Stage")]
    seed = lambda t: int(num(t.get("Seed")) or 99)  # noqa: E731
    R = BK.order_rounds(ko, seed)
    if not R:
        return ""
    names, weeks = [], []
    for j, games in enumerate(R):
        real = next((g for g in games if g), None)
        names.append(real["name"] if real else ROUND_BY_GAMES.get(len(games), f"Round {j + 1}"))
        weeks.append(real["week"] if real else (weeks[-1] + 1 if weeks else int(pc.get("first_week", 13))))
    # bowls for rounds not drawn yet: this season's rotation (past seasons show bowls as played)
    current = int(year) >= ps.current_season() if current is None else current
    full = len(R) == len(pc.get("rounds", []))
    planned = {int(k) - 1: v for k, v in ps.playoff_round_bowls(year).items()} if (current and full) else {}
    e8 = next((j for j, g in enumerate(R) if len(g) == 4), None)
    quad_bowls = None
    if e8 is not None and e8 >= 1:
        quad_bowls = [(g["bowl"] if g and g.get("bowl") else (planned.get(e8) or [""] * 4)[i]) for i, g in enumerate(R[e8])]
        if not all(quad_bowls):  # seasons without Elite 8 bowls (2021) get no quads
            quad_bowls = None
    full_short = {v: k for k, v in ps.league_short().items()} if short is None else short

    def side(t):
        bg, fg = col.get(t["Team"], ("#14213a", "#ffffff"))
        return {"name": t["Team"], "seed": t.get("Seed", ""), "conf": full_short.get(t["LeagueName"], t["LeagueName"]),
                "bg": bg, "fg": fg, "logo": logo_html(t["Team"], bg=bg)}

    def href(g):  # the Scoreboard's postseason game view (current-season games carry a GameID)
        return f"scoreboard.html?season={g['year']}&week={g['week']}&post={g['id']}" if g.get("id") else None

    site = pc.get("championship_sites", {}).get(str(year))
    B = BK.model(R, year=int(year), title="National Playoff", eyebrow=f"{lcfg.brand()} · {year} Postseason",
                 round_names=names, weeks=weeks, side=side, href=href, bowls=planned, quad_bowls=quad_bowls,
                 quad_round=e8 if quad_bowls else None, e8_round=e8, quad_label=dcfg.get("quad_label", "{bowl} Quad"),
                 bowl_src=bowl_src, site=bp.where({"location": site}) if site else "",
                 champion_trophy="../" + urllib.parse.quote(TROPHY), foot=bp.LINK.replace("https://", ""))
    nt = (T or {}).get(("NationalTitle", "National Championship", ""))
    if B["champion"] and nt:  # engraved (task 5.1): page card + the larger Save-image card
        d = TR.cfg()["display"]
        B["champion"]["trophy_html"] = TR.trophy_html(nt[0], width=d["champion"], lazy=False)
        B["champion"]["trophy_html_big"] = TR.trophy_html(nt[0], width=d["export"], lazy=False)
    dim = (float(dcfg.get("loser_opacity", 0.35)), float(dcfg.get("loser_grayscale", 0.6)))
    return BK.html_(B, dim)


def section(title, sub, body, sid):
    return f'<section class="card" id="{sid}"><h2>{e(title)} <small>{e(sub)}</small></h2>{body}</section>'


def build_season(year, years):
    G = games_for(year)
    T = trophy_index(year)
    col = colors()
    short = {v: k for k, v in ps.league_short().items()}
    secs = []

    # champions
    po = [g for g in G if g["event"] == "Playoff"]
    nit = [g for g in G if g["event"] == "NIT"]
    champ = []
    if po:
        last = max(po, key=lambda g: (g["round"], g["week"]))
        if last["final"] and last["name"] != "Third Place Game":
            w = next((t for t in last["teams"] if t["Win"]), None)
            if w:
                champ.append(("National Champion", bp.bowl_logo("National Championship"), w))
    if nit:
        last = max(nit, key=lambda g: (g["round"], g["week"]))
        if last["final"] and len(last["teams"]) == 2:
            w = next((t for t in last["teams"] if t["Win"]), None)
            if w:
                champ.append((f"NIT Champion · {last['name']}", bp.bowl_logo("Stagg Bowl"), w))
    if champ:
        secs.append('<div class="champs">' + "".join(
            f'<div class="card champ">{lg.replace("<img ", "<img class=ev ", 1)}<div><h3>{e(t)}</h3>{chip(w, col, short)}</div></div>'
            for t, lg, w in champ) + "</div>")

    # bracket: the traditional view (Chris, 2026-11-08), then the round-by-round cards
    brk = bracket_html(po, col, year, short, T=T) if po else ""
    if brk:
        secs.append(section("Bracket", "", brk, "bracket"))

    # playoff: latest round first
    if po:
        # Ties (2020: Championship and Third Place Game share a week and round) break by name, title game
        # first, so the page doesn't flip between runs (set order follows string hashing).
        rounds = sorted({(g["round"], g["week"], g["name"]) for g in po},
                        key=lambda x: (-x[1], -x[0], x[2] == "Third Place Game", x[2]))
        body = ""
        for rnd, wk, name in rounds:
            gs = [g for g in po if (g["round"], g["week"], g["name"]) == (rnd, wk, name)]
            hosts = ([b for v in ps.playoff_round_bowls(year).values() for b in v] if int(year) >= ps.current_season() else []) or \
                ["Orange Bowl", "Cotton Bowl", "Peach Bowl", "Fiesta Bowl", "Rose Bowl", "Sugar Bowl"]  # past: as played
            gs.sort(key=lambda g: (hosts.index(g["bowl"]) if g["bowl"] in hosts else 99,
                                   min(int(num(t["Seed"]) or 99) for t in g["teams"])))  # bracket order
            natty = name == "National Championship"

            def tro(g):  # round trophies on the host bowl; the title trophy lives on the bracket card
                if natty:
                    return "" if brk else trophy_for(T, ("NationalTitle", "National Championship", ""), g)
                return trophy_for(T, ("PlayoffRound", g["bowl"], name), g) if g["bowl"] else ""
            inner = "".join(game_html(g, col, short, "" if natty else g["bowl"], logo_name="National Championship" if natty else "",
                                      trophy=tro(g)) for g in gs)
            body += f'<h3>{e(name)}</h3><div class="{"two" if len(gs) > 1 else ""}">{inner}</div>'
        secs.append(section("Playoff", f"{len([g for g in po])} games", body, "playoff"))

    # bowls by tier (from the last bowl week back)
    bw = [g for g in G if g["event"] == "Bowl"]
    if bw:
        weeks = sorted({g["week"] for g in bw}, reverse=True)
        tier = {w: TIERS[i] if i < len(TIERS) else f"Week {w}" for i, w in enumerate(weeks)}
        body = ""
        for w in weeks:
            gs = sorted([g for g in bw if g["week"] == w], key=lambda g: g["bowl"])
            body += (f'<h3>{e(tier[w])}</h3><div class="two">'
                     f'{"".join(game_html(g, col, short, trophy=trophy_for(T, ("Bowl", g["bowl"], ""), g)) for g in gs)}</div>')
        secs.append(section("Bowls", f"{len(bw)} games", body, "bowls"))

    # NIT: latest round first
    if nit:
        rounds = sorted({(g["week"], g["name"]) for g in nit}, key=lambda x: -x[0])
        body = ""
        for wk, name in rounds:
            gs = sorted([g for g in nit if (g["week"], g["name"]) == (wk, name)], key=lambda g: g["group"] or "")
            last_nit = (wk, name) == rounds[0] and len(gs) == 1 and len(gs[0]["teams"]) == 2
            inner = "".join(game_html(g, col, short, ("Group " + g["group"]) if g["group"] else "",
                                      trophy=trophy_for(T, ("NIT", "NIT", ""), g) if last_nit else "") for g in gs)
            body += f'<h3>{e(name)}</h3><div class="two">{inner}</div>'
        secs.append(section("NIT", "", body, "nit"))

    # CCG
    cc = [g for g in G if g["event"] == "CCG"]
    if cc:
        def lgname(g):
            return short.get(g["teams"][0]["LeagueName"], g["teams"][0]["LeagueName"])
        body = '<div class="two">' + "".join(game_html(g, col, short, lgname(g), trophy=trophy_for(T, ("CCG", f"{lgname(g)} Championship", ""), g))
                                             for g in sorted(cc, key=lgname)) + "</div>"
        secs.append(section("Conference Championships", "", body, "ccg"))

    if not secs:
        secs.append('<p class="status">Nothing published yet for this season.</p>')
    note = ('<p class="note">Names, logos and formats as played that season. Some early seasons are missing scores '
            '(results were recorded outside Sleeper).</p>') if int(year) < ps.current_season() else ""
    return (page_head(f"{lcfg.brand()} postseason {year}", CSS) +
            f'<div class="wrap">{menu_html("postseason", ["postseason-seasons"])}'
            f'<header><h1>{lcfg.brand()} <em>{year} Postseason</em></h1></header>' + "".join(secs) + note
            # fold + save image on every section (Chris, 2026-11-07 site design rule)
            + bp.FOLD_JS + bp.snap_js(0, foot=f"{lcfg.brand()} · {year} Postseason · {bp.LINK.replace('https://', '')}", tag=str(year), projection=False)
            + "</div></body></html>")


def main():
    os.chdir(lcfg.ROOT)
    ys = seasons()
    for y in ys:
        doc = build_season(y, ys)
        with open(SEASON_PAGE.format(y), "w", encoding="utf-8") as f:
            f.write(doc)
        if y == ps.current_season():
            with open(PAGE, "w", encoding="utf-8") as f:
                f.write(doc)
    print(f"Postseason pages: {', '.join(map(str, ys))}" + (" (current season live on postseason.html)" if ps.current_season() in ys else ""))


if __name__ == "__main__":
    main()
